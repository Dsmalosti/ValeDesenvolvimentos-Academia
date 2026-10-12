"""
[back-17-personal] PACOTES DE SESSÕES e SALDO do aluno, na conta de personal trainer.

A academia vende acesso por período (plano com `duracao_dias`); o personal vende SESSÃO (pacote com
`quantidade_sessoes`). No banco é a mesma tabela `planos`; o que muda é o número que manda.

Como o saldo é calculado (não existe coluna "saldo" para ficar errada):

    saldo  =  sessões COMPRADAS  -  sessões que ABATERAM

  - compradas: a soma de `cobrancas.quantidade_sessoes` do aluno (toda cobrança que não foi cancelada,
    paga ou ainda em aberto: a sessão é creditada na venda, e o que falta receber aparece como pendente);
  - abateram: as sessões concluídas com `abateu = True`. Só sessão CONCLUÍDA consome, e só se o aluno
    tinha saldo na hora. Cancelada não consome.

Consequência (decisão D12, a mesma do front de exemplo): ao renovar, O QUE SOBROU SOMA no pacote novo.

O "pacote atual" do aluno, mostrado nas telas, é o da ÚLTIMA compra: `total` é o que ele tinha ao
comprar (sobra + sessões novas) e `usadas` é o que abateu desde então.
"""
from flask import g
from flask_login import current_user

from app.helpers.conta import da_conta
from app.models import COBRANCA_CANCELADA, CONTA_PERSONAL, Aluno, Cobranca, Plano, Sessao

ACABANDO_NO_PAINEL = 2      # o painel avisa quando sobram 2 sessões ou menos
ACABANDO_NA_AGENDA = 1      # a agenda avisa na última
VALIDADE_PADRAO_DIAS = 90   # validade de um pacote novo (o formulário de pacote não pergunta)


def e_personal():
    """A conta de quem está logado é de personal trainer?"""
    return current_user.is_authenticated and current_user.conta.modelo == CONTA_PERSONAL


def saldo_txt(saldo):
    if saldo <= 0:
        return 'sem saldo'
    return 'sobra 1 sessão' if saldo == 1 else f'sobram {saldo} sessões'


def e_avulso(plano):
    """"Sessão avulsa": pacote de uma sessão só. Não entra em "pacotes acabando" (ele sempre acaba na primeira)."""
    return bool(plano is not None and plano.quantidade_sessoes == 1)


def _valor_da_sessao(valor, quantidade):
    return round(float(valor or 0) / quantidade, 2) if quantidade else 0.0


def _pacote_vazio(plano):
    """Quem ainda não comprou nada: o pacote do cadastro, com saldo zero."""
    quantidade = (plano.quantidade_sessoes or 0) if plano else 0
    return {'id': plano.id if plano else None, 'nome': plano.nome if plano else 'Sem pacote', 'total': 0, 'usadas': 0, 'saldo': 0,
            'valor': float(plano.valor or 0) if plano else 0.0, 'valor_sessao': _valor_da_sessao(plano.valor, quantidade) if plano else 0.0,
            'avulso': e_avulso(plano)}


def _calcular():
    """{aluno_id: pacote} de todos os alunos da conta que já compraram, em três consultas."""
    planos = {p.id: p for p in da_conta(Plano).all()}
    compras = {}
    for c in (da_conta(Cobranca).filter(Cobranca.aluno_id.isnot(None), Cobranca.quantidade_sessoes.isnot(None),
                                        Cobranca.status != COBRANCA_CANCELADA).order_by(Cobranca.data_geracao, Cobranca.id)):
        compras.setdefault(c.aluno_id, []).append(c)
    abatidas = {}
    for aluno_id, quando in da_conta(Sessao).filter(Sessao.abateu.is_(True)).with_entities(Sessao.aluno_id, Sessao.concluida_em):
        abatidas.setdefault(aluno_id, []).append(quando)

    pacotes = {}
    for aluno_id, lista in compras.items():
        ultima = lista[-1]
        usadas_no_total = abatidas.get(aluno_id, [])
        saldo = max(sum(c.quantidade_sessoes for c in lista) - len(usadas_no_total), 0)
        usadas = sum(1 for quando in usadas_no_total if quando and quando >= ultima.data_geracao)
        plano = planos.get(ultima.plano_id)
        pacotes[aluno_id] = {'id': ultima.plano_id, 'nome': plano.nome if plano else 'Pacote', 'total': saldo + usadas, 'usadas': usadas,
                             'saldo': saldo, 'valor': float(ultima.valor or 0),
                             'valor_sessao': _valor_da_sessao(ultima.valor, ultima.quantidade_sessoes), 'avulso': ultima.quantidade_sessoes == 1}
    return pacotes


def pacotes_da_conta():
    """O mesmo que _calcular(), guardado durante a requisição (as listas chamam isto uma vez por aluno)."""
    if not hasattr(g, '_pacotes_da_conta'):
        g._pacotes_da_conta = _calcular()
    return g._pacotes_da_conta


def esquecer():
    """Depois de gravar uma compra ou fechar uma sessão na mesma requisição, o que estava guardado não vale mais."""
    if hasattr(g, '_pacotes_da_conta'):
        del g._pacotes_da_conta


def pacote_do(aluno):
    """O pacote atual do aluno: {id, nome, total, usadas, saldo, valor, valor_sessao, avulso}."""
    return pacotes_da_conta().get(aluno.id) or _pacote_vazio(aluno.plano)


def situacao_txt(aluno, pacote):
    """O texto que ocupa, nas listas, o lugar do "vence em": o saldo do pacote."""
    if not aluno.ativo:
        return 'pacote encerrado'
    if pacote['avulso'] and pacote['saldo'] <= 1:
        return 'sessão avulsa' if pacote['saldo'] == 1 else 'sem saldo'
    return saldo_txt(pacote['saldo'])


def acabando(limite=ACABANDO_NO_PAINEL):
    """
    Alunos ATIVOS com pacote (não avulso) e saldo até `limite`, do menor saldo para o maior:
    [{id, nome, telefone, vence_txt, pacote}]. Quem nunca comprou não entra (não tem pacote para acabar).
    """
    pacotes = pacotes_da_conta()
    ativos = da_conta(Aluno).filter(Aluno.ativo.is_(True), Aluno.id.in_(list(pacotes) or [0])).order_by(Aluno.nome, Aluno.id).all()
    linhas = [{'id': a.id, 'nome': a.nome or 'Aluno sem nome', 'telefone': a.telefone or '', 'pacote': pacotes[a.id],
               'vence_txt': situacao_txt(a, pacotes[a.id])} for a in ativos if not pacotes[a.id]['avulso'] and pacotes[a.id]['saldo'] <= limite]
    return sorted(linhas, key=lambda x: x['pacote']['saldo'])


def pacotes_para_renovar(aluno):
    """Pacotes ativos da conta, cada um com o novo saldo já calculado (o que sobrou + as sessões novas). O front só mostra."""
    saldo = pacote_do(aluno)['saldo']
    planos = (da_conta(Plano).filter(Plano.ativo.is_(True), Plano.quantidade_sessoes.isnot(None))
              .order_by(Plano.quantidade_sessoes.desc(), Plano.id).all())
    return [{'id': p.id, 'nome': p.nome, 'sessoes': p.quantidade_sessoes, 'valor': float(p.valor),
             'valor_sessao': _valor_da_sessao(p.valor, p.quantidade_sessoes), 'novo_saldo': saldo + p.quantidade_sessoes} for p in planos]
