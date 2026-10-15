"""
Cobrança: gerar o que o aluno deve, receber, renovar, diária avulsa e extrato.

[back-09-cobranca] Criado nesta branch. As rotas ficam em blueprints/cobrancas/routes.py e em
blueprints/alunos/routes.py (renovar e extrato); aqui ficam as regras.

Como funciona, em uma frase: a COBRANÇA é o que se deve (pode ficar em aberto) e o PAGAMENTO é
o que entrou no caixa. Confirmar um recebimento cria o pagamento e marca a cobrança como paga.

Regras:
  - um aluno tem no máximo UMA cobrança em aberto. Gerar outra atualiza a que já existe, em vez
    de empilhar duas dívidas;
  - o valor é congelado na cobrança: mudar o preço do plano depois não mexe nela;
  - matrícula: o período começa na data de início do aluno. Renovação: começa no vencimento
    atual ou, se já venceu, hoje. O fim é o começo mais a duração do plano;
  - no lançamento TODA confirmação é manual (PIX inclusive): a recepção confere e confirma, e
    o pagamento guarda quem confirmou. `origem_confirmacao='webhook'` fica para quando houver
    PIX automático.
"""
import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask_login import current_user
from sqlalchemy.orm import joinedload

from app.extensions.database import db
from app.helpers.conta import conta_id, da_conta
from app.helpers.dinheiro import ler_reais, reais_txt
from app.models import (COBRANCA_DIARIA, COBRANCA_MATRICULA, COBRANCA_PAGA, COBRANCA_PENDENTE, COBRANCA_RENOVACAO,
                        FORMAS_DE_PAGAMENTO, ORIGEM_MANUAL, Cobranca, Pagamento, Plano)

# 'cartao' e 'nao_informada' só existem em pagamento anterior à back-09 (a tela antiga tinha "Cartão" e aceitava vazio)
FORMAS = {'pix': 'PIX', 'debito': 'Débito', 'credito': 'Crédito', 'dinheiro': 'Dinheiro', 'cartao': 'Cartão', 'nao_informada': 'Não informada'}
VALOR_MAXIMO = Decimal('99999999.99')   # o que cabe na coluna Numeric(10, 2)
DIARIA_PADRAO = Decimal('25.00')        # valor que o popup de diária avulsa do front sugere


class CobrancaInvalida(Exception):
    """O que foi enviado não dá para cobrar ou receber. A mensagem é mostrada ao usuário."""


def _dmy(d):
    return d.strftime('%d/%m/%Y') if d else None


# ------------------------------------------------------------------ consultas
def cobranca_da_conta(id):
    """A cobrança, se for da conta de quem está logado; senão None."""
    return da_conta(Cobranca).filter_by(id=id).first()


def vencimento_do(aluno):
    """Até quando o aluno está em dia: a maior data de vencimento entre as cobranças PAGAS dele."""
    datas = [c.data_vencimento for c in da_conta(Cobranca).filter_by(aluno_id=aluno.id, status=COBRANCA_PAGA)
             if c.data_vencimento]
    return max(datas, default=None)


def em_aberto_do(aluno):
    """A cobrança em aberto do aluno (a mais antiga, se por dado antigo houver mais de uma), ou None."""
    return (da_conta(Cobranca).filter_by(aluno_id=aluno.id, status=COBRANCA_PENDENTE)
            .order_by(Cobranca.data_inicio, Cobranca.id).first())


def _ja_pagou(aluno):
    return da_conta(Cobranca).filter_by(aluno_id=aluno.id, status=COBRANCA_PAGA).first() is not None


# ------------------------------------------------------------------ gerar
def periodo(aluno, plano, tipo, hoje=None):
    """(início, fim) do período que uma cobrança deste tipo cobre."""
    hoje = hoje or date.today()
    if tipo == COBRANCA_MATRICULA:
        inicio = aluno.data_inicio or hoje
    else:
        vencimento = vencimento_do(aluno)
        inicio = max(vencimento, hoje) if vencimento else hoje
    return inicio, inicio + timedelta(days=int(plano.duracao_dias))


def gerar(aluno, plano, hoje=None):
    """
    Cria a cobrança do aluno para o plano dado. Se ele já tem uma em aberto, atualiza essa.
    É matrícula enquanto o aluno nunca pagou nada; depois disso, renovação.
    """
    tipo = COBRANCA_RENOVACAO if _ja_pagou(aluno) else COBRANCA_MATRICULA
    inicio, fim = periodo(aluno, plano, tipo, hoje)
    cobranca = em_aberto_do(aluno)
    if cobranca is None:
        cobranca = Cobranca(conta_id=conta_id(), aluno_id=aluno.id, status=COBRANCA_PENDENTE, instrutor_id=current_user.id)
        db.session.add(cobranca)
    cobranca.tipo, cobranca.plano_id, cobranca.valor = tipo, plano.id, plano.valor
    cobranca.data_inicio, cobranca.data_vencimento = inicio, fim
    # [back-17-personal] na conta de personal a compra dá SESSÕES ao aluno: a quantidade fica congelada na cobrança,
    # como o valor. Na academia o plano não tem quantidade e a coluna fica vazia (nada muda).
    cobranca.quantidade_sessoes = plano.quantidade_sessoes
    db.session.commit()
    from app.services import pacote_service
    pacote_service.esquecer()       # o saldo guardado nesta requisição não vale mais
    return cobranca


def gerar_diaria(valor_txt, nome_visitante, hoje=None):
    """Diária avulsa: entrada de caixa de visitante, sem aluno e sem plano."""
    try:
        valor = ler_reais(valor_txt) if (valor_txt or '').strip() else DIARIA_PADRAO
    except ValueError:
        raise CobrancaInvalida('Informe o valor da diária em reais, como 25,00.')
    if not (0 < valor <= VALOR_MAXIMO):
        raise CobrancaInvalida('Informe um valor maior que zero.')
    cobranca = Cobranca(conta_id=conta_id(), tipo=COBRANCA_DIARIA, valor=valor, data_inicio=hoje or date.today(),
                        nome_visitante=' '.join((nome_visitante or '').split())[:100] or None,
                        status=COBRANCA_PENDENTE, instrutor_id=current_user.id)
    db.session.add(cobranca)
    db.session.commit()
    return cobranca


# ------------------------------------------------------------------ renovar
def planos_para_renovar(aluno, hoje=None):
    """Planos ativos da conta, cada um com o novo vencimento já calculado (o front só mostra)."""
    planos = da_conta(Plano).filter(Plano.ativo.is_(True)).order_by(Plano.valor, Plano.id).all()
    linhas = []
    for p in planos:
        _, fim = periodo(aluno, p, COBRANCA_RENOVACAO if _ja_pagou(aluno) else COBRANCA_MATRICULA, hoje)
        linhas.append({'id': p.id, 'nome': p.nome, 'dias': int(p.duracao_dias), 'valor': float(p.valor),
                       'valor_txt': reais_txt(p.valor), 'novo_venc': _dmy(fim)})
    return linhas


def renovar(aluno, plano_id_txt, hoje=None):
    """Troca o plano do aluno (se mudou) e gera a cobrança da renovação. Devolve a cobrança."""
    plano = None
    if (plano_id_txt or '').isdigit():
        plano = da_conta(Plano).filter_by(id=int(plano_id_txt)).filter(Plano.ativo.is_(True)).first()
    if plano is None:
        raise CobrancaInvalida('Escolha um plano para renovar.')
    aluno.plano_id = plano.id
    return gerar(aluno, plano, hoje)


# ------------------------------------------------------------------ receber
def confirmar(cobranca, forma, valor_recebido_txt=None, agora=None):
    """
    Registra que a recepção recebeu: cria o pagamento (confirmação manual, com o nome de quem
    confirmou) e marca a cobrança como paga. Chamar de novo numa cobrança já paga não cria
    outro pagamento (o botão pode ser tocado duas vezes, ou a página recarregada).
    """
    if cobranca.status == COBRANCA_PAGA:
        return cobranca.pagamentos[-1]
    if cobranca.status != COBRANCA_PENDENTE:
        raise CobrancaInvalida('Esta cobrança foi cancelada.')
    if forma not in FORMAS_DE_PAGAMENTO:
        raise CobrancaInvalida('Escolha a forma de pagamento.')
    # O campo do formulário se chama `valor_recebido`; a coluna é `valor_pago`. Vazio = o valor da cobrança.
    try:
        valor_pago = ler_reais(valor_recebido_txt) if (valor_recebido_txt or '').strip() else cobranca.valor
    except ValueError:
        raise CobrancaInvalida('Informe o valor recebido em reais, como 149,90.')
    if not (0 < valor_pago <= VALOR_MAXIMO):
        raise CobrancaInvalida('Informe um valor recebido maior que zero.')

    pagamento = Pagamento(conta_id=cobranca.conta_id, cobranca_id=cobranca.id, forma=forma, valor_pago=valor_pago,
                          data_pagamento=agora or datetime.now(), origem_confirmacao=ORIGEM_MANUAL,
                          confirmado_por_instrutor_id=current_user.id)
    db.session.add(pagamento)
    cobranca.status = COBRANCA_PAGA
    if cobranca.aluno is not None:
        cobranca.aluno.ativo = True      # quem paga volta a ser aluno ativo (é o que o front de exemplo faz)
    db.session.commit()
    return pagamento


def para_a_tela(cobranca, forma_sugerida=None):
    """A cobrança no formato que cobranca/receber.html espera (variável `c`)."""
    aluno, plano = cobranca.aluno, cobranca.plano
    nome = (aluno.nome if aluno else None) or cobranca.nome_visitante or 'Visitante'
    pago = cobranca.status == COBRANCA_PAGA
    pagamento = cobranca.pagamentos[-1] if (pago and cobranca.pagamentos) else None
    if cobranca.tipo == COBRANCA_MATRICULA:
        contexto_txt, contexto_curto = f'{nome} acabou de ser matriculado, falta receber a primeira mensalidade', 'Matrícula criada, falta receber'
    elif cobranca.tipo == COBRANCA_RENOVACAO:
        contexto_txt, contexto_curto = f'Renovação de {nome}, falta receber a mensalidade', 'Renovação, falta receber'
    else:
        contexto_txt, contexto_curto = 'Diária avulsa, entrada de caixa rápida', 'Diária avulsa'
    quitada = 'Diária recebida' if cobranca.tipo == COBRANCA_DIARIA else 'Mensalidade quitada'
    # [back-17-personal] cobrança de PACOTE (conta de personal): mesma tela, outro texto. Somem "dias" e "vencimento".
    de_pacote = cobranca.quantidade_sessoes is not None and cobranca.tipo != COBRANCA_DIARIA
    if de_pacote:
        if cobranca.tipo == COBRANCA_MATRICULA:
            contexto_txt, contexto_curto = f"{nome} acabou de comprar o {plano.nome if plano else 'pacote'}, falta receber", 'Pacote vendido, falta receber'
        else:
            contexto_txt, contexto_curto = f'Renovação do pacote de {nome}, falta receber', 'Renovação do pacote, falta receber'
        quitada = 'Pacote quitado'
    if forma_sugerida not in FORMAS_DE_PAGAMENTO:
        forma_sugerida = aluno.forma_pagamento if (aluno and aluno.forma_pagamento in FORMAS_DE_PAGAMENTO) else None
    return {
        'id': cobranca.id,
        'estado': 'confirmado' if pago else 'pendente',
        'tipo': cobranca.tipo,
        'aluno_id': cobranca.aluno_id,
        'nome': nome,
        'plano': plano.nome if plano else 'Diária avulsa',
        'termo': 'pacote' if de_pacote else None,           # [back-17-personal] o template troca "mensalidade" por "pacote"
        'dias': int(plano.duracao_dias) if (plano and not de_pacote) else None,
        'valor': float(pagamento.valor_pago if pagamento else cobranca.valor),
        'valor_txt': reais_txt(cobranca.valor),
        'inicio': _dmy(cobranca.data_inicio),
        'vence': None if de_pacote else _dmy(cobranca.data_vencimento),
        'forma': pagamento.forma if pagamento else forma_sugerida,
        'origem': pagamento.origem_confirmacao if pagamento else None,
        'confirmado_em': pagamento.data_pagamento.strftime('%Hh%M') if pagamento else None,
        'confirmado_data': _dmy(pagamento.data_pagamento) if pagamento else None,
        'confirmado_por': (pagamento.confirmado_por.nome if (pagamento and pagamento.confirmado_por) else 'a recepção') if pagamento else None,
        'contexto_txt': contexto_txt,
        'contexto_curto': contexto_curto,
        'subtitulo_head': quitada if pago else contexto_curto,
    }


# ------------------------------------------------------------------ extrato
def pagamentos_do(aluno):
    """Os pagamentos do aluno, do mais novo para o mais antigo, no formato das telas (perfil e extrato)."""
    pagamentos = (da_conta(Pagamento).join(Cobranca, Pagamento.cobranca_id == Cobranca.id)
                  .filter(Cobranca.aluno_id == aluno.id).options(joinedload(Pagamento.confirmado_por))
                  .order_by(Pagamento.data_pagamento.desc(), Pagamento.id.desc()).all())
    return [{
        'data': _dmy(p.data_pagamento),
        'ano': p.data_pagamento.year,
        'forma': FORMAS.get(p.forma, p.forma or '—'),
        'valor': float(p.valor_pago),
        'origem': p.origem_confirmacao,
        'quem': p.confirmado_por.nome if p.confirmado_por else 'A recepção',
        'status': 'pago',
    } for p in pagamentos]


def total_do_ano(pagamentos, hoje=None):
    ano = (hoje or date.today()).year
    return sum(p['valor'] for p in pagamentos if p['ano'] == ano)


def _celula(texto):
    """Texto seguro para planilha: o apóstrofo impede o Excel de executar como fórmula o que começa com = + - @."""
    texto = str(texto or '')
    return "'" + texto if texto[:1] in ('=', '+', '-', '@', '\t', '\r') else texto


def extrato_csv(pagamentos):
    """O extrato em CSV (ponto e vírgula e marca de acentos, como o Excel em português espera)."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=';')
    escritor.writerow(['Data', 'Forma', 'Valor', 'Confirmado por'])
    for p in pagamentos:
        quem = 'Banco (automático)' if p['origem'] == 'webhook' else p['quem']
        escritor.writerow([p['data'], p['forma'], reais_txt(p['valor']), _celula(quem)])
    return '﻿' + saida.getvalue()
