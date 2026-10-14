"""
[back-15-avaliacoes] Regras da AVALIAÇÃO FÍSICA do front novo (templates/avaliacoes/).

São duas coisas separadas:

  - a AGENDA (`AvaliacaoAgendada`): o horário marcado. Qualquer pessoa da equipe marca e vê.
  - a AVALIAÇÃO FEITA (`AvaliacaoFisica`): anamnese, medidas, dobras e testes. São dados de saúde
    (sensíveis pela LGPD): só o dono e os instrutores registram (PAPEIS_QUE_AVALIAM); a equipe toda
    abre o resultado (PAPEIS_QUE_VEEM_O_RESULTADO). [back-22-ajustes-de-produto] antes: a recepção não abria.

Três regras que valem para o módulo inteiro:

  1. É MEDIDA, NÃO DIAGNÓSTICO. O sistema guarda número; não classifica ("obeso", "risco alto")
     nem tem campo de laudo.
  2. IMC e relação cintura/quadril NUNCA vêm do formulário. O servidor calcula ao salvar, para o
     número gravado bater sempre com o peso e a altura da mesma linha.
  3. O que o banco não tem aparece como "sem dado": aluno que nunca foi avaliado não entra na
     conta de "avaliações vencidas".
"""
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask_login import current_user
from sqlalchemy import and_, func, or_

from app.extensions.database import db
from app.helpers.conta import da_conta
from app.helpers.whatsapp import link_do_whatsapp, so_numeros
from app.models import (AGENDA_A_CONFIRMAR, AGENDA_CONFIRMADA, AGENDA_REALIZADA, AGENDA_REMARCADA, AVALIACAO_AVULSA, AVALIACAO_INCLUSA,
                        AVALIACAO_PRIMEIRA, AVALIACAO_REAVALIACAO, PAPEL_INSTRUTOR, PAPEL_PROPRIETARIO, PAPEL_RECEPCAO, Aluno, AvaliacaoAgendada,
                        AvaliacaoFisica, User)

PAPEIS_QUE_AVALIAM = (PAPEL_PROPRIETARIO, PAPEL_INSTRUTOR)   # quem registra a avaliação (dado de saúde)
# [back-22-ajustes-de-produto] quem abre o resultado e o histórico. Antes: os mesmos de PAPEIS_QUE_AVALIAM (a recepção não via as medidas).
# Decisão do Adauto em 14/10/2026: a recepção pode ver.
PAPEIS_QUE_VEEM_O_RESULTADO = (PAPEL_PROPRIETARIO, PAPEL_RECEPCAO, PAPEL_INSTRUTOR)
HORARIOS = [f'{h:02d}:00' for h in range(6, 21)]              # 06:00 a 20:00, de hora em hora
VALIDADE_DIAS = 180                                           # depois disso a avaliação do aluno conta como "vencida"
DIAS_ATE_A_DATA_SUGERIDA = 2
AGENDAR_ATE_DIAS = 365
ABERTOS = (AGENDA_CONFIRMADA, AGENDA_A_CONFIRMAR)             # horários que ainda vão acontecer
CHIP_DO_STATUS = {AGENDA_CONFIRMADA: ('green', 'Confirmada'), AGENDA_A_CONFIRMAR: ('yellow', 'A confirmar'), AGENDA_REMARCADA: ('slate', 'Remarcada')}
SEMANA = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

# Medidas do formulário: (campo, nome para o aviso, mínimo, máximo, obrigatório). Fora da faixa é erro de digitação.
MEDIDAS = [
    ('peso_kg', 'Peso', 20, 400, True), ('altura_cm', 'Altura', 80, 250, True),
    ('cintura_cm', 'Cintura', 10, 300, False), ('quadril_cm', 'Quadril', 10, 300, False), ('braco_d_cm', 'Braço direito', 10, 300, False),
    ('coxa_d_cm', 'Coxa direita', 10, 300, False), ('torax_cm', 'Tórax', 10, 300, False), ('panturrilha_cm', 'Panturrilha', 10, 300, False),
    ('dobra_triceps', 'Dobra do tríceps', 1, 99, False), ('dobra_subescapular', 'Dobra subescapular', 1, 99, False),
    ('dobra_suprailiaca', 'Dobra supra-ilíaca', 1, 99, False), ('dobra_abdominal', 'Dobra abdominal', 1, 99, False),
    ('dobra_coxa', 'Dobra da coxa', 1, 99, False), ('teste_flexibilidade', 'Sentar e alcançar', -50, 99, False),
]
CONTAGENS = [('teste_flexao', 'Flexões em 1 minuto'), ('teste_abdominal', 'Abdominais em 1 minuto')]   # inteiros de 0 a 500


class AvaliacaoInvalida(Exception):
    """Pedido recusado. `erros` é {campo: mensagem} (agendar) e str(erro) é o aviso do topo da tela."""

    def __init__(self, mensagem, erros=None):
        super().__init__(mensagem)
        self.erros = erros or {}


# ------------------------------------------------------------------ ajudantes
def pode_avaliar():
    """Quem está logado registra avaliação? (dono e instrutor)"""
    return current_user.papel in PAPEIS_QUE_AVALIAM


def pode_ver_o_resultado():
    """[back-22-ajustes-de-produto] Quem está logado abre o resultado e o histórico de avaliações? (hoje, a equipe toda)"""
    return current_user.papel in PAPEIS_QUE_VEEM_O_RESULTADO


def _dmy(d):
    return d.strftime('%d/%m/%Y')


def _br(valor, casas=1):
    """Número no formato brasileiro: 68.4 -> '68,4'."""
    return f'{float(valor):.{casas}f}'.replace('.', ',')


def _nome(usuario):
    return ' '.join(p for p in (usuario.nome, getattr(usuario, 'sobrenome', None)) if p) if usuario else 'Não informado'


def avaliadores():
    """Quem pode ser o avaliador: dono e instrutores ativos da conta. [(id em texto, nome)]"""
    usuarios = da_conta(User).filter(User.ativo.is_(True), User.papel.in_(PAPEIS_QUE_AVALIAM)).order_by(func.lower(User.nome)).all()
    return [(str(u.id), _nome(u)) for u in usuarios]


def historico_do(aluno):
    """Avaliações feitas do aluno, da mais recente para a mais antiga."""
    return da_conta(AvaliacaoFisica).filter_by(aluno_id=aluno.id).order_by(AvaliacaoFisica.data.desc(), AvaliacaoFisica.id.desc()).all()


def ultima_do(aluno):
    return da_conta(AvaliacaoFisica).filter_by(aluno_id=aluno.id).order_by(AvaliacaoFisica.data.desc(), AvaliacaoFisica.id.desc()).first()


def avaliacao_da_conta(id):
    """A avaliação feita, se for da conta de quem está logado; senão None."""
    return da_conta(AvaliacaoFisica).filter_by(id=id).first()


def _ultima_data_por_aluno():
    """{aluno_id: data da última avaliação feita} de toda a conta, numa consulta só."""
    linhas = (db.session.query(AvaliacaoFisica.aluno_id, func.max(AvaliacaoFisica.data))
              .filter(AvaliacaoFisica.conta_id == current_user.conta_id).group_by(AvaliacaoFisica.aluno_id).all())
    return dict(linhas)


def _tipo_txt(agendamento, ultima_data):
    """'Primeira avaliação' ou 'Reavaliação · 90 dias' (os dias desde a última avaliação feita)."""
    if agendamento.tipo == AVALIACAO_PRIMEIRA:
        return 'Primeira avaliação'
    if ultima_data and agendamento.data > ultima_data:
        return f'Reavaliação · {(agendamento.data - ultima_data).days} dias'
    return 'Reavaliação'


def _vencidas_e_sem_avaliar(ultima_data, hoje):
    """
    Dois números sobre os alunos ATIVOS:
      - vencidas: a última avaliação feita tem mais de VALIDADE_DIAS. Quem nunca foi avaliado não conta
        (não há avaliação para vencer).
      - sem avaliar: as vencidas MAIS quem nunca foi avaliado e está cadastrado há mais de VALIDADE_DIAS
        (para esses o banco sustenta a frase "sem avaliar há 6 meses": é a data do cadastro).
    """
    vencidas = nunca = 0
    for aluno_id, cadastro in da_conta(Aluno).filter(Aluno.ativo.is_(True)).with_entities(Aluno.id, Aluno.data_cadastro).all():
        ultima = ultima_data.get(aluno_id)
        if ultima:
            vencidas += (hoje - ultima).days > VALIDADE_DIAS
        elif cadastro and (hoje - cadastro.date()).days > VALIDADE_DIAS:
            nunca += 1
    return vencidas, vencidas + nunca


# ------------------------------------------------------------------ agenda
def contexto_da_agenda(hoje=None):
    """Variáveis de avaliacoes/agenda.html."""
    hoje = hoje or date.today()
    amanha = hoje + timedelta(days=1)
    ultima_data = _ultima_data_por_aluno()
    abertos = (da_conta(AvaliacaoAgendada).filter(AvaliacaoAgendada.status.in_(ABERTOS))
               .order_by(AvaliacaoAgendada.data, AvaliacaoAgendada.hora, AvaliacaoAgendada.id).all())
    itens = [{'id': a.id, 'aluno': {'id': a.aluno_id, 'nome': a.aluno.nome or 'Aluno sem nome'}, 'dia': a.data, 'hora': a.hora,
              'tipo': _tipo_txt(a, ultima_data.get(a.aluno_id)), 'chip': CHIP_DO_STATUS[a.status],
              'dia_txt': f"{SEMANA[a.data.weekday()]} {a.data.strftime('%d/%m')}"} for a in abertos]
    grupos = [
        # horário que passou e ninguém registrou a avaliação: fica à vista até ser remarcado ou feito
        {'titulo': 'Não realizadas', 'itens': [i for i in itens if i['dia'] < hoje], 'com_dia': True},
        {'titulo': f"Hoje, {hoje.strftime('%d/%m')}", 'itens': [i for i in itens if i['dia'] == hoje]},
        {'titulo': f"Amanhã, {amanha.strftime('%d/%m')}", 'itens': [i for i in itens if i['dia'] == amanha]},
        {'titulo': 'Resto da semana', 'itens': [i for i in itens if amanha < i['dia'] <= hoje + timedelta(days=7)], 'com_dia': True},
        {'titulo': 'Mais adiante', 'itens': [i for i in itens if i['dia'] > hoje + timedelta(days=7)], 'com_dia': True},
    ]
    do_mes = da_conta(AvaliacaoAgendada).filter(AvaliacaoAgendada.status.in_(ABERTOS + (AGENDA_REALIZADA,)),
                                                func.extract('year', AvaliacaoAgendada.data) == hoje.year,
                                                func.extract('month', AvaliacaoAgendada.data) == hoje.month).count()
    vencidas, sem_avaliar = _vencidas_e_sem_avaliar(ultima_data, hoje)
    return {'stats': {'hoje': len(grupos[1]['itens']), 'confirmar': sum(1 for a in abertos if a.status == AGENDA_A_CONFIRMAR),
                      'vencidas': vencidas, 'mes': do_mes, 'mes_nome': MESES[hoje.month - 1]},
            'grupos': [g for g in grupos if g['itens']], 'sem_avaliar': {'qtd': sem_avaliar, 'meses': VALIDADE_DIAS // 30},
            'pode_avaliar': pode_avaliar()}


# ------------------------------------------------------------------ agendar
def agendamento_em_aberto(id, aluno=None):
    """Horário ainda em aberto da conta (e do aluno, se informado); senão None."""
    if not id:
        return None
    consulta = da_conta(AvaliacaoAgendada).filter(AvaliacaoAgendada.id == id, AvaliacaoAgendada.status.in_(ABERTOS))
    if aluno is not None:
        consulta = consulta.filter(AvaliacaoAgendada.aluno_id == aluno.id)
    return consulta.first()


def contexto_do_agendamento(aluno, erros=None, f=None, remarcar=None, hoje=None):
    """Variáveis de avaliacoes/agendar.html quando o aluno já foi escolhido."""
    hoje = hoje or date.today()
    ultima = ultima_do(aluno)
    pessoas = avaliadores()
    f = dict(f or {})
    if not f.get('avaliador'):
        # sugere quem está logado, se ele avalia; senão o primeiro da lista
        f['avaliador'] = str(current_user.id) if pode_avaliar() else (pessoas[0][0] if pessoas else '')
    plano = aluno.plano
    return {'aluno': {'id': aluno.id, 'nome': aluno.nome or 'Aluno sem nome', 'plano': plano.nome if plano else 'atual'},
            'achados': [], 'q': '', 'erros': erros or {}, 'f': f, 'horarios': HORARIOS, 'avaliadores': pessoas,
            # O sistema ainda não tem onde o dono informa o preço da avaliação avulsa: sem preço, a tela mostra
            # "cobrada à parte" e a recepção recebe pela diária avulsa do painel.
            'preco': None,
            'plano_inclui': bool(plano and (plano.avaliacoes_incluidas or 0) > 0),
            'ultima': _dmy(ultima.data) if ultima else None,
            'remarcar': remarcar.id if remarcar else None,
            'lembretes_automaticos': False,     # o sistema não envia aviso sozinho: a tela não promete
            'data_padrao': _dmy(hoje + timedelta(days=DIAS_ATE_A_DATA_SUGERIDA))}


def agendar(aluno, formulario, hoje=None):
    """
    Marca um horário para o aluno. Com `remarcar` (id de um horário em aberto dele), o antigo vira
    'remarcada'. Devolve o horário novo. Levanta AvaliacaoInvalida com os erros por campo.
    """
    hoje = hoje or date.today()
    erros = {}
    if not aluno.ativo:
        raise AvaliacaoInvalida('Este aluno está inativo. Reative o cadastro antes de agendar.')
    try:
        dia = datetime.strptime((formulario.get('data') or '').strip(), '%d/%m/%Y').date()
        if dia < hoje:
            erros['data'] = 'Escolha uma data de hoje em diante.'
        elif dia > hoje + timedelta(days=AGENDAR_ATE_DIAS):
            erros['data'] = 'Escolha uma data dentro de um ano.'
    except ValueError:
        dia = None
        erros['data'] = 'Use o formato dd/mm/aaaa.'
    hora = (formulario.get('horario') or '').strip()
    if hora not in HORARIOS:
        erros['horario'] = 'Escolha um horário.'
    pessoas = dict(avaliadores())
    avaliador = (formulario.get('avaliador') or '').strip()
    if avaliador not in pessoas:
        erros['avaliador'] = 'Escolha o avaliador.'
    antigo = None
    if formulario.get('remarcar'):
        antigo = agendamento_em_aberto(formulario.get('remarcar', type=int), aluno)
    if not erros:
        ocupado = da_conta(AvaliacaoAgendada).filter(AvaliacaoAgendada.status.in_(ABERTOS), AvaliacaoAgendada.data == dia,
                                                    AvaliacaoAgendada.hora == hora, AvaliacaoAgendada.avaliador_id == int(avaliador))
        if antigo:
            ocupado = ocupado.filter(AvaliacaoAgendada.id != antigo.id)
        if ocupado.first():
            erros['horario'] = f'{pessoas[avaliador]} já tem avaliação marcada neste horário.'
    if erros:
        # a tela não tem lugar para o erro do avaliador: quando ele é o único problema, o aviso do topo diz qual é
        raise AvaliacaoInvalida(erros['avaliador'] if list(erros) == ['avaliador'] else 'Revise a data e o horário.', erros)

    tem_anterior = ultima_do(aluno) is not None
    tipo = formulario.get('tipo')
    if tipo not in (AVALIACAO_PRIMEIRA, AVALIACAO_REAVALIACAO):
        tipo = AVALIACAO_REAVALIACAO if tem_anterior else AVALIACAO_PRIMEIRA
    novo = AvaliacaoAgendada(conta_id=current_user.conta_id, aluno_id=aluno.id, data=dia, hora=hora, tipo=tipo, status=AGENDA_CONFIRMADA,
                             avaliador_id=int(avaliador), observacao=' '.join((formulario.get('observacao') or '').split())[:200] or None,
                             cobranca=AVALIACAO_AVULSA if formulario.get('cobranca') == AVALIACAO_AVULSA else AVALIACAO_INCLUSA,
                             criado_por_id=current_user.id)
    if antigo:
        antigo.status = AGENDA_REMARCADA
    db.session.add(novo)
    db.session.commit()
    return novo


# ------------------------------------------------------------------ registrar
def _numero(texto):
    """'68,4' ou '68.4' -> Decimal; vazio -> None. Levanta ValueError se não for número."""
    texto = (texto or '').strip().replace(',', '.')
    if not texto:
        return None
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ValueError(texto)
    if not valor.is_finite():
        raise ValueError(texto)
    return valor


def ler_medidas(formulario):
    """
    Confere os números do formulário. Devolve {campo: valor ou None}. Levanta AvaliacaoInvalida no
    primeiro problema, com um aviso que diz qual campo e qual a faixa aceita.
    """
    valores = {}
    for campo, nome, minimo, maximo, obrigatorio in MEDIDAS:
        try:
            valor = _numero(formulario.get(campo))
        except ValueError:
            raise AvaliacaoInvalida(f'{nome}: use só números, como 68,4.')
        if valor is None and obrigatorio:
            raise AvaliacaoInvalida('Informe peso e altura válidos para calcular o IMC.')
        if valor is not None and not (minimo <= valor <= maximo):
            raise AvaliacaoInvalida(f'{nome}: confira o número (aceita de {minimo} a {maximo}).')
        # o banco guarda o peso com 2 casas e as outras medidas com 1: arredonda aqui para o que é gravado ser o que foi conferido
        valores[campo] = valor.quantize(Decimal('0.01') if campo == 'peso_kg' else Decimal('0.1')) if valor is not None else None
    for campo, nome in CONTAGENS:
        texto = (formulario.get(campo) or '').strip()
        if texto and not (texto.isdigit() and int(texto) <= 500):
            raise AvaliacaoInvalida(f'{nome}: use um número inteiro de 0 a 500.')
        valores[campo] = int(texto) if texto else None
    return valores


def calcular_imc(peso_kg, altura_cm):
    """IMC = peso (kg) dividido pela altura (m) ao quadrado, com 1 casa."""
    metros = Decimal(altura_cm) / 100
    return (Decimal(peso_kg) / (metros * metros)).quantize(Decimal('0.1'))


def calcular_rcq(cintura_cm, quadril_cm):
    """Relação cintura/quadril, com 2 casas. Sem uma das duas medidas não há o que calcular (None)."""
    if not cintura_cm or not quadril_cm:
        return None
    return (Decimal(cintura_cm) / Decimal(quadril_cm)).quantize(Decimal('0.01'))


def contexto_do_registro(aluno, f=None, ag=None):
    """Variáveis de avaliacoes/registrar.html. Da avaliação anterior só vem a ALTURA (não muda); o resto é medido de novo."""
    ultima = ultima_do(aluno)
    return {'aluno': {'id': aluno.id, 'nome': aluno.nome or 'Aluno sem nome'},
            'base': {'altura': _br(ultima.altura_cm, 0)} if ultima else {}, 'ag': ag, 'f': f or {},
            'fotos_ligadas': False}     # as fotos ainda não são guardadas: a tela não oferece o envio


def registrar(aluno, formulario, hoje=None):
    """Grava a avaliação feita agora por quem está logado. Devolve a AvaliacaoFisica. Levanta AvaliacaoInvalida."""
    hoje = hoje or date.today()
    medidas = ler_medidas(formulario)

    # mesmo formulário enviado duas vezes (toque duplo, voltar e reenviar): devolve a que já foi gravada
    repetida = (da_conta(AvaliacaoFisica).filter_by(aluno_id=aluno.id, data=hoje, avaliador_id=current_user.id)
                .filter(AvaliacaoFisica.criado_em >= datetime.utcnow() - timedelta(minutes=2)).order_by(AvaliacaoFisica.id.desc()).first())
    if repetida and repetida.peso_kg == medidas['peso_kg'] and repetida.altura_cm == medidas['altura_cm']:
        return repetida

    def texto(campo, limite):
        return ' '.join((formulario.get(campo) or '').split())[:limite] or None

    agendamento = agendamento_em_aberto(formulario.get('ag', type=int), aluno)
    avaliacao = AvaliacaoFisica(
        conta_id=current_user.conta_id, aluno_id=aluno.id, data=hoje, avaliador_id=current_user.id,
        agendamento_id=agendamento.id if agendamento else None,
        objetivo=texto('objetivo', 200), restricoes=(formulario.get('restricoes') or '').strip()[:1000] or None,
        medicamentos=texto('medicamentos', 200), liberacao_medica=bool(formulario.get('liberacao_medica')),
        imc=calcular_imc(medidas['peso_kg'], medidas['altura_cm']), rcq=calcular_rcq(medidas['cintura_cm'], medidas['quadril_cm']),
        anotacao=(formulario.get('anotacao') or '').strip()[:2000] or None, **medidas)
    if agendamento:
        agendamento.status = AGENDA_REALIZADA
    db.session.add(avaliacao)
    db.session.commit()
    return avaliacao


# ------------------------------------------------------------------ histórico e resultado
def _para_a_tela(e):
    """Uma avaliação feita no formato que os templates esperam (números como float; o que não foi medido fica None)."""
    def n(valor):
        return float(valor) if valor is not None else None
    return {'id': e.id, 'data': _dmy(e.data), 'avaliador': _nome(e.avaliador), 'peso': n(e.peso_kg), 'altura': n(e.altura_cm), 'imc': n(e.imc),
            'cintura': n(e.cintura_cm), 'quadril': n(e.quadril_cm), 'rcq': n(e.rcq), 'braco': n(e.braco_d_cm), 'coxa': n(e.coxa_d_cm),
            'torax': n(e.torax_cm), 'panturrilha': n(e.panturrilha_cm), 'nota': e.anotacao or ''}


def contexto_do_historico(aluno):
    """Variáveis de avaliacoes/aluno.html."""
    feitas = historico_do(aluno)
    grafico, variacao = None, 0
    if len(feitas) >= 2:
        em_ordem = list(reversed(feitas))
        anos = sorted({e.data.year for e in em_ordem})
        grafico = {'labels': [e.data.strftime('%m/%y') for e in em_ordem], 'valores': [float(e.peso_kg) for e in em_ordem],
                   'periodo': str(anos[0]) if len(anos) == 1 else f'{anos[0]} a {anos[-1]}'}
        variacao = round(float(em_ordem[-1].peso_kg - em_ordem[0].peso_kg), 1)
    return {'aluno': {'id': aluno.id, 'nome': aluno.nome or 'Aluno sem nome'}, 'hist': [_para_a_tela(e) for e in feitas],
            'grafico': grafico, 'variacao': variacao}


# (nome na tela, chave em _para_a_tela, unidade, "menor é melhor?"). A regra de "melhor" é fixa e simples:
# peso, IMC e cintura menores pintam de verde; braço e coxa maiores pintam de verde. É só a cor da variação.
COMPARADAS = [('Peso', 'peso', 'kg', True), ('IMC', 'imc', '', True), ('Cintura', 'cintura', 'cm', True),
              ('Braço direito', 'braco', 'cm', False), ('Coxa direita', 'coxa', 'cm', False)]


def _anterior_a(avaliacao):
    return (da_conta(AvaliacaoFisica).filter(AvaliacaoFisica.aluno_id == avaliacao.aluno_id, AvaliacaoFisica.id != avaliacao.id,
                                            or_(AvaliacaoFisica.data < avaliacao.data,
                                                and_(AvaliacaoFisica.data == avaliacao.data, AvaliacaoFisica.id < avaliacao.id)))
            .order_by(AvaliacaoFisica.data.desc(), AvaliacaoFisica.id.desc()).first())


def _mensagem_do_resultado(aluno, e, linhas, anterior):
    """Texto que vai pronto no WhatsApp: os números da avaliação e o que mudou. Sem interpretação."""
    partes = [f"Oi {(aluno.nome or 'aluno').split()[0]}! Segue o resultado da sua avaliação física de {e['data']}.", '',
              f"Peso: {_br(e['peso'])} kg", f"IMC: {_br(e['imc'])}"]
    for nome, chave, unidade in (('Cintura', 'cintura', 'cm'), ('Quadril', 'quadril', 'cm'), ('Braço direito', 'braco', 'cm'),
                                 ('Coxa direita', 'coxa', 'cm'), ('Tórax', 'torax', 'cm'), ('Panturrilha', 'panturrilha', 'cm')):
        if e[chave] is not None:
            partes.append(f'{nome}: {_br(e[chave])} {unidade}')
    if linhas:
        partes += ['', f"Desde {anterior['data']}:"]
        partes += [f"{l['nome']}: {'+' if l['delta'] > 0 else ''}{_br(l['delta'])} {l['un']}".replace('-', '−').rstrip() for l in linhas]
    partes += ['', f'Qualquer dúvida é só chamar. — {current_user.conta.nome}']
    return '\n'.join(partes)


def contexto_do_resultado(avaliacao):
    """Variáveis de avaliacoes/resultado.html."""
    aluno = avaliacao.aluno
    e = _para_a_tela(avaliacao)
    antes = _anterior_a(avaliacao)
    anterior = _para_a_tela(antes) if antes else None
    linhas = []
    if anterior:
        for nome, chave, unidade, menor_e_melhor in COMPARADAS:
            if e[chave] is None or anterior[chave] is None:
                continue          # só compara o que foi medido nas duas avaliações
            delta = round(e[chave] - anterior[chave], 1)
            linhas.append({'nome': nome, 'antes': anterior[chave], 'agora': e[chave], 'delta': delta,
                           'melhor': delta <= 0 if menor_e_melhor else delta >= 0, 'un': unidade})
    return {'aluno': {'id': aluno.id, 'nome': aluno.nome or 'Aluno sem nome'}, 'e': e, 'anterior': anterior, 'linhas': linhas,
            'dias': (avaliacao.data - antes.data).days if antes else None,
            'wa_url': link_do_whatsapp(aluno.telefone, _mensagem_do_resultado(aluno, e, linhas, anterior))}


# ------------------------------------------------------------------ perfil do aluno e painel
def resumo_para_o_perfil(aluno, hoje=None):
    """
    O cartão "Avaliação física" do perfil: {data, em_dia, resumo}, ou None para quem nunca foi avaliado.
    [back-22-ajustes-de-produto] antes: a recepção via só a data. Agora quem pode ver o resultado vê peso e IMC.
    """
    hoje = hoje or date.today()
    feitas = historico_do(aluno)[:2]
    if not feitas:
        return None
    ultima = feitas[0]
    if not pode_ver_o_resultado():
        resumo = 'Resultado visível para o dono e os instrutores'
    else:
        resumo = f'{_br(ultima.peso_kg)} kg · IMC {_br(ultima.imc)}'
        if len(feitas) == 2:
            delta = float(ultima.peso_kg - feitas[1].peso_kg)
            resumo += f" · {'+' if delta > 0 else ''}{_br(delta)} kg desde a anterior".replace('-', '−')
    return {'data': _dmy(ultima.data), 'em_dia': (hoje - ultima.data).days <= VALIDADE_DIAS, 'resumo': resumo}


def de_hoje_para_o_painel(hoje=None):
    """
    As avaliações marcadas para hoje, no formato do aviso e do card do painel:
    [{nome, tipo, hora, avaliador, telefone (só dígitos), aluno_id, agenda_id, status, tom, aviso}]
    """
    hoje = hoje or date.today()
    ultima_data = _ultima_data_por_aluno()
    marcadas = (da_conta(AvaliacaoAgendada).filter(AvaliacaoAgendada.status.in_(ABERTOS), AvaliacaoAgendada.data == hoje)
                .order_by(AvaliacaoAgendada.hora, AvaliacaoAgendada.id).all())
    return [{'nome': a.aluno.nome or 'Aluno sem nome', 'tipo': _tipo_txt(a, ultima_data.get(a.aluno_id)), 'hora': a.hora,
             'avaliador': _nome(a.avaliador), 'telefone': so_numeros(a.aluno.telefone), 'aluno_id': a.aluno_id, 'agenda_id': a.id,
             'tom': CHIP_DO_STATUS[a.status][0], 'status': CHIP_DO_STATUS[a.status][1],
             'aviso': None}     # o sistema não envia aviso sozinho; o lembrete entra com o módulo de mensagens
            for a in marcadas]
