"""
[back-17-personal] Regras da AGENDA DE SESSÕES (templates/agenda/). Só existe na conta de personal trainer.

  - Marcar: aluno ativo da conta, de hoje até um ano à frente, num horário da grade, num local ligado
    em Configurações. O mesmo profissional não fica com duas sessões no mesmo dia e horário.
  - Concluir ("marcar presença"): a sessão vira `concluida` e ABATE 1 do saldo, se o aluno tinha saldo.
    Sem saldo, a sessão é fechada do mesmo jeito e fica fora do pacote (`abateu = False`).
  - Cancelar: vira `cancelada` e não abate.
  - "Toda semana": ao CONCLUIR uma sessão semanal, o sistema já marca a da semana seguinte, no mesmo
    horário e local. Cancelar interrompe a repetição.

O sistema não manda aviso ao aluno. A sessão nasce `agendada`; os estados "confirmada", "a confirmar"
e "remarcada" do desenho dependem de o aluno responder a um lembrete automático, que não existe.
O lembrete da véspera aparece na fila de Mensagens, para a pessoa enviar pelo WhatsApp.
"""
from datetime import date, datetime, timedelta

from flask_login import current_user

from app.extensions.database import db
from app.helpers.conta import da_conta
from app.helpers.whatsapp import so_numeros
from app.models import LOCAIS_DE_ATENDIMENTO, SESSAO_AGENDADA, SESSAO_CANCELADA, SESSAO_CONCLUIDA, SESSAO_SEMANAL, SESSAO_UNICA, Sessao
from app.services import pacote_service

HORARIOS = [f'{h:02d}:{m}' for h in range(6, 22) for m in ('00', '30')]     # 06:00 a 21:30, de meia em meia hora
DURACOES = [('30', '30 minutos'), ('45', '45 minutos'), ('60', '1 hora'), ('90', '1 hora e meia')]
MARCAR_ATE_DIAS = 365
DIAS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
CHIP = {SESSAO_AGENDADA: ('blue', 'Agendada'), SESSAO_CONCLUIDA: ('green', 'Concluída'), SESSAO_CANCELADA: ('slate', 'Cancelada')}
# (chave, nome, nome curto, descrição). A descrição do estúdio é o endereço da conta.
LOCAIS = [('estudio', 'Estúdio', 'Estúdio', None), ('casa', 'Casa do aluno', 'Casa', 'endereço do cadastro'),
          ('parque', 'Parque', 'Parque', 'treino ao ar livre'), ('online', 'Online', 'Online', 'chamada de vídeo')]


class SessaoInvalida(Exception):
    """Pedido recusado. `erros` é {campo: mensagem} e str(erro) é o aviso do topo da tela."""

    def __init__(self, mensagem, erros=None):
        super().__init__(mensagem)
        self.erros = erros or {}


# ------------------------------------------------------------------ locais de atendimento
def locais():
    """Os quatro locais, com `ativo` conforme Configurações: [{chave, nome, curto, sub, ativo}]"""
    conta = current_user.conta
    ligados = set((conta.locais_ativos or ','.join(LOCAIS_DE_ATENDIMENTO)).split(','))
    return [{'chave': chave, 'nome': nome, 'curto': curto, 'ativo': chave in ligados,
             'sub': sub or (conta.endereco or 'endereço não informado')} for chave, nome, curto, sub in LOCAIS]


def salvar_locais(formulario):
    """Liga e desliga os locais e grava o endereço do estúdio. Pelo menos um local precisa ficar ligado."""
    ligados = [chave for chave in LOCAIS_DE_ATENDIMENTO if chave in set(formulario.getlist('ativos'))]
    if not ligados:
        raise SessaoInvalida('Deixe pelo menos um local ligado.')
    conta = current_user.conta
    conta.locais_ativos = ','.join(ligados)
    endereco = ' '.join((formulario.get('endereco_estudio') or '').split())[:200]
    if endereco:
        conta.endereco = endereco
    db.session.commit()


# ------------------------------------------------------------------ formato das telas
def _fim(hora, minutos):
    return (datetime.strptime(hora, '%H:%M') + timedelta(minutes=minutos)).strftime('%H:%M')


def _duracao_txt(minutos):
    if minutos < 60:
        return f'{minutos}min'
    horas, resto = divmod(minutos, 60)
    return f'{horas}h' if not resto else f'{horas}h{resto:02d}'


def _titulo_do_dia(dia, hoje):
    if dia == hoje:
        return f"Hoje, {dia.strftime('%d/%m')}"
    if dia == hoje + timedelta(days=1):
        return f"Amanhã, {dia.strftime('%d/%m')}"
    return f"{DIAS[dia.weekday()]}, {dia.strftime('%d/%m')}"


def _aluno_para_a_tela(aluno, pacote):
    return {'id': aluno.id, 'nome': aluno.nome or 'Aluno sem nome', 'telefone': aluno.telefone or '', 'valor': pacote['valor'],
            'pacote': pacote, 'vence_txt': pacote_service.situacao_txt(aluno, pacote), 'plano': pacote['nome']}


def para_a_tela(sessao, hoje=None):
    """A sessão com tudo que as telas da agenda mostram."""
    from app.services import treino_service
    hoje = hoje or date.today()
    aluno = sessao.aluno
    pacote = pacote_service.pacote_do(aluno)
    local = next((l for l in locais() if l['chave'] == sessao.local), None) or {'nome': 'Local', 'curto': 'Local', 'sub': ''}
    ficha = treino_service.ficha_do(aluno)
    return {'id': sessao.id, 'dia': sessao.data, 'hora': sessao.hora, 'fim': _fim(sessao.hora, sessao.duracao), 'duracao': sessao.duracao,
            'dur_txt': _duracao_txt(sessao.duracao), 'dur_longo': dict(DURACOES).get(str(sessao.duracao), f'{sessao.duracao} minutos'),
            'data_txt': f"{sessao.data.strftime('%d/%m/%Y')} · {DIAS[sessao.data.weekday()].lower()}",
            'quando_txt': f'Hoje às {sessao.hora}' if sessao.data == hoje else f'{_titulo_do_dia(sessao.data, hoje)} às {sessao.hora}',
            # o botão de marcar presença aparece no dia da sessão e também depois dele (sessão que ficou sem fechar)
            'hoje': sessao.data <= hoje,
            'tipo': 'Treino', 'treino': ficha.nome if ficha else 'sem ficha de treino', 'status': sessao.status, 'chip': CHIP[sessao.status],
            'local': sessao.local, 'local_obj': local, 'repete': sessao.repete, 'aluno': _aluno_para_a_tela(aluno, pacote), 'pacote': pacote}


def sessao_da_conta(id):
    """A sessão, se for da conta de quem está logado; senão None."""
    return da_conta(Sessao).filter_by(id=id).first()


# ------------------------------------------------------------------ agenda
def contexto_da_agenda(hoje=None):
    """Variáveis de agenda/index.html: as sessões de hoje em diante (menos as canceladas), agrupadas por dia."""
    hoje = hoje or date.today()
    vivas = (da_conta(Sessao).filter(Sessao.data >= hoje, Sessao.status != SESSAO_CANCELADA)
             .order_by(Sessao.data, Sessao.hora, Sessao.id).all())
    grupos = []
    for sessao in vivas:
        if not grupos or grupos[-1]['dia'] != sessao.data:
            grupos.append({'dia': sessao.data, 'titulo': _titulo_do_dia(sessao.data, hoje), 'itens': []})
        grupos[-1]['itens'].append(para_a_tela(sessao, hoje))
    for grupo in grupos:
        n = len(grupo['itens'])
        grupo['sub'] = f"{n} {'sessão' if n == 1 else 'sessões'} · {_duracao_txt(sum(i['duracao'] for i in grupo['itens']))} de trabalho"
    de_hoje = grupos[0]['itens'] if grupos and grupos[0]['dia'] == hoje else []
    return {'stats': {'hoje': len(de_hoje),
                      'confirmar': 0,       # depende da resposta do aluno a um lembrete automático, que não existe
                      'valor_dia': sum(i['pacote']['valor_sessao'] for i in de_hoje)},
            'grupos': grupos, 'acabando': pacote_service.acabando(pacote_service.ACABANDO_NA_AGENDA),
            'hoje_txt': f"{DIAS[hoje.weekday()]}, {hoje.strftime('%d/%m')}"}


def sessoes_de_hoje(hoje=None):
    """Quantas sessões estão marcadas para hoje (card do painel)."""
    return da_conta(Sessao).filter(Sessao.data == (hoje or date.today()), Sessao.status != SESSAO_CANCELADA).count()


# ------------------------------------------------------------------ marcar e remarcar
def sessao_para_remarcar(id, aluno):
    """Sessão ainda agendada da conta e deste aluno; senão None."""
    if not id:
        return None
    return da_conta(Sessao).filter_by(id=id, aluno_id=aluno.id, status=SESSAO_AGENDADA).first()


def contexto_do_formulario(aluno, erros=None, f=None, remarcar=None, hoje=None):
    """Variáveis de agenda/nova.html quando o aluno já foi escolhido."""
    hoje = hoje or date.today()
    ligados = [l for l in locais() if l['ativo']]
    padrao = {'data': (remarcar.data if remarcar else hoje + timedelta(days=1)).strftime('%d/%m/%Y'),
              'horario': remarcar.hora if remarcar else '09:00', 'duracao': str(remarcar.duracao if remarcar else 60),
              'local': remarcar.local if remarcar else (ligados[0]['chave'] if ligados else 'estudio'),
              'repete': remarcar.repete if remarcar else SESSAO_UNICA}
    valores = {campo: ((f.get(campo) if f else None) or valor) for campo, valor in padrao.items()}
    pacote = pacote_service.pacote_do(aluno)
    return {'aluno': _aluno_para_a_tela(aluno, pacote), 'achados': [], 'q': '', 'erros': erros or {}, 'f': valores,
            'remarcar': remarcar.id if remarcar else None, 'horarios': HORARIOS, 'duracoes': DURACOES, 'locais': ligados,
            'avulso': pacote_service.e_avulso(aluno.plano)}


def marcar(aluno, formulario, hoje=None):
    """
    Marca uma sessão para o aluno, ou muda a que está sendo remarcada (`remarcar` = id de uma sessão agendada dele).
    Devolve (sessão, remarcou?). Levanta SessaoInvalida com os erros por campo.
    """
    hoje = hoje or date.today()
    if not aluno.ativo:
        raise SessaoInvalida('Este aluno está inativo. Reative o cadastro antes de marcar sessão.')
    erros = {}
    try:
        dia = datetime.strptime((formulario.get('data') or '').strip(), '%d/%m/%Y').date()
        if dia < hoje:
            erros['data'] = 'Escolha hoje ou uma data futura.'
        elif dia > hoje + timedelta(days=MARCAR_ATE_DIAS):
            erros['data'] = 'Escolha uma data dentro de um ano.'
    except ValueError:
        dia = None
        erros['data'] = 'Data inválida. Use dd/mm/aaaa.'
    hora = (formulario.get('horario') or '').strip()
    if hora not in HORARIOS:
        erros['horario'] = 'Escolha um horário.'
    duracao = formulario.get('duracao') if formulario.get('duracao') in dict(DURACOES) else '60'
    ligados = [l['chave'] for l in locais() if l['ativo']]
    local = formulario.get('local') if formulario.get('local') in ligados else (ligados[0] if ligados else 'estudio')
    antiga = sessao_para_remarcar(formulario.get('remarcar', type=int), aluno)
    if not erros:
        ocupado = da_conta(Sessao).filter(Sessao.status == SESSAO_AGENDADA, Sessao.data == dia, Sessao.hora == hora,
                                         Sessao.instrutor_id == current_user.id)
        if antiga:
            ocupado = ocupado.filter(Sessao.id != antiga.id)
        outra = ocupado.first()
        if outra:
            erros['horario'] = f"Você já tem sessão com {(outra.aluno.nome or 'outro aluno').split()[0]} neste horário."
    if erros:
        raise SessaoInvalida('Revise os campos destacados.', erros)

    sessao = antiga or Sessao(conta_id=current_user.conta_id, aluno_id=aluno.id, status=SESSAO_AGENDADA)
    sessao.instrutor_id = current_user.id
    sessao.data, sessao.hora, sessao.duracao, sessao.local = dia, hora, int(duracao), local
    sessao.repete = SESSAO_SEMANAL if formulario.get('repete') == SESSAO_SEMANAL else SESSAO_UNICA
    db.session.add(sessao)
    db.session.commit()
    return sessao, antiga is not None


# ------------------------------------------------------------------ concluir e cancelar
def concluir(sessao, hoje=None):
    """
    Marca presença. Devolve (pacote do aluno depois, já estava concluída?). Sessão futura ou cancelada
    levanta SessaoInvalida. Chamar de novo numa sessão concluída não abate outra vez.
    """
    hoje = hoje or date.today()
    if sessao.status == SESSAO_CONCLUIDA:
        return pacote_service.pacote_do(sessao.aluno), True
    if sessao.status != SESSAO_AGENDADA:
        raise SessaoInvalida('Esta sessão foi cancelada.')
    if sessao.data > hoje:
        raise SessaoInvalida('Só dá para marcar presença no dia da sessão.')
    sessao.status, sessao.concluida_em = SESSAO_CONCLUIDA, datetime.utcnow()
    sessao.abateu = pacote_service.pacote_do(sessao.aluno)['saldo'] > 0      # sem saldo, fica fora do pacote
    if sessao.repete == SESSAO_SEMANAL:
        _marcar_a_da_semana_seguinte(sessao)
    db.session.commit()
    pacote_service.esquecer()
    return pacote_service.pacote_do(sessao.aluno), False


def _marcar_a_da_semana_seguinte(sessao):
    """A repetição semanal anda uma semana por vez: fechou esta, nasce a próxima (se o horário estiver livre)."""
    proxima = sessao.data + timedelta(days=7)
    ja_tem = da_conta(Sessao).filter(Sessao.status == SESSAO_AGENDADA, Sessao.data == proxima, Sessao.hora == sessao.hora,
                                     Sessao.instrutor_id == sessao.instrutor_id).first()
    if ja_tem or not sessao.aluno.ativo:
        return
    db.session.add(Sessao(conta_id=sessao.conta_id, aluno_id=sessao.aluno_id, instrutor_id=sessao.instrutor_id, data=proxima, hora=sessao.hora,
                          duracao=sessao.duracao, local=sessao.local, repete=SESSAO_SEMANAL, status=SESSAO_AGENDADA))


def cancelar(sessao):
    """Cancela uma sessão agendada. Não mexe no saldo. Sessão já fechada levanta SessaoInvalida."""
    if sessao.status == SESSAO_CONCLUIDA:
        raise SessaoInvalida('Esta sessão já foi fechada e não pode ser cancelada.')
    sessao.status = SESSAO_CANCELADA
    db.session.commit()


# ------------------------------------------------------------------ para outras telas
def de_amanha(hoje=None):
    """As sessões agendadas para amanhã, de alunos ativos (lembrete da véspera na fila de mensagens)."""
    amanha = (hoje or date.today()) + timedelta(days=1)
    sessoes = da_conta(Sessao).filter(Sessao.status == SESSAO_AGENDADA, Sessao.data == amanha).order_by(Sessao.hora, Sessao.id).all()
    return [s for s in sessoes if s.aluno.ativo]


def telefone_do(sessao_tela):
    return so_numeros(sessao_tela['aluno']['telefone'])


def alunos_para_marcar(q=''):
    """Alunos ativos da conta para escolher com quem é a sessão (mesma busca de "usar com um aluno" das fichas)."""
    from app.services import treino_service
    return treino_service.alunos_para_atribuir(q, limite=8)
