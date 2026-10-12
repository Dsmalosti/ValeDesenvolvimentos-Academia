"""
Painel administrativo (templates/relatorios/admin.html): financeiro e frequência da academia.

[back-11-relatorios] Criado nesta branch. As rotas ficam em blueprints/relatorios/routes.py.

Regra do front: nenhum número é calculado no template, tudo sai daqui. Regra desta branch:
número que o banco não tem como sustentar NÃO é inventado. Onde falta dado, o bloco chega vazio
e a tela diz "sem dado" (retenção e churn dependem da data em que cada aluno foi inativado,
que só passou a ser guardada nesta branch).

De onde vem cada bloco:
  - recebido, formas, lançamentos: tabela de pagamentos, no período escolhido;
  - ponto de equilíbrio: recebido contra os custos fixos (tabela `custos`), na proporção do período;
  - "a receber" e "em atraso": os mesmos números do painel (painel_service), para nunca discordarem;
  - movimento por dia e horário: entradas dos últimos 28 dias (tabela `frequencias`);
  - retenção e churn: data de cadastro e data de inativação dos alunos;
  - risco de cancelar: uma nota de 0 a 100 por aluno ativo (ver `_nota_de_risco`).
"""
import csv
import io
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from math import ceil

from flask_login import current_user
from sqlalchemy.orm import joinedload

from app.extensions.database import db
from app.helpers.conta import conta_id, da_conta
from app.helpers.dinheiro import ler_reais, reais_txt
from app.models import COBRANCA_PENDENTE, Aluno, Cobranca, Custo, Frequencia, Pagamento
from app.services import frequencia_service, painel_service
from app.services.situacao_service import cobrancas_em_aberto_da_conta, linha_do_aluno, vencimentos_da_conta

PERIODOS = {'semana': 'Esta semana', 'mes': 'Este mês', '3m': 'Últimos 3 meses', '6m': '6 meses', '9m': '9 meses', 'ano': '1 ano'}
MESES_DO_PERIODO = {'mes': 1, '3m': 3, '6m': 6, '9m': 9, 'ano': 12}
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
DIAS7 = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
DIAS7_LONGO = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
HORAS_MAPA = [6, 9, 12, 15, 18, 21]                 # cada linha do mapa cobre 3 horas: 06h é das 6h às 8h59
NIVEIS = ['vazio', 'tranquilo', 'movimentado', 'cheio', 'lotado']
DIAS_DO_MAPA = 28
MARCOS_DE_RETENCAO = [0, 30, 60, 90, 180, 365]
# formas do banco -> grupo mostrado no relatório (o filtro do front tem PIX, Cartão e Dinheiro)
GRUPO_DA_FORMA = {'pix': 'PIX', 'debito': 'Cartão', 'credito': 'Cartão', 'cartao': 'Cartão', 'dinheiro': 'Dinheiro'}
CORES_DAS_FORMAS = {'PIX': 'blue', 'Cartão': 'yellow-chart', 'Dinheiro': 'teal', 'Outras': 'slate'}
MAX_CUSTOS = 60
VALOR_MAXIMO = Decimal('99999999.99')


class CustoInvalido(Exception):
    """O custo enviado não pode ser gravado. A mensagem é mostrada ao usuário."""


def _reais0(valor):
    """'R$ 18.900' (sem centavos), como o front mostra nas legendas."""
    return 'R$ ' + reais_txt(round(valor)).split(',')[0]


def _mes_antes(ano, mes, quantos=1):
    indice = ano * 12 + (mes - 1) - quantos
    return indice // 12, indice % 12 + 1


# ------------------------------------------------------------------ período
def intervalo(periodo, hoje):
    """
    (início, fim, início do período anterior, fim do período anterior, texto, texto com "de").
    O fim é sempre hoje (inclusive). O período anterior serve para o "+11% vs ...":
      - mês: o mês passado até o mesmo dia do mês (comparar um mês pela metade com um inteiro
        daria sempre "piorou" na primeira quinzena);
      - os demais: o trecho de mesmo tamanho imediatamente antes.
    """
    if periodo == 'semana':
        inicio = hoje - timedelta(days=hoje.weekday())
        return inicio, hoje, inicio - timedelta(days=7), hoje - timedelta(days=7), 'nesta semana', 'desta semana'
    meses = MESES_DO_PERIODO[periodo]
    ano, mes = _mes_antes(hoje.year, hoje.month, meses - 1)
    inicio = date(ano, mes, 1)
    if periodo == 'mes':
        ano_ant, mes_ant = _mes_antes(hoje.year, hoje.month)
        ultimo_dia = (date(hoje.year, hoje.month, 1) - timedelta(days=1)).day
        return (inicio, hoje, date(ano_ant, mes_ant, 1), date(ano_ant, mes_ant, min(hoje.day, ultimo_dia)),
                f'em {MESES[hoje.month - 1]}', f'de {MESES[hoje.month - 1]}')
    tamanho = (hoje - inicio).days
    rotulo = 'nos últimos 12 meses' if periodo == 'ano' else f'nos últimos {meses} meses'
    return inicio, hoje, inicio - timedelta(days=tamanho + 1), inicio - timedelta(days=1), rotulo, rotulo.replace('nos ', 'dos ')


def _no_intervalo(pagamentos, inicio, fim):
    return [p for p in pagamentos if inicio <= p.data_pagamento.date() <= fim]


def _variacao(agora, antes, periodo, hoje):
    """Texto do selo "+11% vs setembro". Vazio quando não há base para comparar."""
    if not antes:
        return ''
    pct = round((agora - antes) / antes * 100)
    contra = MESES[_mes_antes(hoje.year, hoje.month)[1] - 1] if periodo == 'mes' else 'o período anterior'
    return f"{'+' if pct >= 0 else '−'}{abs(pct)}% vs {contra}"


# ------------------------------------------------------------------ blocos financeiros
def _formas(pagamentos):
    """Faturamento por forma de pagamento: PIX, Cartão (débito + crédito), Dinheiro e, se houver, Outras."""
    soma = defaultdict(float)
    for p in pagamentos:
        soma[GRUPO_DA_FORMA.get(p.forma, 'Outras')] += float(p.valor_pago)
    total = sum(soma.values())
    return [{'nome': nome, 'pct': round(soma[nome] / total * 100) if total else 0, 'cor': CORES_DAS_FORMAS[nome],
             'texto': _reais0(soma[nome]), 'valor': soma[nome]}
            for nome in ('PIX', 'Cartão', 'Dinheiro', 'Outras') if soma[nome] or nome != 'Outras']


def _receita_12_meses(pagamentos, hoje):
    """Gráfico "Receita mês a mês": os últimos 12 meses, o atual por último (a coluna em destaque)."""
    meses = [_mes_antes(hoje.year, hoje.month, n) for n in range(11, -1, -1)]
    por_mes = defaultdict(float)
    for p in pagamentos:
        por_mes[(p.data_pagamento.year, p.data_pagamento.month)] += float(p.valor_pago)
    valores = [round(por_mes[m]) for m in meses]
    melhor = valores.index(max(valores))
    return {
        'labels': [MESES[m - 1][:3].capitalize() for _, m in meses], 'valores': valores, 'destaque': 11,
        'titulo': 'Receita mês a mês', 'sub': 'Últimos 12 meses · a coluna amarela é o mês corrente',
        'selo': 'sem receita no período' if not max(valores) else ('melhor mês do período' if melhor == 11 else f'melhor mês: {MESES[meses[melhor][1] - 1]}'),
        # sem meta de faturamento (vem de Configurações), a linha tracejada é a média
        'meta': round(sum(valores) / len(valores)), 'meta_rotulo': None,
    }


def custos_da_conta():
    return [{'id': c.id, 'descricao': c.descricao, 'valor': float(c.valor)} for c in da_conta(Custo).order_by(Custo.id).all()]


def salvar_custo(id_txt, descricao, valor_txt):
    """Cria um custo fixo (id vazio) ou altera um que já é da conta. Devolve o custo."""
    descricao = ' '.join((descricao or '').split())
    try:
        valor = ler_reais(valor_txt)
    except ValueError:
        valor = Decimal('0')
    if not descricao or len(descricao) > 100 or not (0 < valor <= VALOR_MAXIMO):
        raise CustoInvalido('Informe o nome do custo (até 100 letras) e um valor maior que zero, como 1.200,00.')
    if (id_txt or '').strip():
        custo = da_conta(Custo).filter_by(id=int(id_txt)).first() if id_txt.strip().isdigit() else None
        if custo is None:
            raise CustoInvalido('Custo não encontrado.')
    else:
        if da_conta(Custo).count() >= MAX_CUSTOS:
            raise CustoInvalido(f'O limite é de {MAX_CUSTOS} custos fixos.')
        custo = Custo(conta_id=conta_id())
        db.session.add(custo)
    custo.descricao, custo.valor = descricao, valor
    db.session.commit()
    return custo


def excluir_custo(id):
    """Remove um custo da conta. Devolve False se ele não existe (ou é de outra conta)."""
    custo = da_conta(Custo).filter_by(id=id).first()
    if custo is None:
        return False
    db.session.delete(custo)
    db.session.commit()
    return True


def _teto_do_medidor(recebido, minimo):
    """Fim da régua do ponto de equilíbrio: cabe o recebido com folga e o mínimo fica até a metade da régua."""
    teto = max(recebido * 1.15, minimo / 0.55, 1000)
    return int(ceil(teto / 1000.0) * 1000)


# ------------------------------------------------------------------ lançamentos
def _lancamentos(pagamentos, inicio, fim, hoje, filtro):
    """
    O que entrou no período (pago) e o que está em aberto ou em atraso hoje, do mais novo para o
    mais antigo. `filtro` = {'forma': 'PIX'|'Cartão'|'Dinheiro'|'', 'situacao': 'pago'|'aberto'|'atrasado'|''}.
    """
    itens = []
    for p in _no_intervalo(pagamentos, inicio, fim):
        c = p.cobranca
        itens.append({'aluno': {'nome': (c.aluno.nome if c.aluno else None) or c.nome_visitante or 'Visitante'},
                      'quando': p.data_pagamento, 'data': p.data_pagamento.strftime('%d/%m'),
                      'plano': c.plano.nome if c.plano else 'Diária avulsa', 'forma': GRUPO_DA_FORMA.get(p.forma, 'Outras'),
                      'valor': float(p.valor_pago), 'situacao': 'pago', 'origem': p.origem_confirmacao})
    abertas = (da_conta(Cobranca).filter(Cobranca.status == COBRANCA_PENDENTE)
               .options(joinedload(Cobranca.aluno), joinedload(Cobranca.plano)).all())
    for c in abertas:
        itens.append({'aluno': {'nome': (c.aluno.nome if c.aluno else None) or c.nome_visitante or 'Visitante'},
                      'quando': datetime(c.data_inicio.year, c.data_inicio.month, c.data_inicio.day), 'data': c.data_inicio.strftime('%d/%m'),
                      'plano': c.plano.nome if c.plano else 'Diária avulsa', 'forma': '—', 'valor': float(c.valor),
                      'situacao': 'atrasado' if c.data_inicio < hoje else 'aberto', 'origem': None})
    if filtro['forma']:
        itens = [x for x in itens if x['forma'] == filtro['forma']]
    if filtro['situacao']:
        itens = [x for x in itens if x['situacao'] == filtro['situacao']]
    return sorted(itens, key=lambda x: x['quando'], reverse=True)


def _filtro(argumentos):
    forma, situacao = argumentos.get('forma') or '', argumentos.get('situacao') or ''
    return {'forma': forma if forma in ('PIX', 'Cartão', 'Dinheiro') else '',
            'situacao': situacao if situacao in ('pago', 'aberto', 'atrasado') else ''}


def _celula(texto):
    """Texto seguro para planilha: o apóstrofo impede o Excel de executar como fórmula o que começa com = + - @."""
    texto = str(texto or '')
    return "'" + texto if texto[:1] in ('=', '+', '-', '@', '\t', '\r') else texto


def exportar_csv(argumentos, hoje=None):
    """Os lançamentos do período, com o mesmo filtro da tela, em CSV. Devolve (texto, nome do arquivo)."""
    hoje = hoje or date.today()
    periodo = argumentos.get('periodo') if argumentos.get('periodo') in PERIODOS else 'mes'
    inicio, fim = intervalo(periodo, hoje)[:2]
    itens = _lancamentos(painel_service._pagamentos_da_conta(), inicio, fim, hoje, _filtro(argumentos))
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=';')
    escritor.writerow(['Aluno', 'Data', 'Plano', 'Forma', 'Valor', 'Situação', 'Confirmação'])
    for x in itens:
        escritor.writerow([_celula(x['aluno']['nome']), x['quando'].strftime('%d/%m/%Y'), _celula(x['plano']), x['forma'],
                           reais_txt(x['valor']), x['situacao'], {'manual': 'recepção', 'webhook': 'banco'}.get(x['origem'], '')])
    return '﻿' + saida.getvalue(), f'lancamentos-{inicio.strftime("%Y-%m-%d")}-a-{fim.strftime("%Y-%m-%d")}.csv'


# ------------------------------------------------------------------ frequência, retenção, churn, risco
def _mapa_de_movimento(hoje):
    """Mapa "Movimento por dia e horário": entradas dos últimos 28 dias, em níveis de 0 (vazio) a 4 (lotado)."""
    desde = datetime(hoje.year, hoje.month, hoje.day) - timedelta(days=DIAS_DO_MAPA)
    contagem = defaultdict(int)
    for (quando,) in da_conta(Frequencia).filter(Frequencia.data_hora_entrada >= desde).with_entities(Frequencia.data_hora_entrada):
        faixa = min(max((quando.hour - HORAS_MAPA[0]) // 3, 0), len(HORAS_MAPA) - 1)
        contagem[(faixa, quando.weekday())] += 1
    maior = max(contagem.values(), default=0)
    niveis = [[(ceil(contagem[(f, d)] / maior * 4) if maior else 0) for d in range(7)] for f in range(len(HORAS_MAPA))]
    pico = '—'
    if maior:
        f, d = max(contagem, key=contagem.get)
        pico = f'{DIAS7_LONGO[d]} {HORAS_MAPA[f]:02d}h'
    return {'dias': DIAS7, 'horas': [f'{h:02d}h' for h in HORAS_MAPA], 'niveis': niveis, 'nomes': NIVEIS, 'pico': pico}


def _dias_de_casa(aluno, hoje):
    """(dias que o aluno ficou ou está ficando, se saiu). None quando não dá para saber."""
    if not aluno.data_cadastro:
        return None
    entrou = aluno.data_cadastro.date()
    if aluno.ativo:
        return (hoje - entrou).days, False
    if aluno.data_inativacao is None:
        return None                   # inativado antes de o sistema guardar a data: não se sabe quanto ficou
    return (aluno.data_inativacao.date() - entrou).days, True


def _retencao(alunos, hoje):
    """
    "Quanto tempo o aluno fica": para cada marco (30, 60... dias), dos alunos matriculados há pelo
    menos esse tempo, quantos por cento continuaram ativos até lá. Marco sem nenhum aluno na base
    fica de fora; sem nenhum marco além do zero, devolve listas vazias ("sem dado").
    """
    historico = [(aluno, _dias_de_casa(aluno, hoje)) for aluno in alunos]
    historico = [(a, h) for a, h in historico if h is not None]
    labels, valores = [], []
    for marco in MARCOS_DE_RETENCAO:
        base = [h for a, h in historico if (hoje - a.data_cadastro.date()).days >= marco]
        if not base:
            break
        ficaram = sum(1 for dias, saiu in base if not saiu or dias >= marco)
        labels.append(str(marco))
        valores.append(round(ficaram / len(base) * 100))
    if len(valores) < 2:
        return {'labels': [], 'valores': [], 'meta': None}
    return {'labels': labels, 'valores': valores, 'meta': None}   # a meta de retenção vem de Configurações


def _fim_do_mes(ano, mes):
    proximo = date(ano + (mes == 12), mes % 12 + 1, 1)
    return proximo - timedelta(days=1)


def _comparativo(alunos, hoje, checkin):
    """
    "Este mês contra o anterior": churn, inadimplência e ausentes. Cada linha só aparece se der
    para calcular os DOIS meses; senão fica de fora (melhor que mostrar um zero inventado).
    """
    ano_ant, mes_ant = _mes_antes(hoje.year, hoje.month)
    fim_ant = _fim_do_mes(ano_ant, mes_ant)
    inicio_ant, inicio_atu = date(ano_ant, mes_ant, 1), date(hoje.year, hoje.month, 1)

    def ativo_em(aluno, dia):
        """O aluno era ativo no fim daquele dia? None se não dá para saber."""
        if not aluno.data_cadastro or aluno.data_cadastro.date() > dia:
            return False
        if aluno.ativo:
            return True
        return None if aluno.data_inativacao is None else aluno.data_inativacao.date() > dia

    def saiu_entre(aluno, de, ate):
        return (not aluno.ativo) and aluno.data_inativacao is not None and de <= aluno.data_inativacao.date() <= ate

    linhas = []
    # churn: quem saiu no mês, sobre quem era ativo quando o mês começou
    base_ant = sum(1 for a in alunos if ativo_em(a, inicio_ant - timedelta(days=1)))
    base_atu = sum(1 for a in alunos if ativo_em(a, fim_ant))
    if base_ant and base_atu:
        linhas.append({'nome': 'Churn', 'unidade': '%', 'casas': 1,
                       'ant': sum(1 for a in alunos if saiu_entre(a, inicio_ant, fim_ant)) / base_ant * 100,
                       'atu': sum(1 for a in alunos if saiu_entre(a, inicio_atu, hoje)) / base_atu * 100})

    # inadimplência: ativos com vencimento passado, sobre os ativos (no fim do mês passado e hoje)
    pagas = defaultdict(list)       # aluno -> [(dia em que foi paga, vencimento que ela garantiu)]
    for p in painel_service._pagamentos_da_conta():
        if p.cobranca.aluno_id and p.cobranca.data_vencimento:
            pagas[p.cobranca.aluno_id].append((p.data_pagamento.date(), p.cobranca.data_vencimento))

    def devendo_em(aluno, dia):
        vencimentos = [venc for pago_em, venc in pagas[aluno.id] if pago_em <= dia]
        return bool(vencimentos) and max(vencimentos) < dia

    ativos_ant = [a for a in alunos if ativo_em(a, fim_ant)]
    ativos_atu = [a for a in alunos if a.ativo]
    if ativos_ant and ativos_atu and pagas:
        linhas.append({'nome': 'Inadimplência', 'unidade': '%', 'casas': 1,
                       'ant': sum(1 for a in ativos_ant if devendo_em(a, fim_ant)) / len(ativos_ant) * 100,
                       'atu': sum(1 for a in ativos_atu if devendo_em(a, hoje)) / len(ativos_atu) * 100})

    # ausentes há mais de 15 dias (só com check-in): contagem no fim do mês passado e hoje
    if checkin:
        ultimas = defaultdict(list)
        for aluno_id, quando in da_conta(Frequencia).with_entities(Frequencia.aluno_id, Frequencia.data_hora_entrada):
            ultimas[aluno_id].append(quando.date())

        def ausentes_em(dia, grupo):
            total = 0
            for a in grupo:
                ate_o_dia = [d for d in ultimas[a.id] if d <= dia]
                total += bool(ate_o_dia) and (dia - max(ate_o_dia)).days > frequencia_service.DIAS_AUSENTE
            return total
        if any(d <= fim_ant for datas in ultimas.values() for d in datas):
            linhas.append({'nome': 'Ausentes +15d', 'unidade': '', 'casas': 0,
                           'ant': ausentes_em(fim_ant, ativos_ant), 'atu': ausentes_em(hoje, ativos_atu)})

    for linha in linhas:
        teto = max(linha['ant'], linha['atu'], 1) * 1.4      # a régua vai até 40% além do maior valor
        linha['max'] = teto
        linha['p_ant'], linha['p_atu'] = round(linha['ant'] / teto * 100), round(linha['atu'] / teto * 100)
    return linhas


def _nota_de_risco(linha, dias_sem_vir, dias_de_casa):
    """
    Nota de 0 a 100: quanto MENOR, mais perto de cancelar. Começa em 100 e perde pontos por:
      - pagamento atrasado: 3 pontos por dia, até 60;
      - sumiço (só com check-in): 2 pontos por dia além de uma semana sem vir, até 50;
      - pouco tempo de casa: 10 pontos nos primeiros 30 dias (é quando mais se desiste).
    Devolve (nota, motivo principal).
    """
    perde_pagamento = min(linha['dias_atraso'] * 3, 60) if linha['vencido'] else 0
    perde_frequencia = min(max(dias_sem_vir - 7, 0) * 2, 50) if dias_sem_vir is not None else 0
    perde_novato = 10 if (dias_de_casa is not None and dias_de_casa < 30) else 0
    nota = max(100 - perde_pagamento - perde_frequencia - perde_novato, 0)
    if perde_pagamento >= perde_frequencia and perde_pagamento:
        motivo = f"{linha['dias_atraso']} dia{'s' if linha['dias_atraso'] != 1 else ''} sem pagar"
    elif perde_frequencia:
        motivo = f'{dias_sem_vir} dias sem vir'
    else:
        motivo = 'matrícula recente'
    return nota, motivo


def _risco(alunos, hoje, checkin, limite=5):
    """Alunos ativos com nota abaixo de 50, do pior para o melhor. Devolve (os `limite` primeiros, total)."""
    vencimento, em_aberto = vencimentos_da_conta(), cobrancas_em_aberto_da_conta()
    sem_vir = (frequencia_service.dias_sem_vir(hoje) or {}) if checkin else {}
    notas = []
    for a in alunos:
        if not a.ativo:
            continue
        linha = linha_do_aluno(a, vencimento.get(a.id), hoje, em_aberto.get(a.id))
        casa = (hoje - a.data_cadastro.date()).days if a.data_cadastro else None
        nota, motivo = _nota_de_risco(linha, sem_vir.get(a.id), casa)
        if nota < 50:
            notas.append({'aluno': linha, 'score': nota, 'motivo': motivo})
    notas.sort(key=lambda x: (x['score'], x['aluno']['nome']))
    return notas[:limite], len(notas)


# ------------------------------------------------------------------ a tela
def contexto_do_painel(argumentos, hoje=None):
    """Todas as variáveis de relatorios/admin.html."""
    hoje = hoje or date.today()
    periodo = argumentos.get('periodo') if argumentos.get('periodo') in PERIODOS else 'mes'
    inicio, fim, ant_inicio, ant_fim, periodo_txt, periodo_de = intervalo(periodo, hoje)
    checkin = bool(current_user.conta.checkin_ativo)
    pagamentos = painel_service._pagamentos_da_conta()
    alunos = da_conta(Aluno).all()
    painel = painel_service.montar_painel(hoje)['k']       # a receber, em atraso e ticket: os números do painel

    do_periodo = _no_intervalo(pagamentos, inicio, fim)
    recebido = sum(float(p.valor_pago) for p in do_periodo)
    recebido_antes = sum(float(p.valor_pago) for p in _no_intervalo(pagamentos, ant_inicio, ant_fim))

    custos = custos_da_conta()
    custos_total = sum(c['valor'] for c in custos)
    # os custos são por mês: num período de 3 meses o mínimo é 3 vezes a soma; numa semana, 7/30 dela
    minimo = custos_total * (7 / 30 if periodo == 'semana' else MESES_DO_PERIODO[periodo])

    ano_ant, mes_ant = _mes_antes(hoje.year, hoje.month)
    fat_mes_passado = sum(float(p.valor_pago) for p in pagamentos if (p.data_pagamento.year, p.data_pagamento.month) == (ano_ant, mes_ant))
    ticket_delta = ''
    if fat_mes_passado and painel['ativos']:
        diferenca = painel['ticket'] - fat_mes_passado / painel['ativos']
        ticket_delta = f"{'+' if diferenca >= 0 else '−'}R$ {reais_txt(abs(diferenca))} vs {MESES[mes_ant - 1]}"

    risco, risco_total = _risco(alunos, hoje, checkin)
    filtro = _filtro(argumentos)
    return {
        'periodo': periodo, 'periodos': PERIODOS, 'periodo_txt': periodo_txt, 'periodo_de': periodo_de,
        'mes_txt': f'{MESES[hoje.month - 1].capitalize()} de {hoje.year}' if periodo == 'mes' else periodo_txt.capitalize(),
        'recebido': recebido, 'formas': _formas(do_periodo), 'variacao': _variacao(recebido, recebido_antes, periodo, hoje),
        'minimo': minimo, 'sobra': recebido - minimo, 'gauge_max': _teto_do_medidor(recebido, minimo),
        'custos': custos, 'custos_total': custos_total,
        'grafico': _receita_12_meses(pagamentos, hoje),
        'ticket': painel['ticket'], 'ticket_delta': ticket_delta,
        'a_receber': painel['vencimentos_valor'], 'em_atraso': painel['inadimplencia'],
        'mapa': _mapa_de_movimento(hoje) if checkin else {'dias': DIAS7, 'horas': [], 'niveis': [], 'nomes': NIVEIS, 'pico': '—'},
        'retencao': _retencao(alunos, hoje),
        'comparativo': _comparativo(alunos, hoje, checkin),
        'risco': risco, 'risco_total': risco_total,
        'lancamentos': _lancamentos(pagamentos, inicio, fim, hoje, filtro), 'filtro': filtro,
        'ultimo_fechamento': None,       # o sistema ainda não guarda quando o fechamento foi baixado
    }
