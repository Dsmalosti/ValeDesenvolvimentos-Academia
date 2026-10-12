"""
[back-16-mensagens] Regras da central de MENSAGENS (templates/mensagens/index.html).

A central é a FILA DO DIA: quem a equipe deveria chamar hoje pelo WhatsApp, cada um já com o texto
escrito. São três motivos:

  - aniversário: aluno ativo que faz aniversário hoje;
  - avaliação: aluno ativo com avaliação física marcada para AMANHÃ;
  - cobrança: aluno ativo com a mensalidade vencida (só dono e recepção veem: é dinheiro).

O SISTEMA NÃO ENVIA MENSAGEM (decisão D14: gratuito). Cada linha tem um endereço `wa.me` que abre o
WhatsApp de quem está usando, na conversa do aluno, com o texto pronto; a pessoa toca em enviar.
Ao tocar no botão, a tela avisa o servidor, que grava o toque em `mensagens_enviadas`.

O texto vem dos modelos da conta (Configurações > Mensagens), com as variáveis entre colchetes
trocadas aqui: [nome] (primeiro nome), [academia], [data], [hora], [valor], [plano] e [dias].

Regra de repetição da cobrança: quem recebeu a cobrança ontem ou anteontem sai da fila de hoje
(no máximo uma a cada DIAS_ENTRE_COBRANCAS dias). Aniversário e avaliação só existem no dia.
"""
import calendar
from datetime import date, timedelta

from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from app.extensions.database import db
from app.helpers.conta import DONO_E_RECEPCAO, da_conta
from app.helpers.dinheiro import reais_txt
from app.helpers.whatsapp import link_do_whatsapp
from app.models import MENSAGEM_ANIVERSARIO, MENSAGEM_AVALIACAO, MENSAGEM_COBRANCA, Aluno, AvaliacaoAgendada, MensagemEnviada
from app.services import agenda_service, avaliacao_service, config_service, pacote_service
from app.services.situacao_service import cobrancas_em_aberto_da_conta, linha_do_aluno, vencimentos_da_conta

DIAS_ENTRE_COBRANCAS = 3
# (tipo, rótulo do filtro, ícone, cor) na ordem em que aparecem
TIPOS = [(MENSAGEM_ANIVERSARIO, 'Aniversários', 'gift', 'blue'), (MENSAGEM_AVALIACAO, 'Avaliações de amanhã', 'calendar-plus', 'teal'),
         (MENSAGEM_COBRANCA, 'Cobranças atrasadas', 'dollar', 'red')]
# [back-17-personal] na conta de personal trainer a véspera é da SESSÃO (a agenda dele), e não da avaliação física
MENSAGEM_SESSAO = 'sessao'
TIPOS_DO_PERSONAL = [TIPOS[0], (MENSAGEM_SESSAO, 'Sessões de amanhã', 'calendar-plus', 'teal'), TIPOS[2]]


def ve_cobrancas():
    """Cobrança é dinheiro: só dono e recepção veem essas linhas (o instrutor vê as outras)."""
    return current_user.papel in DONO_E_RECEPCAO


def preencher(texto, **valores):
    """Troca [nome], [data]... pelos valores. Variável sem valor fica como está, para o erro aparecer na prévia."""
    for chave, valor in valores.items():
        texto = texto.replace(f'[{chave}]', str(valor))
    return texto


def _faz_aniversario(nascimento, hoje):
    """Aniversário é hoje? Quem nasceu em 29/02 comemora em 28/02 nos anos que não são bissextos."""
    if not nascimento:
        return False
    if (nascimento.day, nascimento.month) == (hoje.day, hoje.month):
        return True
    return (nascimento.day, nascimento.month) == (29, 2) and (hoje.day, hoje.month) == (28, 2) and not calendar.isleap(hoje.year)


def fila(hoje=None):
    """
    A fila de hoje para quem está logado:
    [{id, tipo, aluno{id, nome, telefone}, contexto, texto, wa, enviada, referencia}]
    O `id` ("tipo-referência") é o que a tela devolve quando a pessoa toca em enviar.
    """
    hoje = hoje or date.today()
    amanha = hoje + timedelta(days=1)
    modelos = {m['tipo']: m['texto'] for m in config_service.modelos_de_mensagem()}
    academia = current_user.conta.nome
    ativos = da_conta(Aluno).filter(Aluno.ativo.is_(True)).order_by(Aluno.nome, Aluno.id).all()

    recentes = da_conta(MensagemEnviada).filter(MensagemEnviada.data > hoje - timedelta(days=DIAS_ENTRE_COBRANCAS)).all()
    de_hoje = {(m.tipo, m.referencia) for m in recentes if m.data == hoje}
    cobrados_ha_pouco = {m.aluno_id for m in recentes if m.tipo == MENSAGEM_COBRANCA and m.data < hoje}

    itens = []

    def entra(tipo, aluno, referencia, contexto, **variaveis):
        texto = preencher(modelos.get(tipo, ''), nome=(aluno.nome or 'aluno').split()[0], academia=academia, **variaveis)
        itens.append({'id': f'{tipo}-{referencia}', 'tipo': tipo, 'referencia': str(referencia), 'contexto': contexto, 'texto': texto,
                      'aluno': {'id': aluno.id, 'nome': aluno.nome or 'Aluno sem nome', 'telefone': aluno.telefone or ''},
                      'wa': link_do_whatsapp(aluno.telefone, texto), 'enviada': (tipo, str(referencia)) in de_hoje})

    # 1) aniversário de hoje
    for aluno in ativos:
        if _faz_aniversario(aluno.data_nascimento, hoje):
            entra(MENSAGEM_ANIVERSARIO, aluno, aluno.id, f'Completa {hoje.year - aluno.data_nascimento.year} anos hoje')

    personal = pacote_service.e_personal()
    # 2) véspera: na conta de personal, a sessão de amanhã; na academia, a avaliação física de amanhã
    if personal:
        nomes_dos_locais = {l['chave']: l['nome'].lower() for l in agenda_service.locais()}
        for sessao in agenda_service.de_amanha(hoje):
            entra(MENSAGEM_SESSAO, sessao.aluno, sessao.id, f"Sessão amanhã às {sessao.hora} · {nomes_dos_locais.get(sessao.local, 'local')}",
                  data=amanha.strftime('%d/%m'), hora=sessao.hora, local=nomes_dos_locais.get(sessao.local, 'local combinado'))
    ultima_data = {} if personal else avaliacao_service._ultima_data_por_aluno()
    marcadas = [] if personal else (da_conta(AvaliacaoAgendada).filter(AvaliacaoAgendada.status.in_(avaliacao_service.ABERTOS), AvaliacaoAgendada.data == amanha)
                                    .order_by(AvaliacaoAgendada.hora, AvaliacaoAgendada.id).all())
    for marcada in marcadas:
        if marcada.aluno.ativo:
            entra(MENSAGEM_AVALIACAO, marcada.aluno, marcada.id,
                  f'Avaliação amanhã às {marcada.hora} · {avaliacao_service._tipo_txt(marcada, ultima_data.get(marcada.aluno_id))}',
                  data=amanha.strftime('%d/%m'), hora=marcada.hora)

    # 3) cobrança atrasada (só para quem pode ver dinheiro)
    if ve_cobrancas():
        vencimento, em_aberto = vencimentos_da_conta(), cobrancas_em_aberto_da_conta()
        atrasados = [(linha_do_aluno(a, vencimento.get(a.id), hoje, em_aberto.get(a.id)), a) for a in ativos]
        for linha, aluno in sorted((x for x in atrasados if x[0]['vencido']), key=lambda x: -x[0]['dias_atraso']):
            if aluno.id in cobrados_ha_pouco:
                continue          # já foi cobrado ontem ou anteontem: volta à fila depois
            valor = f"R$ {reais_txt(linha['valor'])}"
            venceu = linha['vence'] if linha['vence_data'] else None
            entra(MENSAGEM_COBRANCA, aluno, aluno.id, (f'Venceu {venceu}' if venceu else ('Pacote em aberto' if personal else 'Cobrança em aberto')) + f' · {valor}',
                  valor=valor, data=venceu or 'data combinada', plano=linha['plano'], dias=linha['dias_atraso'])
    return itens


def contexto_da_tela(hoje=None):
    """Variáveis de mensagens/index.html."""
    itens = fila(hoje)
    tipos = [(tipo, rotulo, icone, cor, sum(1 for i in itens if i['tipo'] == tipo))
             for tipo, rotulo, icone, cor in (TIPOS_DO_PERSONAL if pacote_service.e_personal() else TIPOS)
             if tipo != MENSAGEM_COBRANCA or ve_cobrancas()]
    # `lembretes_auto` faz a tela dizer que a fila "sai sozinha às 9h". Isso só existe com a API oficial do WhatsApp (paga,
    # fica para depois do lançamento), então hoje é sempre False, esteja a chave de Configurações ligada ou não:
    # a tela descreve o que o sistema faz de verdade ("você toca, o WhatsApp abre pronto").
    return {'itens': itens, 'tipos': tipos, 'lembretes_auto': False, 'pendentes': sum(1 for i in itens if not i['enviada'])}


def marcar_enviada(id_do_item, hoje=None):
    """
    Grava que a pessoa tocou em "Enviar" na linha `id_do_item` ("tipo-referência"). Só aceita linha que
    está na fila de hoje de quem está logado: é isso que impede marcar aluno de outra academia ou
    cobrança por quem não vê cobrança. Devolve True se gravou ou se já estava gravada hoje; False se
    a linha não existe na fila.
    """
    hoje = hoje or date.today()
    item = next((i for i in fila(hoje) if i['id'] == id_do_item), None)
    if item is None:
        return False
    if item['enviada']:
        return True
    db.session.add(MensagemEnviada(conta_id=current_user.conta_id, aluno_id=item['aluno']['id'], tipo=item['tipo'],
                                   referencia=item['referencia'], data=hoje, enviada_por_id=current_user.id))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()     # duas pessoas tocaram na mesma linha ao mesmo tempo: a primeira já gravou
    return True
