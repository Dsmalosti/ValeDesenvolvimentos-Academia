"""
Configurações da conta (templates/config/): dados da academia, horário, metas, modelos de
mensagem, funcionalidades ligadas e recebimento.

[back-12-config] Criado nesta branch. As rotas ficam em blueprints/config/routes.py.

Onde cada coisa fica guardada:
  - dados, horário, metas e funcionalidades: colunas da tabela `contas` (uma linha por academia);
  - modelos de mensagem: tabela `modelos_mensagem`, e só os que a academia ALTEROU. Os que ela
    nunca mexeu vêm do padrão escrito aqui (MODELOS_PADRAO), então melhorar um texto padrão
    chega a todo mundo que não personalizou.
"""
import re
from datetime import date, timedelta
from decimal import Decimal

from flask import session
from flask_login import current_user

from app.extensions.database import db
from app.helpers.conta import da_conta
from app.helpers.dinheiro import ler_reais
from app.models import PAPEL_INSTRUTOR, PAPEL_PROPRIETARIO, Aluno, ModeloMensagem, Pagamento, User
from app.services.situacao_service import vencimentos_da_conta

ABAS = [('academia', 'Academia'), ('equipe', 'Equipe'), ('mensagens', 'Mensagens'), ('cobranca', 'Cobrança'),
        ('integracoes', 'Integrações'), ('metas', 'Metas')]
PAPEIS = {'proprietario': ('green', 'Proprietário'), 'recepcao': ('blue', 'Recepção'), 'instrutor': ('slate', 'Instrutor')}
HORARIO_SEM_DADO = 'Não informado'
MAX_MENSAGEM = 500                       # o mesmo limite do campo no front
DIAS_INATIVIDADE = (15, 365)             # mínimo e máximo aceitos, como no campo do front
META_FATURAMENTO_MAXIMA = Decimal('99999999.99')

# tipo, nome na tela, cor do marcador e texto padrão. [nome], [valor], [data], [academia], [plano], [dias],
# [hora] e [local] são trocados na hora de montar a mensagem (módulo de mensagens).
MODELOS_PADRAO = [
    ('cobranca', 'Cobrança de mensalidade', 'yellow', 'Oi [nome], tudo certo? Sua mensalidade de [valor] venceu em [data]. Quer que eu mande o PIX?'),
    ('aniversario', 'Aniversário', 'blue', 'Parabéns, [nome]! A equipe da [academia] deseja um dia ótimo.'),
    ('sumido', 'Aluno sumido', 'orange', '[nome], sentimos sua falta! Faz [dias] dias que você não aparece. Bora voltar essa semana?'),
    ('boasvindas', 'Boas-vindas', 'green', 'Bem-vindo à [academia], [nome]! Seu plano [plano] já está ativo e vence dia [data].'),
    ('avaliacao', 'Lembrete de avaliação', 'teal', 'Oi [nome]! Sua avaliação física é amanhã, [data] às [hora], na [academia]. Venha com roupa leve. Confirma pra mim?'),
    ('sessao', 'Lembrete de sessão', 'teal', 'Oi [nome]! Confirmando nosso treino amanhã, [data] às [hora], no [local]. Posso contar com você?'),
]
TIPOS_DE_MENSAGEM = {tipo for tipo, _, _, _ in MODELOS_PADRAO}


class ConfigInvalida(Exception):
    """O que foi enviado não pode ser gravado. A mensagem é mostrada ao usuário."""


def _so_digitos(texto):
    return re.sub(r'\D', '', texto or '')


def _conta():
    return current_user.conta


# ------------------------------------------------------------------ leitura
def modelos_de_mensagem():
    """Os modelos da conta: o texto que ela gravou ou, se nunca mexeu, o padrão."""
    proprios = {m.tipo: m.texto for m in da_conta(ModeloMensagem).all()}
    return [{'tipo': tipo, 'nome': nome, 'cor': cor, 'texto': proprios.get(tipo, padrao)} for tipo, nome, cor, padrao in MODELOS_PADRAO]


def equipe():
    """
    Quem tem acesso à conta (o dono primeiro) e, depois, os convites que ainda esperam resposta.
    [back-13-equipe] antes: listava todo usuário da conta. Agora deixa de fora quem foi removido (inativo)
    e inclui os convites em aberto, com `id` NEGATIVO (é assim que a rota distingue pessoa de convite).
    `convite` é o link, quando o dono acabou de criá-lo nesta sessão; senão True (o banco só guarda o hash).
    """
    from app.services import acesso_service              # importado aqui: ele também usa modelos desta tela
    usuarios = da_conta(User).filter(User.ativo.is_(True)).order_by(User.id).all()
    usuarios.sort(key=lambda u: (u.papel != PAPEL_PROPRIETARIO, u.id))
    pessoas = [{'id': u.id, 'nome': ' '.join(p for p in (u.nome, u.sobrenome) if p) or u.email, 'email': u.email, 'papel': u.papel}
               for u in usuarios]
    links = session.get('links_de_convite', {})
    for c in acesso_service.convites_abertos():
        pessoas.append({'id': -c.id, 'nome': c.email.split('@')[0], 'email': c.email, 'papel': c.papel, 'convite': links.get(str(c.id), True)})
    return pessoas


def _cfg():
    conta = _conta()
    return {
        'func': {'frequencia': bool(conta.checkin_ativo), 'inatividade': bool(conta.inatividade_ligada), 'lembretes': bool(conta.lembretes_ligados)},
        'inatividade_dias': conta.inatividade_dias,
        'horario': {'semana': conta.horario_semana or HORARIO_SEM_DADO, 'sabado': conta.horario_sabado or HORARIO_SEM_DADO,
                    'domingo': conta.horario_domingo or HORARIO_SEM_DADO},
        'mensagens': modelos_de_mensagem(),
        'equipe': equipe(),
    }


def metas_da_conta():
    """As três metas. Vazio ('') quando a academia ainda não definiu: é o que o campo do formulário mostra."""
    conta = _conta()
    return {'alunos_ativos': conta.meta_alunos_ativos or '', 'faturamento': float(conta.meta_faturamento) if conta.meta_faturamento else '',
            'retencao': conta.meta_retencao or ''}


def _metas_de_hoje():
    """Quanto vale hoje cada número que tem meta (os mesmos do painel e do administrativo)."""
    from app.services import painel_service, relatorio_service    # importados aqui: eles também importam este módulo
    k = painel_service.montar_painel()['k']
    retencao = relatorio_service.retencao_aos_90_dias()
    return {'alunos_ativos': k['ativos'], 'faturamento': k['faturamento'], 'retencao': retencao, 'retencao_txt': f'{retencao}%' if retencao is not None else None}


def contexto(aba, erros=None, metas=None):
    """Variáveis de config/index.html. `aba` inválida vira None (menu no celular, "Academia" no desktop)."""
    abas = [a for a in ABAS if a[0] != 'metas' or current_user.papel != PAPEL_INSTRUTOR]    # instrutor não vê metas
    return {'aba': aba if aba in dict(abas) else None, 'abas': abas, 'cfg': _cfg(), 'papeis': PAPEIS,
            'metas': metas or metas_da_conta(), 'metas_hoje': _metas_de_hoje(), 'erros': erros or {}}


def contexto_do_recebimento(hoje=None):
    """Variáveis de config/recebimento.html: a situação do PIX e de onde veio cada confirmação do mês."""
    hoje = hoje or date.today()
    do_mes = [p for p in da_conta(Pagamento).all() if (p.data_pagamento.year, p.data_pagamento.month) == (hoje.year, hoje.month)]
    grupos = [('Confirmado pelo banco', 'blue', lambda p: p.origem_confirmacao == 'webhook'),
              ('PIX, na mão', 'teal', lambda p: p.origem_confirmacao != 'webhook' and p.forma == 'pix'),
              ('Maquininha, na mão', 'yellow-chart', lambda p: p.origem_confirmacao != 'webhook' and p.forma in ('debito', 'credito', 'cartao')),
              ('Dinheiro, na mão', 'slate', lambda p: p.origem_confirmacao != 'webhook' and p.forma not in ('pix', 'debito', 'credito', 'cartao'))]
    itens = []
    for nome, cor, pertence in grupos:
        qtd = sum(1 for p in do_mes if pertence(p))
        itens.append({'nome': nome, 'cor': cor, 'qtd': qtd, 'pct': round(qtd / len(do_mes) * 100) if do_mes else 0})
    from app.services.relatorio_service import MESES
    return {'pix': {'ligado': bool(_conta().pix_ligado), 'conta_desde': '—', 'chave': '—', 'ultimo_aviso': '—'},
            'origem': {'total': len(do_mes), 'itens': itens, 'mes': MESES[hoje.month - 1].capitalize()}}


# ------------------------------------------------------------------ gravação
def salvar_academia(formulario):
    """Dados da academia. Só o nome é obrigatório. Devolve a conta."""
    conta = _conta()
    nome = ' '.join((formulario.get('nome') or '').split())
    if not nome or len(nome) > 120:
        raise ConfigInvalida('Informe o nome da academia (até 120 letras).')
    cnpj = _so_digitos(formulario.get('cnpj'))
    if cnpj and len(cnpj) != 14:
        raise ConfigInvalida('CNPJ incompleto: são 14 números.')
    email = (formulario.get('email') or '').strip().lower()
    if email and (len(email) > 120 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email)):
        raise ConfigInvalida('E-mail inválido.')
    conta.nome = nome
    conta.cnpj = f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}' if cnpj else None
    conta.telefone = (formulario.get('telefone') or '').strip()[:20] or None
    conta.email = email or None
    conta.cidade = ' '.join((formulario.get('cidade') or '').split())[:80] or None
    conta.endereco = ' '.join((formulario.get('endereco') or '').split())[:200] or None
    db.session.commit()
    return conta


def salvar_horario(formulario):
    """Horário de funcionamento: três textos livres ("06h - 22h", "Fechado")."""
    conta = _conta()
    valores = {k: ' '.join((formulario.get(k) or '').split()) for k in ('semana', 'sabado', 'domingo')}
    if not all(valores.values()) or any(len(v) > 40 for v in valores.values()):
        raise ConfigInvalida('Preencha os três horários (até 40 letras cada). Ex.: 06h - 22h ou Fechado.')
    conta.horario_semana, conta.horario_sabado, conta.horario_domingo = valores['semana'], valores['sabado'], valores['domingo']
    db.session.commit()


def salvar_mensagem(tipo, texto):
    """Grava o texto de um modelo de mensagem da conta (cria a linha na primeira vez que a academia altera)."""
    texto = (texto or '').strip()
    if tipo not in TIPOS_DE_MENSAGEM or not texto:
        raise ConfigInvalida('A mensagem não pode ficar vazia.')
    if len(texto) > MAX_MENSAGEM:
        raise ConfigInvalida(f'A mensagem pode ter no máximo {MAX_MENSAGEM} letras.')
    modelo = da_conta(ModeloMensagem).filter_by(tipo=tipo).first()
    if modelo is None:
        modelo = ModeloMensagem(conta_id=_conta().id, tipo=tipo)
        db.session.add(modelo)
    modelo.texto = texto
    db.session.commit()


def salvar_funcionalidade(chave, ligado, dias_txt=None):
    """
    Liga ou desliga uma funcionalidade da conta: frequencia (check-in), inatividade ou lembretes.
    `dias_txt` é o prazo da inatividade automática. Devolve o texto do aviso.
    """
    conta = _conta()
    if chave not in ('frequencia', 'inatividade', 'lembretes'):
        raise ConfigInvalida('Configuração desconhecida.')
    if (dias_txt or '').strip():
        if not dias_txt.strip().isdigit() or not (DIAS_INATIVIDADE[0] <= int(dias_txt) <= DIAS_INATIVIDADE[1]):
            raise ConfigInvalida(f'O prazo de inatividade vai de {DIAS_INATIVIDADE[0]} a {DIAS_INATIVIDADE[1]} dias.')
        conta.inatividade_dias = int(dias_txt)
    if chave == 'frequencia':
        conta.checkin_ativo = ligado
        aviso = ('Controle de frequência ligado: o check-in, o menu de frequência e os números de ausência voltam a aparecer.' if ligado
                 else 'Controle de frequência desligado: o check-in, o menu de frequência e os números de ausência saem do painel.')
    elif chave == 'inatividade':
        conta.inatividade_ligada = ligado
        aviso = 'Configuração salva.'
    else:
        conta.lembretes_ligados = ligado
        aviso = 'Configuração salva.'
    db.session.commit()
    return aviso


def validar_metas(formulario):
    """Devolve (valores para gravar, erros {campo: mensagem}, o que devolver à tela se houver erro)."""
    erros, novo = {}, {}
    alunos = (formulario.get('alunos_ativos') or '').strip()
    if alunos.isdigit() and 1 <= int(alunos) <= 100000:
        novo['alunos_ativos'] = int(alunos)
    else:
        erros['alunos_ativos'] = 'Use um número de alunos maior que zero.'
    try:
        novo['faturamento'] = ler_reais(formulario.get('faturamento'))
        if not (0 < novo['faturamento'] <= META_FATURAMENTO_MAXIMA):
            raise ValueError
    except ValueError:
        erros['faturamento'] = 'Informe um valor maior que zero, como 35.000,00.'
    retencao = (formulario.get('retencao') or '').strip()
    if retencao.isdigit() and 1 <= int(retencao) <= 100:
        novo['retencao'] = int(retencao)
    else:
        erros['retencao'] = 'A retenção vai de 1% a 100%.'
    devolver = {'alunos_ativos': novo.get('alunos_ativos', alunos), 'retencao': novo.get('retencao', retencao),
                'faturamento': float(novo['faturamento']) if 'faturamento' not in erros else ''}
    return novo, erros, devolver


def salvar_metas(valores):
    conta = _conta()
    conta.meta_alunos_ativos, conta.meta_faturamento, conta.meta_retencao = valores['alunos_ativos'], valores['faturamento'], valores['retencao']
    db.session.commit()


# ------------------------------------------------------------------ inatividade automática
def inativar_quem_nao_renovou(conta, hoje=None):
    """
    A regra "o aluno vira Inativo sozinho depois de X dias sem renovar": desativa os alunos
    ativos da conta cujo vencimento passou há mais de `inatividade_dias`. Quem nunca pagou não
    tem vencimento e não é tocado. Não apaga nada. Devolve quantos foram desativados.
    Tem de ser chamada com um usuário da conta logado (usa o filtro de conta).
    """
    hoje = hoje or date.today()
    if not conta.inatividade_ligada:
        return 0
    limite = hoje - timedelta(days=conta.inatividade_dias)
    vencimento = vencimentos_da_conta()
    desativados = 0
    for aluno in da_conta(Aluno).filter(Aluno.ativo.is_(True)).all():
        if aluno.id in vencimento and vencimento[aluno.id] < limite:
            aluno.ativo = False          # a data da inativação é guardada sozinha (models.py)
            desativados += 1
    return desativados


def aplicar_inatividade_uma_vez_por_dia(hoje=None):
    """
    Roda a regra de inatividade da conta logada no máximo uma vez por dia (a data da última vez
    fica em contas.inatividade_conferida_em). É chamada quando o painel abre: assim a regra
    funciona sem depender de uma tarefa agendada no servidor.
    """
    hoje = hoje or date.today()
    conta = _conta()
    if conta.inatividade_conferida_em == hoje:
        return 0
    desativados = inativar_quem_nao_renovou(conta, hoje)
    conta.inatividade_conferida_em = hoje
    db.session.commit()
    return desativados
