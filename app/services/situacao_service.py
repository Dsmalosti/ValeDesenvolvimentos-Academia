"""
Situação de pagamento de cada aluno: vencimento, se está em atraso e o status mostrado na tela.

[back-07-alunos] Criado nesta branch, tirado de dentro do painel_service.py (back-04), para o
painel e as telas de alunos usarem EXATAMENTE a mesma regra. Se cada tela calculasse do seu
jeito, o painel diria "2 pendentes" e a lista mostraria 3.

[back-09-cobranca] As regras passaram a ler as COBRANÇAS (antes liam a tabela de pagamentos,
que guardava o vencimento junto):
  - vencimento do aluno  = a maior `data_vencimento` entre as cobranças PAGAS dele;
  - pendente (em atraso) = aluno ativo que (a) tem vencimento anterior a hoje, ou (b) tem
    cobrança em aberto cujo período já começou. O caso (b) é novo: antes, quem era matriculado
    e não pagava nada aparecia como "em dia";
  - aluno sem nenhuma cobrança não é pendente: não há o que comparar;
  - status na tela: 'inativo' (coluna ativo falsa), 'pendente' ou 'ativo'.
"""
from app.helpers.conta import da_conta
from app.models import COBRANCA_PAGA, COBRANCA_PENDENTE, Cobranca


def data_curta(d, hoje=None):
    """Data curta, dd/mm. Mostra o ano quando ele não é o atual: num plano anual, '20/09' pareceria já vencido."""
    if hoje is not None and d.year != hoje.year:
        return d.strftime('%d/%m/%y')
    return d.strftime('%d/%m')


def vencimentos_da_conta():
    """Dicionário {aluno_id: maior data de vencimento paga}, só da conta de quem está logado."""
    vencimento = {}
    pagas = da_conta(Cobranca).filter(Cobranca.status == COBRANCA_PAGA, Cobranca.aluno_id.isnot(None),
                                      Cobranca.data_vencimento.isnot(None))
    for aluno_id, data in pagas.with_entities(Cobranca.aluno_id, Cobranca.data_vencimento):
        if aluno_id not in vencimento or data > vencimento[aluno_id]:
            vencimento[aluno_id] = data
    return vencimento


def cobrancas_em_aberto_da_conta():
    """Dicionário {aluno_id: cobrança pendente mais antiga}, só da conta de quem está logado."""
    aberta = {}
    pendentes = da_conta(Cobranca).filter(Cobranca.status == COBRANCA_PENDENTE, Cobranca.aluno_id.isnot(None))
    for cobranca in pendentes.order_by(Cobranca.data_inicio, Cobranca.id):
        aberta.setdefault(cobranca.aluno_id, cobranca)
    return aberta


def linha_do_aluno(aluno, vencimento, hoje, em_aberto=None):
    """
    Um aluno no formato que os templates do front esperam nas listas, no painel e na busca.
    `vencimento` vem de vencimentos_da_conta() e `em_aberto` de cobrancas_em_aberto_da_conta().
    """
    venceu = bool(vencimento and vencimento < hoje)
    devendo = bool(em_aberto and em_aberto.data_inicio <= hoje)      # [back-09-cobranca] cobrança em aberto já iniciada
    vencido = bool(aluno.ativo and (venceu or devendo))
    if not aluno.ativo:
        status = 'inativo'
    elif vencido:
        status = 'pendente'
    else:
        status = 'ativo'
    plano = aluno.plano
    if vencimento:
        vence_txt = ('Venceu ' if venceu else 'Vence ') + data_curta(vencimento, hoje)
    else:
        vence_txt = 'Cobrança em aberto' if em_aberto else 'Sem pagamento registrado'
    # atraso: conta a partir do vencimento; para quem nunca pagou, a partir do começo do período em aberto
    desde = vencimento if venceu else (em_aberto.data_inicio if devendo else None)
    linha = {
        'id': aluno.id,
        'nome': aluno.nome or 'Aluno sem nome',
        'cpf': aluno.cpf or '',
        'email': aluno.email or '',
        'plano': plano.nome if plano else 'Sem plano',
        'plano_id': aluno.plano_id,
        # o que o aluno deve: o valor da cobrança em aberto, se houver; senão, o do plano
        'valor': float(em_aberto.valor) if em_aberto else (float(plano.valor) if plano else 0.0),
        'telefone': aluno.telefone or '',
        'ativo': bool(aluno.ativo),
        'vence': data_curta(vencimento, hoje) if vencimento else '—',
        'vence_txt': vence_txt,
        'vence_data': vencimento,
        'vencido': vencido,
        'dias_atraso': (hoje - desde).days if (vencido and desde) else 0,
        'status': status,
    }
    return _com_pacote(aluno, linha, em_aberto, hoje)


def _com_pacote(aluno, linha, em_aberto, hoje):
    """
    [back-17-personal] Na conta de personal trainer não existe "vencimento": o aluno compra SESSÕES. A linha ganha o
    `pacote` (com o saldo), o texto do saldo entra no lugar do "vence em" e o aluno só fica PENDENTE quando tem
    cobrança em aberto (o pacote passar da validade não é dívida). Na conta de academia a linha volta como veio.
    """
    from app.services import pacote_service     # importado aqui: o pacote_service também usa os modelos desta tela
    if not pacote_service.e_personal():
        return linha
    pacote = pacote_service.pacote_do(aluno)
    devendo = bool(aluno.ativo and em_aberto and em_aberto.data_inicio <= hoje)
    linha.update({'pacote': pacote, 'vence_txt': pacote_service.situacao_txt(aluno, pacote), 'vence': '—', 'vence_data': None,
                  'vencido': devendo, 'dias_atraso': (hoje - em_aberto.data_inicio).days if devendo else 0,
                  'status': 'inativo' if not aluno.ativo else ('pendente' if devendo else 'ativo')})
    return linha
