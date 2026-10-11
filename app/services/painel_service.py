"""
Números do painel (tela inicial do front novo, templates/painel/index.html).

[back-04-painel] Criado nesta branch. Tudo aqui é calculado a partir do que o banco já tem
hoje (alunos, planos e pagamentos) e SÓ da conta de quem está logado (helpers/conta.py).

Regras usadas, para o número do card e a lista que ele abre nunca discordarem:
  - vencimento do aluno  = a maior `data_vencimento` entre os pagamentos dele;
  - pendente (em atraso) = aluno ativo com vencimento anterior a hoje;
  - aluno sem nenhum pagamento registrado não entra como pendente: não há vencimento para comparar;
  - faturamento do mês   = soma dos pagamentos com `data_pagamento` no mês atual.

O que ainda NÃO dá para calcular, e por isso vem vazio:
  - ausentes (não existe frequência), meta (não existe Configurações), notificações e
    avaliação do dia (módulos ainda não criados);
  - histórico real de "alunos ativos por mês": o banco não guarda quando um aluno foi
    inativado. O gráfico mostra, para cada mês, quantos dos alunos ATIVOS HOJE já estavam
    cadastrados até o fim daquele mês. Quem saiu no meio do caminho não aparece.
"""
from collections import defaultdict
from datetime import date

from app.helpers.conta import da_conta
from app.models import Aluno, Pagamento, Plano

DIAS = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro',
         'outubro', 'novembro', 'dezembro']
# cores do gráfico "De onde vem o faturamento", do plano que mais rende para o que menos rende
CORES_PLANOS = ['blue-dark', 'blue', 'blue-500', 'blue-300', 'blue-100']
MESES_NO_GRAFICO = 9


def _dm(d, hoje=None):
    """Data curta. Mostra o ano quando ele não é o atual: num plano anual, '20/09' pareceria já vencido."""
    if hoje is not None and d.year != hoje.year:
        return d.strftime('%d/%m/%y')
    return d.strftime('%d/%m')


def _mes_anterior(ano, mes):
    return (ano, mes - 1) if mes > 1 else (ano - 1, 12)


def _mesmo_mes(d, ano, mes):
    return d is not None and d.year == ano and d.month == mes


def _pct(novo, antigo):
    """Variação em % de `antigo` para `novo`. None quando não há base para comparar."""
    if not antigo:
        return None
    return round((novo - antigo) / antigo * 100)


def _linha_aluno(aluno, vencimento, hoje):
    """Um aluno no formato que os templates do painel esperam."""
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
        'plano': plano.nome if plano else 'Sem plano',
        'valor': float(plano.valor) if plano else 0.0,
        'telefone': aluno.telefone or '',
        'vence': _dm(vencimento, hoje) if vencimento else '—',
        'vence_txt': (('Venceu ' if vencido else 'Vence ') + _dm(vencimento, hoje)) if vencimento else 'Sem pagamento registrado',
        'vencido': vencido,
        'dias_atraso': (hoje - vencimento).days if vencido else 0,
        'status': status,
    }


def montar_painel(hoje=None):
    """Devolve o dicionário de contexto do painel: k, serie, planos_fat, alunos, alertas, listas, pendentes, hoje."""
    hoje = hoje or date.today()
    ano, mes = hoje.year, hoje.month
    ano_ant, mes_ant = _mes_anterior(ano, mes)

    alunos = da_conta(Aluno).order_by(Aluno.data_cadastro.desc()).all()
    pagamentos = da_conta(Pagamento).all()
    planos = da_conta(Plano).all()

    # maior vencimento de cada aluno
    vencimento = {}
    for p in pagamentos:
        if p.aluno_id not in vencimento or p.data_vencimento > vencimento[p.aluno_id]:
            vencimento[p.aluno_id] = p.data_vencimento

    linhas = {a.id: _linha_aluno(a, vencimento.get(a.id), hoje) for a in alunos}
    cadastro = {a.id: (a.data_cadastro.date() if a.data_cadastro else None) for a in alunos}
    ativos = [a for a in alunos if a.ativo]
    inativos = [a for a in alunos if not a.ativo]

    pendentes = sorted((linhas[a.id] for a in ativos if linhas[a.id]['vencido']), key=lambda x: -x['dias_atraso'])
    vencem = sorted((linhas[a.id] for a in ativos
                     if not linhas[a.id]['vencido'] and _mesmo_mes(vencimento.get(a.id), ano, mes)),
                    key=lambda x: x['vence'][:2])  # todos vencem neste mês: basta ordenar pelo dia
    novas = [a for a in alunos if _mesmo_mes(cadastro[a.id], ano, mes)]
    novas_mes_anterior = sum(1 for a in alunos if _mesmo_mes(cadastro[a.id], ano_ant, mes_ant))

    faturamento = sum(float(p.valor) for p in pagamentos if _mesmo_mes(p.data_pagamento, ano, mes))
    faturamento_anterior = sum(float(p.valor) for p in pagamentos if _mesmo_mes(p.data_pagamento, ano_ant, mes_ant))

    aniversariantes = [a for a in ativos if a.data_nascimento
                       and (a.data_nascimento.day, a.data_nascimento.month) == (hoje.day, hoje.month)]

    serie = _serie_ativos(ativos, cadastro, hoje)

    k = {
        'ativos': len(ativos),
        'ativos_delta': sum(1 for a in ativos if _mesmo_mes(cadastro[a.id], ano, mes)),
        'inativos': len(inativos),
        'faturamento': faturamento,
        'fat_delta': _pct(faturamento, faturamento_anterior),      # None = sem mês anterior para comparar
        'fat_meta': None, 'fat_meta_pct': None,                    # metas vêm de Configurações (ainda não existe)
        'vencimentos': len(vencem),
        'vencimentos_valor': sum(x['valor'] for x in vencem),
        'inadimplencia': sum(x['valor'] for x in pendentes),
        'inad_qtd': len(pendentes),
        'ticket': (faturamento / len(ativos)) if ativos else 0.0,
        'ausentes': None,                                          # precisa do módulo de frequência
        'novas': len(novas),
        'novas_delta': len(novas) - novas_mes_anterior,
        'aniversarios': len(aniversariantes),
        'em_risco': len(pendentes),
        'notificacoes': 0,                                         # módulo ainda não criado
        # crescimento no ano: ativos de hoje contra os que já estavam cadastrados na virada do ano
        'ano_delta': _pct(len(ativos), sum(1 for a in ativos if cadastro[a.id] is None or cadastro[a.id].year < ano)),
    }

    alertas = {
        'avaliacao_hoje': None,                                    # precisa do módulo de avaliações
        'risco': [{'nome': x['nome'], 'tipo': 'pagamento', 'tom': 'red',
                   'motivo': f"Pagamento atrasado há {x['dias_atraso']} dia{'s' if x['dias_atraso'] != 1 else ''}"}
                  for x in pendentes],
        'aniversarios': [{'nome': a.nome or 'Aluno sem nome',
                          'motivo': f"Completa {hoje.year - a.data_nascimento.year} anos hoje"}
                         for a in aniversariantes],
        'renovacao': [{'nome': x['nome'], 'tom': 'red' if x['dias_atraso'] > 10 else 'blue',
                       'motivo': f"Plano {x['plano'].lower()} venceu há {x['dias_atraso']} dias"}
                      for x in pendentes if x['dias_atraso'] > 5],
    }

    listas = {
        'vencem': vencem,
        'ausentes': [],
        'novas': [{'aluno': linhas[a.id], 'data': _dm(cadastro[a.id])} for a in novas],
    }

    return {
        'k': k,
        'serie': serie,
        'planos_fat': _faturamento_por_plano(planos, ativos, pagamentos, faturamento, ano, mes),
        'alunos': [linhas[a.id] for a in alunos[:6]],
        'alertas': alertas,
        'listas': listas,
        'pendentes': pendentes[:8],
        'hoje': f"{DIAS[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month - 1]}",
    }


def _serie_ativos(ativos, cadastro, hoje):
    """Gráfico "Alunos ativos por mês": os últimos meses, do mais antigo para o atual."""
    meses = []
    ano, mes = hoje.year, hoje.month
    for _ in range(MESES_NO_GRAFICO):
        meses.append((ano, mes))
        ano, mes = _mes_anterior(ano, mes)
    meses.reverse()

    valores = []
    for a, m in meses:
        # cadastrados até o fim do mês (a, m); aluno sem data de cadastro conta em todos
        valores.append(sum(1 for al in ativos
                           if cadastro[al.id] is None or (cadastro[al.id].year, cadastro[al.id].month) <= (a, m)))

    primeiro, ultimo = meses[0], meses[-1]
    periodo = f"{MESES[primeiro[1] - 1].capitalize()} a {MESES[ultimo[1] - 1]} de {ultimo[0]}"
    if primeiro[0] != ultimo[0]:
        periodo = f"{MESES[primeiro[1] - 1].capitalize()} de {primeiro[0]} a {MESES[ultimo[1] - 1]} de {ultimo[0]}"
    return {
        'labels': [MESES[m - 1][:3].capitalize() for _, m in meses],
        'valores': valores,
        'meta': None,                                              # vem de Configurações > Metas (ainda não existe)
        'periodo': periodo,
    }


def _faturamento_por_plano(planos, ativos, pagamentos, faturamento, ano, mes):
    """Gráfico "De onde vem o faturamento": quanto cada plano recebeu no mês."""
    plano_do_aluno = {a.id: a.plano_id for a in ativos}
    alunos_no_plano = defaultdict(int)
    for a in ativos:
        alunos_no_plano[a.plano_id] += 1

    recebido = defaultdict(float)
    for p in pagamentos:
        if _mesmo_mes(p.data_pagamento, ano, mes):
            recebido[plano_do_aluno.get(p.aluno_id)] += float(p.valor)

    linhas = [{
        'plano_id': pl.id,
        'nome': pl.nome,
        'alunos': alunos_no_plano[pl.id],
        'dias': int(pl.duracao_dias) if pl.duracao_dias else None,
        'valor': recebido[pl.id],
        'pct': round(recebido[pl.id] / faturamento * 100) if faturamento else 0,
    } for pl in planos if pl.ativo or alunos_no_plano[pl.id]]
    linhas.sort(key=lambda x: (-x['valor'], -x['alunos'], x['nome']))
    for i, linha in enumerate(linhas):
        linha['cor'] = CORES_PLANOS[min(i, len(CORES_PLANOS) - 1)]
    return linhas
