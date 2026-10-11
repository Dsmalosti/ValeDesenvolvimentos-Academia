"""
Situação de pagamento de cada aluno: vencimento, se está em atraso e o status mostrado na tela.

[back-07-alunos] Criado nesta branch, tirado de dentro do painel_service.py (back-04), para o
painel e as telas de alunos usarem EXATAMENTE a mesma regra. Se cada tela calculasse do seu
jeito, o painel diria "2 pendentes" e a lista mostraria 3.

Regras:
  - vencimento do aluno  = a maior `data_vencimento` entre os pagamentos dele;
  - pendente (em atraso) = aluno ativo com vencimento anterior a hoje;
  - aluno sem nenhum pagamento registrado não é pendente: não há vencimento para comparar;
  - status na tela: 'inativo' (coluna ativo falsa), 'pendente' ou 'ativo'.
"""
from app.helpers.conta import da_conta
from app.models import Pagamento


def data_curta(d, hoje=None):
    """Data curta, dd/mm. Mostra o ano quando ele não é o atual: num plano anual, '20/09' pareceria já vencido."""
    if hoje is not None and d.year != hoje.year:
        return d.strftime('%d/%m/%y')
    return d.strftime('%d/%m')


def vencimentos_da_conta():
    """Dicionário {aluno_id: maior data de vencimento}, só da conta de quem está logado."""
    vencimento = {}
    for aluno_id, data in da_conta(Pagamento).with_entities(Pagamento.aluno_id, Pagamento.data_vencimento):
        if aluno_id not in vencimento or data > vencimento[aluno_id]:
            vencimento[aluno_id] = data
    return vencimento


def linha_do_aluno(aluno, vencimento, hoje):
    """Um aluno no formato que os templates do front esperam nas listas, no painel e na busca."""
    vencido = bool(aluno.ativo and vencimento and vencimento < hoje)
    if not aluno.ativo:
        status = 'inativo'
    elif vencido:
        status = 'pendente'
    else:
        status = 'ativo'
    plano = aluno.plano
    return {
        'id': aluno.id,
        'nome': aluno.nome or 'Aluno sem nome',
        'cpf': aluno.cpf or '',
        'email': aluno.email or '',
        'plano': plano.nome if plano else 'Sem plano',
        'plano_id': aluno.plano_id,
        'valor': float(plano.valor) if plano else 0.0,
        'telefone': aluno.telefone or '',
        'ativo': bool(aluno.ativo),
        'vence': data_curta(vencimento, hoje) if vencimento else '—',
        'vence_txt': (('Venceu ' if vencido else 'Vence ') + data_curta(vencimento, hoje)) if vencimento else 'Sem pagamento registrado',
        'vence_data': vencimento,
        'vencido': vencido,
        'dias_atraso': (hoje - vencimento).days if vencido else 0,
        'status': status,
    }
