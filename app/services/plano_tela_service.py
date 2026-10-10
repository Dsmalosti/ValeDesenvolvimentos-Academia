"""
Telas de PLANOS do front novo (templates/planos/): lista em cartões, criar, editar, pausar e reativar.

[back-08-planos] Criado nesta branch. As rotas ficam em blueprints/planos/routes.py e só conferem
conta e papel; as regras (validação, números de cada cartão) ficam aqui.

Contrato com o front (planos/_form.html): os campos chegam com os nomes das colunas (nome, valor,
duracao_dias, descricao, ativo, avaliacoes_incluidas). O valor vem como o usuário digita em
português, "1.234,56". O interruptor "Plano ativo" manda ativo=1 quando ligado e não manda nada
quando desligado (é assim que caixa de seleção funciona em formulário).

Os números de cada cartão (alunos, faturamento do mês e participação) vêm do painel_service, para
a tela de Planos e o gráfico "De onde vem o faturamento" do painel nunca discordarem.
"""
import re
from decimal import Decimal

from flask_login import current_user
from sqlalchemy import func

from app.extensions.database import db
from app.helpers.conta import conta_id, da_conta
from app.models import PAPEL_INSTRUTOR, Plano
from app.services.painel_service import planos_com_faturamento

MAX_DIAS = 1095                 # 3 anos; é o mesmo limite do campo no formulário do front
MAX_DESCRICAO = 500
VALOR_MAXIMO = Decimal('99999999.99')   # o que cabe na coluna Numeric(10, 2)
AVALIACOES = (0, 1, 2, 4)       # opções do campo "Avaliação física inclusa" do front
# Cor da etiqueta e da barra de cada cartão, na ordem em que os planos aparecem (as do front).
TONS = ['blue', 'teal', 'orange', 'yellow', 'slate']
CORES_BARRA = ['blue', 'teal', 'orange', 'yellow-chart', 'slate']
# "1.234,56", "1234,56", "1234" ou "149,9": milhar com ponto (opcional) e centavos com vírgula
_VALOR_BR = re.compile(r'(\d{1,3}(\.\d{3})+|\d+)(,\d{1,2})?')


# ------------------------------------------------------------------ lista
def _linha(plano, numeros, posicao):
    """Um plano no formato que planos/lista.html e planos/_form.html esperam."""
    n = numeros.get(plano.id) or {}
    return {
        'id': plano.id,
        'nome': plano.nome,
        'valor': float(plano.valor or 0),
        'duracao_dias': int(plano.duracao_dias or 0),
        'descricao': plano.descricao or '',
        'ativo': bool(plano.ativo),
        'avaliacoes_incluidas': str(plano.avaliacoes_incluidas or 0),   # texto, para casar com as opções do <select>
        'alunos': n.get('alunos', 0),            # alunos ATIVOS neste plano
        'faturamento': n.get('valor', 0.0),      # recebido no mês de alunos deste plano
        'pct': n.get('pct', 0),                  # quanto isso representa do faturamento do mês
        'tom': TONS[posicao % len(TONS)],
        'cor_barra': CORES_BARRA[posicao % len(CORES_BARRA)],
    }


def planos_da_tela():
    """
    Devolve (linhas, ticket médio). Planos ativos primeiro, depois os pausados; dentro de cada
    grupo, por nome. A ordem não depende do faturamento, para os cartões não trocarem de lugar
    de um dia para o outro.
    """
    numeros, ticket = planos_com_faturamento()
    if current_user.papel == PAPEL_INSTRUTOR:
        # o instrutor consulta nome, preço e duração, mas não vê o dinheiro da academia
        numeros = {pid: dict(n, valor=0.0, pct=0) for pid, n in numeros.items()}
        ticket = 0.0
    planos = sorted(da_conta(Plano).all(), key=lambda p: (not p.ativo, (p.nome or '').lower(), p.id))
    return [_linha(p, numeros, i) for i, p in enumerate(planos)], ticket


def contexto_da_lista(argumentos):
    """Contexto de planos/lista.html. `?editar=<id>` abre o painel lateral (desktop) já preenchido."""
    linhas, ticket = planos_da_tela()
    editar = argumentos.get('editar', type=int)
    return {'planos': linhas, 'ticket_medio': ticket, 'erros': {},
            'plano_edicao': next((p for p in linhas if p['id'] == editar), None)}


def linha_do_plano(plano):
    """O plano no formato do formulário de edição (com alunos, faturamento e participação)."""
    linhas, _ = planos_da_tela()
    return next(p for p in linhas if p['id'] == plano.id)


# ------------------------------------------------------------------ formulário
def _valor(texto):
    """'1.234,56' -> Decimal('1234.56'). Levanta ValueError se não estiver no formato brasileiro."""
    texto = (texto or '').replace('R$', '').strip()
    if not _VALOR_BR.fullmatch(texto):
        # Não "adivinha" formatos: aceitar "149.90" tirando o ponto gravaria R$ 14.990,00.
        raise ValueError(texto)
    return Decimal(texto.replace('.', '').replace(',', '.'))


def validar(formulario, plano=None):
    """
    Confere o formulário. Devolve (valores prontos para gravar, erros {campo: mensagem}).
    `plano` é o registro em edição (None ao criar). A conferência do navegador é só
    conveniência: quem garante a regra é esta função.
    """
    erros, v = {}, {}

    v['nome'] = ' '.join((formulario.get('nome') or '').split())
    if not v['nome']:
        erros['nome'] = 'Dê um nome ao plano.'
    elif len(v['nome']) > 100:
        erros['nome'] = 'O nome pode ter no máximo 100 letras.'
    else:
        # dois planos com o mesmo nome ficariam iguais na hora de matricular
        repetido = da_conta(Plano).filter(func.lower(Plano.nome) == v['nome'].lower())
        if plano is not None:
            repetido = repetido.filter(Plano.id != plano.id)
        if repetido.first():
            erros['nome'] = 'Já existe um plano com este nome.'

    try:
        v['valor'] = _valor(formulario.get('valor'))
        if v['valor'] <= 0:
            erros['valor'] = 'Informe um valor maior que zero.'
        elif v['valor'] > VALOR_MAXIMO:
            erros['valor'] = 'Valor alto demais.'
    except ValueError:
        v['valor'] = Decimal('0')
        erros['valor'] = 'Informe o valor em reais, como 149,90.'

    dias = (formulario.get('duracao_dias') or '').strip()
    if dias.isdigit() and 1 <= int(dias) <= MAX_DIAS:
        v['duracao_dias'] = int(dias)
    else:
        v['duracao_dias'] = 0
        erros['duracao_dias'] = f'A duração vai de 1 a {MAX_DIAS} dias.'

    v['descricao'] = (formulario.get('descricao') or '').strip()
    if len(v['descricao']) > MAX_DESCRICAO:
        erros['descricao'] = f'A descrição pode ter no máximo {MAX_DESCRICAO} letras.'

    v['ativo'] = formulario.get('ativo') == '1'

    # O painel lateral do desktop não tem este campo: se ele não veio, o valor gravado não muda.
    if 'avaliacoes_incluidas' in formulario:
        avaliacoes = formulario.get('avaliacoes_incluidas') or '0'
        if avaliacoes.isdigit() and int(avaliacoes) in AVALIACOES:
            v['avaliacoes_incluidas'] = int(avaliacoes)
        else:
            erros['avaliacoes_incluidas'] = 'Escolha uma das opções.'
    return v, erros


def do_formulario(valores, formulario, plano=None):
    """O que a pessoa digitou, de volta para a tela quando há erro (com os números do plano, se for edição)."""
    dados = linha_do_plano(plano) if plano is not None else {}
    dados.update({k: valores[k] for k in ('nome', 'duracao_dias', 'descricao', 'ativo')})
    dados['valor'] = float(valores['valor'])
    if 'avaliacoes_incluidas' in formulario:
        dados['avaliacoes_incluidas'] = formulario.get('avaliacoes_incluidas') or '0'
    return dados


def aviso_dos_erros(erros):
    """
    O aviso do topo quando o formulário volta com erro. Os outros campos mostram a mensagem
    embaixo deles; a descrição é o único que o front desenha sem mensagem, então vai no aviso.
    """
    return erros.get('descricao') or 'Revise os campos destacados.'


def criar(valores):
    """Grava um plano novo na conta de quem está logado."""
    plano = Plano(conta_id=conta_id(), instrutor_id=current_user.id, **valores)
    db.session.add(plano)
    db.session.commit()
    return plano


def atualizar(plano, valores):
    """Mudar o valor não mexe em quem já pagou: os pagamentos guardam o valor que foi pago."""
    for campo, valor in valores.items():
        setattr(plano, campo, valor)
    db.session.commit()
    return plano


def alternar(plano):
    """Pausa ou reativa. Plano pausado some do cadastro de aluno e continua nos alunos que já o têm."""
    plano.ativo = not plano.ativo
    db.session.commit()
    return plano
