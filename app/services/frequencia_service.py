"""
Frequência: registrar a entrada do aluno, ver quem está na academia, quem sumiu e a assiduidade.

[back-10-frequencia] Criado nesta branch. As rotas ficam em blueprints/frequencia/routes.py.

Regra que vale para tudo aqui (é a regra de leitura do Esquema-Backend): frequência se mede pela
EXISTÊNCIA de linhas na tabela `frequencias`. Quem não tem nenhuma entrada registrada é "sem
dado", nunca "0 acessos": um aluno novo, ou uma academia que acabou de ligar o check-in, não
pode aparecer como aluno sumido.

Definições (são escolhas simples, fáceis de explicar para o dono):
  - o sistema não registra saída. "Na academia agora" = quem entrou há menos de PERMANENCIA_MIN;
  - toque duplo: a mesma pessoa não ganha outra entrada antes de INTERVALO_MIN;
  - ausente = aluno ativo cuja ÚLTIMA entrada foi há mais de DIAS_AUSENTE dias;
  - assiduidade = em quantos dos últimos 30 dias o aluno veio, sobre 30.
"""
import csv
import io
import re
from collections import Counter
from datetime import date, datetime, timedelta

from flask_login import current_user
from sqlalchemy import func

from app.extensions.database import db
from app.helpers.conta import conta_id, da_conta
from app.models import Aluno, Frequencia
from app.services.situacao_service import cobrancas_em_aberto_da_conta, linha_do_aluno, vencimentos_da_conta

PERMANENCIA_MIN = 90        # quanto tempo depois da entrada o aluno ainda conta como "na academia"
INTERVALO_MIN = 60          # menos que isso desde a última entrada do mesmo aluno é toque repetido
DIAS_AUSENTE = 15           # o card do painel é "Ausentes há mais de 15 dias"
HORAS = list(range(6, 23))  # barras do gráfico: das 06h às 22h
ORIGENS = {'recepcao': 'Recepção', 'app': 'App'}
DIAS_DA_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']


class EntradaRecusada(Exception):
    """Não dá para registrar a entrada. A mensagem é mostrada à recepção."""


def _hm(momento):
    return momento.strftime('%Hh%M')


def _so_digitos(texto):
    return re.sub(r'\D', '', texto or '')


def _linhas_dos_alunos(alunos, hoje):
    """Alunos no formato das telas (com plano e status), usando a mesma regra de situação do painel."""
    vencimento, em_aberto = vencimentos_da_conta(), cobrancas_em_aberto_da_conta()
    linhas = {}
    for a in alunos:
        linha = linha_do_aluno(a, vencimento.get(a.id), hoje, em_aberto.get(a.id))
        linha['acesso_liberado'] = bool(a.acesso_liberado)
        linhas[a.id] = linha
    return linhas


def _do_dia(dia):
    """As entradas da conta num dia, da mais recente para a mais antiga."""
    inicio = datetime(dia.year, dia.month, dia.day)
    return (da_conta(Frequencia).filter(Frequencia.data_hora_entrada >= inicio, Frequencia.data_hora_entrada < inicio + timedelta(days=1))
            .order_by(Frequencia.data_hora_entrada.desc(), Frequencia.id.desc()).all())


# ------------------------------------------------------------------ registrar
def registrar(aluno, origem='recepcao', agora=None):
    """
    Registra a entrada do aluno. Devolve (entrada, nova): `nova` é False quando ele já tinha
    entrada há menos de INTERVALO_MIN (toque repetido), e nesse caso nada é gravado.
    """
    agora = agora or datetime.now()
    if not aluno.ativo:
        raise EntradaRecusada(f'{aluno.nome} está com a matrícula inativa. Renove antes de liberar a entrada.')
    if not aluno.acesso_liberado:
        raise EntradaRecusada(f'{aluno.nome} está com o acesso bloqueado na recepção.')
    ultima = (da_conta(Frequencia).filter_by(aluno_id=aluno.id)
              .order_by(Frequencia.data_hora_entrada.desc()).first())
    if ultima and timedelta(0) <= agora - ultima.data_hora_entrada < timedelta(minutes=INTERVALO_MIN):
        return ultima, False
    entrada = Frequencia(conta_id=conta_id(), aluno_id=aluno.id, data_hora_entrada=agora,
                         origem=origem if origem in ORIGENS else 'recepcao', instrutor_id=current_user.id)
    db.session.add(entrada)
    db.session.commit()
    return entrada, True


def alternar_acesso(aluno):
    """Bloqueia ou libera a entrada do aluno na recepção. Não mexe em matrícula nem em cobrança."""
    aluno.acesso_liberado = not aluno.acesso_liberado
    db.session.commit()
    return aluno


# ------------------------------------------------------------------ tela de frequência
def buscar(q, limite=6, hoje=None):
    """Alunos da conta por pedaço do nome ou por números do CPF, no formato das telas."""
    q = (q or '').strip().lower()
    numeros = _so_digitos(q)
    alunos = [a for a in da_conta(Aluno).order_by(Aluno.nome).all()
              if q in (a.nome or '').lower() or (len(numeros) > 2 and numeros in _so_digitos(a.cpf))]
    return list(_linhas_dos_alunos(alunos[:limite], hoje or date.today()).values())


def sugestoes(q='', agora=None, limite=3):
    """
    Quem a recepção provavelmente vai registrar. Com busca (2 letras ou mais): o resultado da busca.
    Sem busca: os alunos ativos que costumam chegar perto desta hora (últimos 30 dias) e ainda
    não entraram hoje; se não houver histórico, os últimos alunos cadastrados.
    """
    agora = agora or datetime.now()
    if len((q or '').strip()) >= 2:
        return buscar(q, hoje=agora.date())
    ja_entraram = {e.aluno_id for e in _do_dia(agora.date())}
    recentes = da_conta(Frequencia).filter(Frequencia.data_hora_entrada >= agora - timedelta(days=30)).all()
    costumam = Counter(e.aluno_id for e in recentes if abs(e.data_hora_entrada.hour - agora.hour) <= 1 and e.aluno_id not in ja_entraram)
    ativos = {a.id: a for a in da_conta(Aluno).filter(Aluno.ativo.is_(True)).all()}
    escolhidos = [ativos[i] for i, _ in costumam.most_common() if i in ativos][:limite]
    if not escolhidos:
        escolhidos = sorted((a for a in ativos.values() if a.id not in ja_entraram), key=lambda a: -a.id)[:limite]
    linhas = _linhas_dos_alunos(escolhidos, agora.date())
    return [linhas[a.id] for a in escolhidos]


def contexto_da_tela(q='', agora=None):
    """Variáveis de frequencia/index.html."""
    agora = agora or datetime.now()
    entradas = _do_dia(agora.date())
    linhas = _linhas_dos_alunos({e.aluno for e in entradas}, agora.date())

    # uma barra por hora, das 06h às 22h; o que cair fora disso entra na barra da ponta
    por_hora = [0] * len(HORAS)
    for e in entradas:
        por_hora[min(max(e.data_hora_entrada.hour, HORAS[0]), HORAS[-1]) - HORAS[0]] += 1
    pico = max(por_hora)
    limite = agora - timedelta(minutes=PERMANENCIA_MIN)
    agora_la, vistos = [], set()
    for e in entradas:      # da mais recente para a mais antiga: cada aluno aparece uma vez
        if limite <= e.data_hora_entrada <= agora and e.aluno_id not in vistos:
            vistos.add(e.aluno_id)
            agora_la.append({'aluno': linhas[e.aluno_id], 'hora': _hm(e.data_hora_entrada)})
    return {
        'stats': {'entradas_hoje': len(entradas), 'na_academia': len(agora_la),
                  # sem nenhuma entrada no dia não existe pico: mostra "--", não "06h"
                  'pico_hora': f'{HORAS[por_hora.index(pico)]:02d}' if pico else '--', 'pico_qtd': pico,
                  'media': round(len(entradas) / len(HORAS))},
        'horas': [f'{h:02d}' for h in HORAS],
        'por_hora': por_hora,
        'q': q,
        'sugestoes': sugestoes(q, agora),
        'na_academia': agora_la,
        'entradas': [{'aluno': linhas[e.aluno_id], 'hora': _hm(e.data_hora_entrada), 'origem': ORIGENS.get(e.origem, e.origem)}
                     for e in entradas],
    }


def _celula(texto):
    """Texto seguro para planilha: o apóstrofo impede o Excel de executar como fórmula o que começa com = + - @."""
    texto = str(texto or '')
    return "'" + texto if texto[:1] in ('=', '+', '-', '@', '\t', '\r') else texto


def exportar_csv(agora=None):
    """Os check-ins de hoje em CSV (ponto e vírgula e marca de acentos, para o Excel em português)."""
    contexto = contexto_da_tela(agora=agora)
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=';')
    escritor.writerow(['Aluno', 'Horário', 'Plano', 'Origem', 'Situação'])
    for e in contexto['entradas']:
        escritor.writerow([_celula(e['aluno']['nome']), e['hora'], _celula(e['aluno']['plano']), e['origem'], e['aluno']['status']])
    return '﻿' + saida.getvalue()


# ------------------------------------------------------------------ por aluno e para o painel
def frequencia_do(aluno, hoje=None):
    """
    O cartão "Frequência" do perfil: {pct, semana, checkins}. Devolve None se o aluno NUNCA teve
    entrada registrada: nesse caso não existe assiduidade para mostrar ("sem dado").
    """
    hoje = hoje or date.today()
    entradas = (da_conta(Frequencia).filter_by(aluno_id=aluno.id)
                .order_by(Frequencia.data_hora_entrada.desc(), Frequencia.id.desc()).limit(400).all())
    if not entradas:
        return None
    dias = {e.data_hora_entrada.date() for e in entradas}
    veio_em_30 = sum(1 for d in dias if 0 <= (hoje - d).days < 30)
    segunda = hoje - timedelta(days=hoje.weekday())
    return {
        'pct': round(veio_em_30 / 30 * 100),
        'semana': [1 if (segunda + timedelta(days=i)) in dias else 0 for i in range(7)],
        'checkins': [(f"{DIAS_DA_SEMANA[e.data_hora_entrada.weekday()]}, {e.data_hora_entrada.strftime('%d/%m')}", _hm(e.data_hora_entrada))
                     for e in entradas[:3]],
    }


def dias_sem_vir(hoje=None):
    """
    {aluno_id: dias desde a última entrada}, só para quem tem pelo menos uma entrada. Devolve
    None se a conta não tem NENHUMA entrada registrada (check-in recém-ligado: "sem dado").
    """
    hoje = hoje or date.today()
    ultimas = (da_conta(Frequencia).with_entities(Frequencia.aluno_id, func.max(Frequencia.data_hora_entrada))
               .group_by(Frequencia.aluno_id).all())
    if not ultimas:
        return None
    resultado = {}
    for aluno_id, ultima in ultimas:
        if isinstance(ultima, str):      # o SQLite devolve o resultado de max() como texto
            ultima = datetime.fromisoformat(ultima)
        resultado[aluno_id] = (hoje - ultima.date()).days
    return resultado
