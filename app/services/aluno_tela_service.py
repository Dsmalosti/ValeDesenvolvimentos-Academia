"""
Telas de alunos do front novo: lista, busca, perfil, cadastro e edição.

[back-07-alunos] Criado nesta branch. Monta as variáveis que os templates de
templates/alunos/ declaram no topo, valida o formulário e grava. Tudo só da conta de quem
está logado (helpers/conta.py); a situação de pagamento vem do situacao_service.py.

O formulário do front é HTML puro (não usa WTForms): os campos chegam em request.form com os
mesmos nomes das colunas, as datas vêm como dd/mm/aaaa e o CPF e o telefone vêm com máscara.
Em caso de erro a tela espera `erros = {campo: mensagem}` e os valores digitados de volta.
"""
import csv
import io
import re
from datetime import date, datetime

from flask_login import current_user
from sqlalchemy import func

from app.extensions.database import db
from app.helpers.conta import conta_id, da_conta, fichas_da_conta
from app.models import Aluno, Ficha, Pagamento, Plano
from app.services.situacao_service import linha_do_aluno, vencimentos_da_conta

POR_PAGINA = 8
MAX_OBSERVACOES = 1000   # o banco aceitaria qualquer tamanho; o limite evita texto gigante na tela
FORMAS = {'pix': 'PIX', 'debito': 'Débito', 'credito': 'Crédito', 'dinheiro': 'Dinheiro'}
DIAS = {'segunda': 'Segunda', 'terca': 'Terça', 'quarta': 'Quarta', 'quinta': 'Quinta', 'sexta': 'Sexta',
        'sabado': 'Sábado', 'domingo': 'Domingo'}


def _so_digitos(texto):
    return re.sub(r'\D', '', texto or '')


def _cpf_valido(numeros):
    """
    Confere os dois dígitos verificadores do CPF (a mesma conta que o app.js do front faz no
    navegador). `numeros` são só os 11 números. CPF com todos os números iguais não vale.
    """
    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False
    for posicao in (9, 10):
        soma = sum(int(numeros[k]) * (posicao + 1 - k) for k in range(posicao))
        if (soma * 10 % 11) % 10 != int(numeros[posicao]):
            return False
    return True


def _data(texto):
    """'25/12/1990' -> date. Devolve None se estiver vazio; levanta ValueError se não for uma data."""
    texto = (texto or '').strip()
    if not texto:
        return None
    return datetime.strptime(texto, '%d/%m/%Y').date()


def _dmy(d):
    return d.strftime('%d/%m/%Y') if d else ''


# ------------------------------------------------------------------ lista e busca
def _alunos_com_situacao(hoje):
    """Todos os alunos da conta, do mais novo para o mais antigo, já no formato das telas."""
    vencimento = vencimentos_da_conta()
    alunos = da_conta(Aluno).order_by(Aluno.data_cadastro.desc(), Aluno.id.desc()).all()
    return [linha_do_aluno(a, vencimento.get(a.id), hoje) for a in alunos]


def _casa_com_a_busca(linha, q):
    """Busca por pedaço do nome (sem diferenciar maiúscula) ou por pelo menos 3 números do CPF."""
    q = q.strip().lower()
    numeros = _so_digitos(q)
    return q in linha['nome'].lower() or (len(numeros) > 2 and numeros in _so_digitos(linha['cpf']))


def _janela(atual, total):
    """Números de página a mostrar: 1 2 3 … 7 8 9 … 20. None marca as reticências."""
    if total <= 7:
        return list(range(1, total + 1))
    paginas = sorted({1, 2, 3, atual - 1, atual, atual + 1, total} & set(range(1, total + 1)))
    saida, anterior = [], 0
    for n in paginas:
        if n - anterior > 1:
            saida.append(None)
        saida.append(n)
        anterior = n
    return saida


def filtrar(argumentos, hoje=None):
    """Aplica ?q=&status=&plano= e devolve (linhas filtradas, todas as linhas, filtro em uso)."""
    hoje = hoje or date.today()
    q = (argumentos.get('q') or '').strip()
    status = argumentos.get('status') or 'todos'
    plano = argumentos.get('plano') or ''
    todas = _alunos_com_situacao(hoje)
    filtradas = []
    for linha in todas:
        if status == 'ativos' and not linha['ativo']:
            continue
        if status in ('pendente', 'inativo') and linha['status'] != status:
            continue
        if plano and str(linha['plano_id']) != plano:
            continue
        if q and not _casa_com_a_busca(linha, q):
            continue
        filtradas.append(linha)
    return filtradas, todas, {'q': q, 'status': status, 'plano': plano}


def contexto_da_lista(argumentos):
    """Variáveis de alunos/lista.html."""
    filtradas, todas, filtro = filtrar(argumentos)
    total_paginas = max(1, -(-len(filtradas) // POR_PAGINA))
    try:
        pagina = int(argumentos.get('pagina', 1))
    except (TypeError, ValueError):
        pagina = 1
    pagina = min(max(1, pagina), total_paginas)
    fatia = filtradas[(pagina - 1) * POR_PAGINA: pagina * POR_PAGINA]
    hoje = date.today()
    return {
        'alunos': fatia,
        'contagem': {'total': len(todas), 'ativos': sum(x['ativo'] for x in todas),
                     'pendentes': sum(x['status'] == 'pendente' for x in todas),
                     'inativos': sum(x['status'] == 'inativo' for x in todas)},
        'filtro': filtro,
        # só o que está em uso vai para os links de página e para o "Exportar"
        'filtro_qs': {k: v for k, v in {'q': filtro['q'], 'plano': filtro['plano'],
                                        'status': filtro['status'] if filtro['status'] != 'todos' else ''}.items() if v},
        'planos': planos_do_formulario(),
        'pag': {'atual': pagina, 'total': total_paginas, 'janela': _janela(pagina, total_paginas),
                'de': (pagina - 1) * POR_PAGINA + 1 if filtradas else 0,
                'ate': (pagina - 1) * POR_PAGINA + len(fatia), 'total_registros': len(filtradas)},
        # o botão "Novo aluno" do desktop abre este mesmo formulário num popup
        'aluno': aluno_em_branco(hoje), 'erros': {}, 'modo': 'novo',
        'abrir_novo': argumentos.get('novo') == '1',
    }


def buscar(q, limite=8):
    """Busca ao vivo: no máximo `limite` alunos; com menos de 2 letras não busca nada."""
    q = (q or '').strip()
    if len(q) < 2:
        return []
    return [x for x in _alunos_com_situacao(date.today()) if _casa_com_a_busca(x, q)][:limite]


def recentes(limite=3):
    """Os últimos cadastrados, mostrados como atalho na tela de busca."""
    return _alunos_com_situacao(date.today())[:limite]


def _celula(texto):
    """
    Texto pronto para uma célula da planilha. Se começar com = + - ou @, o Excel trata como
    FÓRMULA e executa; um aluno cadastrado com o nome "=HYPERLINK(...)" viraria um link clicável
    na planilha do dono. O apóstrofo na frente faz o Excel tratar como texto comum.
    """
    texto = str(texto or '')
    return "'" + texto if texto[:1] in ('=', '+', '-', '@', '\t', '\r') else texto


def exportar_csv(argumentos):
    """A lista filtrada em CSV (separado por ponto e vírgula, como o Excel em português espera)."""
    filtradas, _, _ = filtrar(argumentos)
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=';')
    escritor.writerow(['Nome', 'CPF', 'Telefone', 'E-mail', 'Plano', 'Vencimento', 'Status'])
    for x in filtradas:
        escritor.writerow([_celula(x['nome']), _celula(x['cpf']), _celula(x['telefone']), _celula(x['email']),
                           _celula(x['plano']), _dmy(x['vence_data']), x['status']])
    return '\ufeff' + saida.getvalue()   # o BOM (marca no começo do arquivo) faz o Excel ler os acentos certo


# ------------------------------------------------------------------ perfil
def contexto_do_perfil(aluno, hoje=None):
    """Variáveis de alunos/detalhe.html para um aluno que já se sabe ser da conta."""
    hoje = hoje or date.today()
    pagamentos = (da_conta(Pagamento).filter_by(aluno_id=aluno.id)
                  .order_by(Pagamento.data_pagamento.desc(), Pagamento.id.desc()).all())
    vencimento = max((p.data_vencimento for p in pagamentos), default=None)
    perfil = linha_do_aluno(aluno, vencimento, hoje)
    inicio = aluno.data_inicio or (aluno.data_cadastro.date() if aluno.data_cadastro else None)
    perfil.update({
        'inicio': _dmy(inicio) or '—',
        'desde': inicio.strftime('%m/%Y') if inicio else '—',
        'vence_completo': _dmy(vencimento) or 'Sem pagamento registrado',
        'forma': aluno.forma_pagamento or '',
        'forma_txt': FORMAS.get(aluno.forma_pagamento, 'Não informada'),
        'observacoes': aluno.observacoes or '',
        # bloquear e liberar acesso na recepção faz parte do módulo de frequência, que ainda não existe
        'acesso_liberado': True,
    })

    ficha = (fichas_da_conta().filter(Ficha.aluno_id == aluno.id, Ficha.ativo.is_(True))
             .order_by(Ficha.data_criacao.desc()).first())
    return {
        'aluno': perfil,
        'pagamentos': [{'data': _dmy(p.data_pagamento), 'forma': FORMAS.get(p.forma_pagamento, p.forma_pagamento or '—'),
                        'valor': float(p.valor), 'origem': 'manual', 'quem': '', 'status': 'pago'} for p in pagamentos],
        'total_ano': sum(float(p.valor) for p in pagamentos if p.data_pagamento.year == hoje.year),
        'freq': None,          # precisa do módulo de frequência
        'avaliacao': None,     # precisa do módulo de avaliações
        'ficha': {'treinos': [DIAS.get(t.dia_semana, t.dia_semana or 'Treino') for t in ficha.treinos] or [ficha.nome],
                  'atualizada': _dmy(ficha.data_criacao.date() if ficha.data_criacao else None) or '—',
                  'por': current_user.conta.nome} if ficha else None,
    }


# ------------------------------------------------------------------ formulário
def planos_do_formulario():
    """Planos da conta para o <select>. O template mostra só os ativos e lê id, nome, valor e duracao_dias."""
    return [{'id': p.id, 'nome': p.nome, 'valor': float(p.valor), 'duracao_dias': int(p.duracao_dias or 0),
             'ativo': bool(p.ativo)} for p in da_conta(Plano).order_by(Plano.nome).all()]


def aluno_em_branco(hoje=None):
    hoje = hoje or date.today()
    return {'data_inicio_txt': _dmy(hoje), 'dia_vencimento': min(hoje.day, 28)}


def aluno_para_o_formulario(aluno):
    """Um aluno do banco no formato que alunos/_campos.html lê."""
    return {
        'id': aluno.id, 'nome': aluno.nome or '', 'cpf': aluno.cpf or '', 'telefone': aluno.telefone or '',
        'email': aluno.email or '', 'data_nascimento_txt': _dmy(aluno.data_nascimento),
        'data_inicio_txt': _dmy(aluno.data_inicio), 'plano_id': aluno.plano_id,
        'forma_pagamento': aluno.forma_pagamento or '', 'dia_vencimento': aluno.dia_vencimento or '',
        'observacoes': aluno.observacoes or '',
    }


def do_formulario(formulario, aluno_id=None, nome_original=None):
    """Devolve à tela o que a pessoa digitou, para ela não ter de preencher tudo de novo depois de um erro."""
    dados = {k: (formulario.get(k) or '') for k in ('nome', 'cpf', 'telefone', 'email', 'forma_pagamento',
                                                     'dia_vencimento', 'observacoes')}
    dados['data_nascimento_txt'] = formulario.get('data_nascimento') or ''
    dados['data_inicio_txt'] = formulario.get('data_inicio') or ''
    plano = formulario.get('plano_id') or ''
    dados['plano_id'] = int(plano) if plano.isdigit() else ''
    if aluno_id:
        dados['id'] = aluno_id
        dados['nome'] = dados['nome'] or nome_original or ''
    return dados


def validar(formulario, aluno=None, hoje=None):
    """
    Confere o formulário. Devolve (valores prontos para gravar, erros {campo: mensagem}).
    `aluno` é o registro em edição (None no cadastro). A validação do navegador é só conveniência:
    quem garante a regra é esta função.
    """
    hoje = hoje or date.today()
    novo = aluno is None
    erros, v = {}, {}

    v['nome'] = ' '.join((formulario.get('nome') or '').split())
    if len(v['nome'].split()) < 2:
        erros['nome'] = 'Informe nome e sobrenome.'
    elif len(v['nome']) > 100:
        erros['nome'] = 'O nome pode ter no máximo 100 letras.'

    cpf = _so_digitos(formulario.get('cpf'))
    if not _cpf_valido(cpf):
        erros['cpf'] = 'CPF inválido. Confira os 11 números.'
    else:
        v['cpf'] = f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'
        # compara só os números, porque cadastros antigos podem ter sido gravados sem os pontos
        sem_pontos = func.replace(func.replace(Aluno.cpf, '.', ''), '-', '')
        repetido = da_conta(Aluno).filter(sem_pontos == cpf)
        if not novo:
            repetido = repetido.filter(Aluno.id != aluno.id)
        if repetido.first():
            erros['cpf'] = 'Já existe um aluno com este CPF.'

    v['telefone'] = (formulario.get('telefone') or '').strip()[:20]
    if len(_so_digitos(v['telefone'])) < 10:
        erros['telefone'] = 'Informe o telefone com DDD.'

    email = (formulario.get('email') or '').strip().lower()
    v['email'] = email or None        # vazio vira None: vários alunos podem não ter e-mail
    if email:
        if len(email) > 120 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
            erros['email'] = 'E-mail inválido.'
        else:
            repetido = da_conta(Aluno).filter(func.lower(Aluno.email) == email)
            if not novo:
                repetido = repetido.filter(Aluno.id != aluno.id)
            if repetido.first():
                erros['email'] = 'Já existe um aluno com este e-mail.'

    try:
        v['data_nascimento'] = _data(formulario.get('data_nascimento'))
        if v['data_nascimento'] and not (date(1900, 1, 1) <= v['data_nascimento'] <= hoje):
            erros['data_nascimento'] = 'Confira a data de nascimento.'
    except ValueError:
        erros['data_nascimento'] = 'Data inválida. Use dia/mês/ano.'

    plano_texto = formulario.get('plano_id') or ''
    plano = da_conta(Plano).filter_by(id=int(plano_texto)).first() if plano_texto.isdigit() else None
    if not plano:
        erros['plano_id'] = 'Escolha um plano.'
    elif not plano.ativo and (novo or plano.id != aluno.plano_id):
        erros['plano_id'] = 'Este plano está pausado. Escolha outro.'
    else:
        v['plano_id'] = plano.id

    v['forma_pagamento'] = formulario.get('forma_pagamento') or ''
    if v['forma_pagamento'] not in FORMAS:
        erros['forma_pagamento'] = 'Escolha a forma de pagamento.'

    dia = formulario.get('dia_vencimento') or ''
    if dia.isdigit() and 1 <= int(dia) <= 28:
        v['dia_vencimento'] = int(dia)
    else:
        erros['dia_vencimento'] = 'Escolha um dia entre 1 e 28.'

    if novo:   # a data de início só aparece no cadastro
        try:
            v['data_inicio'] = _data(formulario.get('data_inicio'))
            if not v['data_inicio']:
                erros['data_inicio'] = 'Informe a data de início.'
        except ValueError:
            erros['data_inicio'] = 'Data inválida. Use dia/mês/ano.'

    v['observacoes'] = (formulario.get('observacoes') or '').strip() or None
    if v['observacoes'] and len(v['observacoes']) > MAX_OBSERVACOES:
        erros['observacoes'] = f'As observações podem ter no máximo {MAX_OBSERVACOES} letras.'
    return v, erros


def aviso_dos_erros(erros):
    """
    O aviso que aparece no topo quando o formulário volta com erro. Os campos mostram a própria
    mensagem embaixo deles; o de observações é o único que o front não desenha com mensagem,
    então o erro dele vai no próprio aviso.
    """
    return erros.get('observacoes') or 'Revise os campos destacados.'


def criar(valores):
    """Grava um aluno novo na conta de quem está logado. Já entra como ativo."""
    aluno = Aluno(ativo=True, conta_id=conta_id(), instrutor_id=current_user.id, **valores)
    db.session.add(aluno)
    db.session.commit()
    return aluno


def atualizar(aluno, valores):
    for campo, valor in valores.items():
        setattr(aluno, campo, valor)
    db.session.commit()
    return aluno
