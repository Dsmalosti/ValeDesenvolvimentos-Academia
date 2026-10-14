"""
[back-24-assinatura] A ASSINATURA de cada conta no Vale Tec: teste grátis, mensalidade e bloqueio.

Decisões do Adauto (14/10/2026):
  - teste grátis de 2 meses a partir da criação da conta; depois, pago;
  - preço do lançamento (falta o Diogo confirmar): academia R$ 49,99 e personal R$ 24,99 por mês;
  - pagamento por PIX; a confirmação é manual (painel de administração ou `flask assinatura-paga`);
  - sem pagar, a conta é bloqueada 7 dias depois do vencimento, sozinha, e a tela diz por quê e mostra
    o código para pagar;
  - os dados da conta bloqueada ficam guardados por 1 mês antes de poderem ser apagados.

Como o sistema decide (é calculado a cada acesso; não precisa de tarefa agendada no servidor):

  vencimento = o mais tarde entre o fim do teste (contas.teste_ate) e o fim do período pago (contas.pago_ate)

  até o vencimento ........................... 'teste' ou 'em_dia'  (aviso amarelo no topo nos últimos DIAS_DE_AVISO dias)
  até DIAS_DE_TOLERANCIA dias depois ......... 'vencida'            (aviso vermelho no topo; tudo funciona)
  depois disso ............................... 'bloqueada'          (só abre a tela de pagamento, os termos e o sair)
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import current_app

from app.extensions.database import db
from app.helpers.datas import somar_meses
from app.helpers.pix import copia_e_cola
from app.models import CONTA_PERSONAL, MESES_DE_TESTE_GRATIS, PAPEL_PROPRIETARIO, Mensalidade, User

PRECOS = {'academia': Decimal('49.99'), CONTA_PERSONAL: Decimal('24.99')}   # por mês; o Diogo ainda confirma
DIAS_DE_AVISO = 7                 # o aviso amarelo aparece quando faltam menos que isso para vencer
DIAS_DE_TOLERANCIA = 7            # depois do vencimento, ainda funciona por estes dias (com aviso vermelho)
DIAS_GUARDANDO_OS_DADOS = 30      # depois do bloqueio, os dados ficam guardados por este tempo

TESTE, EM_DIA, VENCIDA, BLOQUEADA = 'teste', 'em_dia', 'vencida', 'bloqueada'
ROTULOS = {TESTE: 'Teste grátis', EM_DIA: 'Em dia', VENCIDA: 'Vencida', BLOQUEADA: 'Bloqueada'}
TONS = {TESTE: 'blue', EM_DIA: 'green', VENCIDA: 'yellow', BLOQUEADA: 'red'}


def _dmy(d):
    return d.strftime('%d/%m/%Y') if d else ''


def _reais(valor):
    return 'R$ ' + f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def preco(conta):
    """Quanto a conta paga por mês."""
    return PRECOS.get(conta.modelo, PRECOS['academia'])


def fim_do_teste(conta):
    """Último dia do teste grátis. As contas novas já nascem com a data gravada; a conta é a de criação + 2 meses."""
    if conta.teste_ate:
        return conta.teste_ate
    criada = (conta.criado_em or datetime.now()).date()
    return somar_meses(criada, MESES_DE_TESTE_GRATIS)


def vencimento(conta):
    """Último dia em que a conta está paga (ou no teste)."""
    return max(d for d in (fim_do_teste(conta), conta.pago_ate) if d)


def situacao(conta, hoje=None):
    """
    Tudo o que as telas precisam saber da assinatura de uma conta:
    {estado, rotulo, tom, vence, dias_para_vencer, dias_vencida, bloqueia_em, guardar_ate, preco, em_teste, fim_do_teste, pago_ate}
    """
    hoje = hoje or date.today()
    vence = vencimento(conta)
    fim = fim_do_teste(conta)
    bloqueia_em = vence + timedelta(days=DIAS_DE_TOLERANCIA + 1)      # primeiro dia bloqueado
    em_teste = conta.pago_ate is None or conta.pago_ate <= fim        # ainda não pagou nenhum mês além do teste
    if hoje <= vence:
        estado = TESTE if em_teste else EM_DIA
    elif hoje < bloqueia_em:
        estado = VENCIDA
    else:
        estado = BLOQUEADA
    return {'estado': estado, 'rotulo': ROTULOS[estado], 'tom': TONS[estado], 'vence': vence,
            'dias_para_vencer': (vence - hoje).days, 'dias_vencida': max(0, (hoje - vence).days),
            'bloqueia_em': bloqueia_em, 'guardar_ate': bloqueia_em + timedelta(days=DIAS_GUARDANDO_OS_DADOS),
            'preco': preco(conta), 'em_teste': em_teste, 'fim_do_teste': fim, 'pago_ate': conta.pago_ate}


def bloqueada(conta, hoje=None):
    return situacao(conta, hoje)['estado'] == BLOQUEADA


def aviso_do_topo(conta, papel, hoje=None):
    """
    O aviso que aparece no topo de toda tela (base.html), ou None.
    O dono vê os avisos de vencimento chegando e de vencida; o resto da equipe só vê o de vencida (para avisar o dono).
    """
    s = situacao(conta, hoje)
    dono = papel == PAPEL_PROPRIETARIO
    if s['estado'] == VENCIDA:
        texto = f"O pagamento não chegou. A conta será bloqueada em {_dmy(s['bloqueia_em'])}."
        if not dono:
            texto += ' Avise o responsável pela conta.'
        return {'tom': 'red', 'titulo': f"Mensalidade do Vale Tec vencida desde {_dmy(s['vence'])}", 'texto': texto, 'link': dono}
    if not dono or s['estado'] == BLOQUEADA or s['dias_para_vencer'] >= DIAS_DE_AVISO:
        return None
    quando = 'hoje' if s['dias_para_vencer'] == 0 else ('amanhã' if s['dias_para_vencer'] == 1 else f"em {s['dias_para_vencer']} dias")
    if s['estado'] == TESTE:
        return {'tom': 'yellow', 'titulo': f"Seu teste grátis termina {quando} ({_dmy(s['vence'])})",
                'texto': f"Depois dele, o Vale Tec custa {_reais(s['preco'])} por mês, pago por PIX.", 'link': True}
    return {'tom': 'yellow', 'titulo': f"Sua mensalidade vence {quando} ({_dmy(s['vence'])})",
            'texto': f"Valor: {_reais(s['preco'])}, por PIX.", 'link': True}


def codigo_pix(conta):
    """O "PIX copia e cola" da mensalidade desta conta, ou None se a chave PIX do Vale Tec ainda não foi configurada."""
    cfg = current_app.config
    chave = (cfg.get('VALE_TEC_PIX_CHAVE') or '').strip()
    if not chave:
        return None
    return copia_e_cola(chave, cfg.get('VALE_TEC_PIX_NOME') or 'VALE TEC', cfg.get('VALE_TEC_PIX_CIDADE') or 'TREMEMBE',
                        valor=preco(conta), identificador=f'VALETEC{conta.id}')


def contato():
    """Como falar com o suporte: {email, whatsapp (só dígitos, ou '')}."""
    cfg = current_app.config
    return {'email': cfg.get('VALE_TEC_SUPORTE_EMAIL') or '', 'whatsapp': ''.join(c for c in (cfg.get('VALE_TEC_SUPORTE_WHATSAPP') or '') if c.isdigit())}


def dono_da(conta):
    """O primeiro dono ativo da conta (para a recepção saber a quem avisar)."""
    return User.query.filter_by(conta_id=conta.id, papel=PAPEL_PROPRIETARIO, ativo=True).order_by(User.id).first()


def contexto_da_tela(conta, usuario, hoje=None):
    """Variáveis de assinatura/index.html e assinatura/bloqueada.html."""
    s = situacao(conta, hoje)
    dono = dono_da(conta)
    return {'s': s, 'dmy': _dmy, 'reais': _reais, 'pix': codigo_pix(conta), 'contato': contato(), 'e_dono': usuario.papel == PAPEL_PROPRIETARIO,
            'nome_do_dono': f'{dono.nome} {dono.sobrenome or ""}'.strip() if dono else 'o responsável pela conta',
            'modelo_txt': 'Personal Trainer' if conta.modelo == CONTA_PERSONAL else 'Academia',
            'historico': Mensalidade.query.filter_by(conta_id=conta.id).order_by(Mensalidade.pago_em.desc()).limit(12).all()}


# ------------------------------------------------------------------ ações (painel de administração e linha de comando)
def registrar_pagamento(conta, meses=1, valor=None, quem=None, observacao='', hoje=None):
    """
    Confirma o pagamento de `meses` mensalidades e estende o período pago.
      - pagou antes do bloqueio (em dia ou na tolerância): o período novo começa no vencimento antigo, sem ganhar
        os dias de atraso;
      - pagou depois do bloqueio: o período começa no dia do pagamento.
    Devolve a Mensalidade gravada.
    """
    if not 1 <= int(meses) <= 24:
        raise ValueError('Informe de 1 a 24 meses.')
    hoje = hoje or date.today()
    s = situacao(conta, hoje)
    base = hoje if s['estado'] == BLOQUEADA else s['vence']
    fim = somar_meses(base, int(meses))
    registro = Mensalidade(conta_id=conta.id, valor=Decimal(valor) if valor is not None else preco(conta) * int(meses), meses=int(meses),
                           periodo_inicio=hoje if s['estado'] == BLOQUEADA else base + timedelta(days=1), periodo_fim=fim,
                           pago_em=datetime.now(), forma='pix', registrado_por_id=quem.id if quem else None, observacao=(observacao or '')[:200] or None)
    conta.pago_ate = fim
    db.session.add(registro)
    db.session.commit()
    return registro


def mudar_fim_do_teste(conta, ate):
    """Troca o último dia do teste grátis (ex.: o cliente piloto ganha 3 meses no total)."""
    criada = (conta.criado_em or datetime.now()).date()
    if ate < criada:
        raise ValueError('O teste não pode terminar antes de a conta ser criada.')
    conta.teste_ate = ate
    db.session.commit()
