"""
[back-25-admin] PAINEL DE ADMINISTRAÇÃO do Vale Tec: o Adauto e o Diogo veem todas as contas e como cada uma usa o
sistema, e cuidam da assinatura delas.

Decisões do Adauto (14/10/2026): admins = os dois (os e-mails pessoais deles); o painel mostra, por conta, alunos ativos,
último acesso, pagamentos registrados, dias de teste restantes e o relatório de entradas e saídas; o admin vê, bloqueia
e entra na conta como se fosse o dono.

Quem é admin: a coluna instrutores.admin_sistema, ligada SÓ pela linha de comando (`flask admin-do-sistema --email ...`),
no servidor. Não existe tela nem e-mail que torne alguém admin: como qualquer pessoa pode criar conta, quem
criasse uma conta com o e-mail de um admin não pode virar admin por isso.

Tudo o que um admin faz fica registrado em acoes_admin (quem, em qual conta, o quê, quando). Esse registro
não tem chave estrangeira: continua existindo mesmo depois de a conta ser apagada.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import session
from flask_login import login_user
from sqlalchemy import func

from app.extensions.database import db
from app.models import (PAPEL_PROPRIETARIO, AcaoAdmin, Aluno, AvaliacaoAgendada, AvaliacaoFisica, Cobranca, Conta, Convite, Custo,
                        Exercicio, Ficha, Frequencia, Mensalidade, MensagemEnviada, ModeloMensagem, Pagamento, Plano, RedefinicaoSenha,
                        Sessao, Treino, TreinoExercicio, User, load_user)
from app.services import assinatura_service, registro_de_acesso_service

CHAVE_DA_SESSAO = 'admin_original'      # na sessão, enquanto o admin está "dentro" de uma conta: quem ele é de verdade
DIAS_DE_INATIVIDADE = 7                 # conta sem acesso há mais que isso aparece com aviso na lista


class AcaoRecusada(Exception):
    """Pedido do admin recusado; o texto é o aviso da tela."""


def _reais(valor):
    return assinatura_service._reais(Decimal(valor or 0))


def _inicio_do_mes(hoje):
    return datetime(hoje.year, hoje.month, 1)


def registrar(admin, conta, acao, detalhe=''):
    """Grava uma linha no registro de ações do admin (sem commit: vai junto com a ação)."""
    db.session.add(AcaoAdmin(admin_id=admin.id, admin_email=admin.email or '', conta_id=conta.id if conta else None,
                             conta_nome=(conta.nome if conta else '')[:120], acao=acao, detalhe=(detalhe or '')[:300]))


# ------------------------------------------------------------------ números de cada conta
def numeros_da_conta(conta, hoje=None):
    """
    O que o painel mostra de uma conta:
    {conta, s (situação da assinatura), dono, alunos_ativos, ultimo_acesso, parado (bool), pagamentos_mes, entradas_mes,
     saidas_mes, saldo_mes, checkins_mes, dias_de_teste}
    "Entradas" são os pagamentos de alunos registrados no mês; "saídas" são os custos fixos cadastrados (por mês).
    """
    hoje = hoje or date.today()
    inicio = _inicio_do_mes(hoje)
    s = assinatura_service.situacao(conta, hoje)
    dono = assinatura_service.dono_da(conta)
    ultimo = db.session.query(func.max(User.ultimo_acesso_em)).filter(User.conta_id == conta.id).scalar()
    pagos = db.session.query(func.count(Pagamento.id), func.coalesce(func.sum(Pagamento.valor_pago), 0)).filter(
        Pagamento.conta_id == conta.id, Pagamento.data_pagamento >= inicio).one()
    saidas = db.session.query(func.coalesce(func.sum(Custo.valor), 0)).filter(Custo.conta_id == conta.id).scalar()
    return {
        'conta': conta, 's': s, 'dono': dono,
        'alunos_ativos': Aluno.query.filter(Aluno.conta_id == conta.id, Aluno.ativo.is_(True), Aluno.anonimizado_em.is_(None)).count(),
        'ultimo_acesso': ultimo,
        'parado': ultimo is None or ultimo < datetime.now() - timedelta(days=DIAS_DE_INATIVIDADE),
        'pagamentos_mes': pagos[0], 'entradas_mes': Decimal(pagos[1]), 'saidas_mes': Decimal(saidas),
        'saldo_mes': Decimal(pagos[1]) - Decimal(saidas),
        'checkins_mes': Frequencia.query.filter(Frequencia.conta_id == conta.id, Frequencia.data_hora_entrada >= inicio).count(),
        'dias_de_teste': max(0, (s['fim_do_teste'] - hoje).days) if s['estado'] == assinatura_service.TESTE else None,
    }


def contexto_da_lista(filtro='', hoje=None):
    """Variáveis de admin/index.html: resumo (cartões do topo) e uma linha por conta."""
    hoje = hoje or date.today()
    linhas = [numeros_da_conta(c, hoje) for c in Conta.query.order_by(Conta.criado_em.desc(), Conta.id.desc()).all()]
    contagem = {estado: sum(1 for l in linhas if l['s']['estado'] == estado) for estado in assinatura_service.ROTULOS}
    receita = sum((l['s']['preco'] for l in linhas if l['s']['estado'] == assinatura_service.EM_DIA), Decimal('0'))
    if filtro in assinatura_service.ROTULOS:
        linhas = [l for l in linhas if l['s']['estado'] == filtro]
    return {'linhas': linhas, 'contagem': contagem, 'total': sum(contagem.values()), 'receita_mensal': receita, 'filtro': filtro,
            'rotulos': assinatura_service.ROTULOS, 'reais': _reais, 'novas_no_mes': Conta.query.filter(Conta.criado_em >= _inicio_do_mes(hoje)).count(),
            # [back-28-precos-e-promocao] quantas vagas da promoção de lançamento ainda sobram
            'vagas_da_promocao': assinatura_service.vagas_da_promocao(), 'total_de_vagas': assinatura_service.VAGAS_DA_PROMOCAO}


def contexto_da_conta(conta, hoje=None):
    """Variáveis de admin/conta.html."""
    hoje = hoje or date.today()
    n = numeros_da_conta(conta, hoje)
    n.update({
        'equipe': User.query.filter_by(conta_id=conta.id).order_by(User.id).all(),
        'planos': Plano.query.filter_by(conta_id=conta.id, ativo=True).count(),
        'mensalidades': Mensalidade.query.filter_by(conta_id=conta.id).order_by(Mensalidade.pago_em.desc()).limit(12).all(),
        'acoes': AcaoAdmin.query.filter_by(conta_id=conta.id).order_by(AcaoAdmin.quando.desc()).limit(15).all(),
        'pode_apagar': pode_apagar(conta, hoje)[0], 'motivo_de_nao_apagar': pode_apagar(conta, hoje)[1],
        'reais': _reais, 'hoje': hoje,
        'vagas_da_promocao': assinatura_service.vagas_da_promocao(), 'desconto_da_promocao': assinatura_service.DESCONTO_DA_PROMOCAO,  # [back-28-precos-e-promocao]
    })
    return n


# ------------------------------------------------------------------ assinatura
def confirmar_pagamento(admin, conta, meses, valor=''):
    try:
        meses = int(meses)
        texto = str(valor or '').strip().replace('R$', '').strip()
        if ',' in texto:                       # "1.234,56" ou "49,99": o jeito brasileiro
            texto = texto.replace('.', '').replace(',', '.')
        valor = Decimal(texto) if texto else None
    except Exception:
        raise AcaoRecusada('Confira os meses e o valor.')
    if valor is not None and valor <= 0:
        raise AcaoRecusada('O valor tem de ser maior que zero.')
    try:
        registro = assinatura_service.registrar_pagamento(conta, meses=meses, valor=valor, quem=admin, observacao='painel de administração')
    except ValueError as erro:
        raise AcaoRecusada(str(erro))
    registrar(admin, conta, 'pagamento', f'{meses} mês(es), {_reais(registro.valor)}, pago até {registro.periodo_fim:%d/%m/%Y}')
    db.session.commit()
    return registro


def mudar_teste(admin, conta, ate_txt):
    try:
        ate = date.fromisoformat((ate_txt or '').strip())
        assinatura_service.mudar_fim_do_teste(conta, ate)
    except ValueError as erro:
        raise AcaoRecusada(str(erro) if 'teste' in str(erro) else 'Informe a data do fim do teste.')
    registrar(admin, conta, 'teste', f'teste grátis até {ate:%d/%m/%Y}')
    db.session.commit()


def bloquear(admin, conta, motivo):
    motivo = (motivo or '').strip()
    if not motivo:
        raise AcaoRecusada('Escreva o motivo do bloqueio (aparece para o cliente).')
    if any(u.admin_sistema for u in conta.usuarios):
        raise AcaoRecusada('Esta conta é de um administrador e não pode ser bloqueada por aqui.')
    conta.bloqueio_manual_em = date.today()
    conta.bloqueio_motivo = motivo[:200]
    registrar(admin, conta, 'bloqueio', motivo)
    db.session.commit()


def desbloquear(admin, conta):
    conta.bloqueio_manual_em = None
    conta.bloqueio_motivo = None
    registrar(admin, conta, 'desbloqueio')
    db.session.commit()


def mudar_promocao(admin, conta, ligar):
    """
    [back-28-precos-e-promocao] Dá ou tira o desconto da promoção de lançamento de uma conta. Serve para corrigir à mão: conta de teste
    ou repetida que pegou uma das vagas, ou um cliente que deveria ter ganhado. Dar só funciona se ainda houver vaga.
    """
    ligar = str(ligar) == '1'
    if ligar == bool(conta.desconto_promocional):
        return
    if ligar:
        if assinatura_service.vagas_da_promocao() <= 0:
            raise AcaoRecusada(f'As {assinatura_service.VAGAS_DA_PROMOCAO} vagas da promoção já foram usadas. Tire de outra conta primeiro.')
        conta.desconto_promocional = assinatura_service.DESCONTO_DA_PROMOCAO
        registrar(admin, conta, 'promocao', f'ganhou {conta.desconto_promocional}% de desconto')
    else:
        conta.desconto_promocional = 0
        registrar(admin, conta, 'promocao', 'perdeu o desconto da promoção')
    db.session.commit()


# ------------------------------------------------------------------ entrar na conta como o dono
def entrar(admin, conta):
    """O admin passa a usar o sistema como o dono da conta. A sessão guarda quem ele é, para voltar."""
    dono = assinatura_service.dono_da(conta)
    if dono is None:
        raise AcaoRecusada('Esta conta não tem dono ativo para entrar.')
    registrar(admin, conta, 'entrou', f'como {dono.email}')
    db.session.commit()
    original = admin.get_id()
    registro_de_acesso_service.registrar(admin, evento='admin_entrou')     # [back-26-lgpd-final] o acesso do admin também entra no registro
    login_user(dono)
    session[CHAVE_DA_SESSAO] = original


def dentro_de_uma_conta():
    return bool(session.get(CHAVE_DA_SESSAO))


def voltar(conta_atual):
    """Sai da conta do cliente e volta a ser o admin. Devolve o admin, ou None se a sessão não vale mais."""
    admin = load_user(session.pop(CHAVE_DA_SESSAO, ''))
    if admin is None or not admin.admin_sistema:
        return None
    registrar(admin, conta_atual, 'saiu')
    db.session.commit()
    login_user(admin)
    return admin


# ------------------------------------------------------------------ apagar a conta (depois do prazo de guarda)
def pode_apagar(conta, hoje=None):
    """(bool, motivo). Só conta bloqueada, depois dos 30 dias em que os dados ficam guardados, e que não tem admin."""
    hoje = hoje or date.today()
    s = assinatura_service.situacao(conta, hoje)
    if any(u.admin_sistema for u in conta.usuarios):
        return False, 'A conta tem um administrador.'
    if s['estado'] != assinatura_service.BLOQUEADA:
        return False, 'Só conta bloqueada pode ser apagada.'
    if hoje < s['guardar_ate']:
        return False, f"Os dados ficam guardados até {s['guardar_ate']:%d/%m/%Y} (prometido ao cliente)."
    return True, ''


def apagar_conta(admin, conta, confirmacao):
    """
    Apaga a conta e TUDO o que é dela, de todas as tabelas, numa transação só. Não tem volta.
    Fica só a linha no registro de ações do admin (com o nome da conta).
    """
    pode, motivo = pode_apagar(conta)
    if not pode:
        raise AcaoRecusada(motivo)
    if (confirmacao or '').strip() != conta.nome.strip():
        raise AcaoRecusada('Para apagar, digite o nome da conta exatamente como aparece.')
    cid, nome = conta.id, conta.nome
    alunos = db.session.query(Aluno.id).filter(Aluno.conta_id == cid)
    usuarios = db.session.query(User.id).filter(User.conta_id == cid)
    fichas = db.session.query(Ficha.id).filter(Ficha.aluno_id.in_(alunos))
    treinos = db.session.query(Treino.id).filter(Treino.ficha_id.in_(fichas))
    exercicios = db.session.query(Exercicio.id).filter(Exercicio.conta_id == cid)
    apagar = lambda consulta: consulta.delete(synchronize_session=False)     # noqa: E731

    # ordem: primeiro o que aponta para os outros (as chaves estrangeiras não deixam apagar fora de ordem)
    apagar(TreinoExercicio.query.filter(TreinoExercicio.treino_id.in_(treinos) | TreinoExercicio.exercicio_id.in_(exercicios)))
    apagar(Treino.query.filter(Treino.ficha_id.in_(fichas)))
    apagar(Ficha.query.filter(Ficha.aluno_id.in_(alunos)))
    for modelo in (MensagemEnviada, AvaliacaoFisica, AvaliacaoAgendada, Sessao, Frequencia, Pagamento, Cobranca, Mensalidade,
                   ModeloMensagem, Custo, Convite):
        apagar(modelo.query.filter(modelo.conta_id == cid))
    apagar(RedefinicaoSenha.query.filter(RedefinicaoSenha.usuario_id.in_(usuarios)))
    apagar(Aluno.query.filter(Aluno.conta_id == cid))
    apagar(Plano.query.filter(Plano.conta_id == cid))
    apagar(Exercicio.query.filter(Exercicio.conta_id == cid))
    # pagamento de mensalidade de OUTRA conta confirmado por alguém desta (só se esta conta tivesse um admin, o que é barrado acima)
    Mensalidade.query.filter(Mensalidade.registrado_por_id.in_(usuarios)).update({'registrado_por_id': None}, synchronize_session=False)
    apagar(User.query.filter(User.conta_id == cid))
    apagar(Conta.query.filter(Conta.id == cid))
    db.session.add(AcaoAdmin(admin_id=admin.id, admin_email=admin.email or '', conta_id=cid, conta_nome=nome[:120], acao='apagou',
                             detalhe='conta e todos os dados apagados'))
    db.session.commit()


# ------------------------------------------------------------------ último acesso
def anotar_acesso(usuario, agora=None):
    """Guarda quando o usuário usou o sistema pela última vez (no máximo uma gravação a cada 10 minutos)."""
    agora = agora or datetime.now()
    if usuario.ultimo_acesso_em is None or agora - usuario.ultimo_acesso_em > timedelta(minutes=10):
        usuario.ultimo_acesso_em = agora
        db.session.commit()
