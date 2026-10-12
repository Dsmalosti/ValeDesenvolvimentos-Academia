"""
Exercícios e fichas de treino do front novo (templates/exercicios/ e templates/treinos/).

[back-14-treinos] Criado nesta branch. As rotas ficam em blueprints/exercicios/routes.py e em
blueprints/treinos/routes.py.

Como as coisas se organizam:
  - CATÁLOGO: os exercícios que a academia pode usar. São os do catálogo padrão (sem dono: todo
    mundo vê, ninguém edita) mais os que ela mesma criou (só ela vê e edita).
  - MODELOS: fichas prontas que vêm com o sistema (app/dados_padrao.py). Não ficam no banco.
  - FICHA DO ALUNO: nasce de um modelo ("usar com um aluno") e depois é ajustada. Cada aluno tem
    UMA ficha em uso: a ativa mais recente. Dar uma ficha nova a quem já tem guarda a antiga como
    inativa (ela não é apagada).
  - Uma ficha tem de 1 a 5 TREINOS (A, B, C, D, E), e cada treino tem os exercícios em ordem.

Tabelas: exercicio, ficha, treino e treino_exercicio. Já existiam; esta branch só acrescentou
colunas (ver a migration b14).
"""
import re
from collections import Counter
from datetime import date, datetime, timedelta
from urllib.parse import quote

from flask_login import current_user
from sqlalchemy import func

from app.dados_padrao import COMO_EXECUTAR_PADRAO, EXERCICIOS_PADRAO, GRUPOS, MODELOS, MUSCULOS_DO_GRUPO
from app.extensions.database import db
from app.helpers.conta import conta_id, da_conta, exercicios_proprios, exercicios_visiveis, fichas_da_conta
from app.models import Aluno, Exercicio, Ficha, Treino, TreinoExercicio, User

LETRAS = ['A', 'B', 'C', 'D', 'E']       # uma ficha aceita até 5 treinos
VALIDADE_DIAS = 90                        # por quanto tempo a ficha vale, a partir do dia em que é criada
PASSO_DA_LISTA = 8                        # quantos exercícios a lista mostra por vez ("carregar mais")
MAX_ITENS_POR_TREINO = 30
SERIES_PADRAO, REPETICOES_PADRAO, DESCANSO_PADRAO = 3, '12', '60s'
SEM_CARGA = '—'


class TreinoInvalido(Exception):
    """O pedido não pode ser atendido. A mensagem é mostrada ao usuário."""


def _dm(momento):
    return momento.strftime('%d/%m') if momento else '—'


# ------------------------------------------------------------------ catálogo de exercícios
def semear_catalogo_padrao():
    """
    Garante que o catálogo padrão do sistema está no banco: cria os exercícios que faltam e
    preenche o equipamento dos que já existem sem ele. Pode rodar quantas vezes for: não duplica.
    Devolve quantos exercícios criou. (A migration b14 faz o mesmo ao subir.)
    """
    existentes = {(e.nome or '').strip().lower(): e for e in Exercicio.query.filter(Exercicio.conta_id.is_(None)).all()}
    criados = 0
    for nome, grupo, equipamento in EXERCICIOS_PADRAO:
        atual = existentes.get(nome.lower())
        if atual is None:
            db.session.add(Exercicio(nome=nome, grupo_muscular=grupo, equipamento=equipamento, ativo=True, conta_id=None))
            criados += 1
        elif not atual.equipamento:
            atual.equipamento = equipamento
    db.session.commit()
    return criados


# A tela ANTIGA de exercícios (/exercicios/criar/) grava o grupo como código ('peito', 'ombro'...). A tela nova
# usa o nome ('Peito', 'Ombros'). Aqui o código antigo é só TRADUZIDO para mostrar; o banco não é alterado.
_GRUPO_DA_TELA_ANTIGA = {'peito': 'Peito', 'costas': 'Costas', 'ombro': 'Ombros', 'biceps': 'Bíceps', 'triceps': 'Tríceps', 'pernas': 'Pernas',
                         'gluteo': 'Glúteo', 'abdomen': 'Abdômen', 'outro': 'Outros'}


def _exercicio_para_a_tela(e):
    """Um exercício no formato que os templates esperam."""
    grupo = (e.grupo_muscular or '').strip()
    # o link vira um endereço clicável na tela: só http(s). Qualquer outra coisa gravada antes é tratada como "sem vídeo".
    video = e.video_url if re.match(r'https?://', e.video_url or '', re.IGNORECASE) else None
    return {
        'id': e.id, 'nome': e.nome, 'grupo_muscular': _GRUPO_DA_TELA_ANTIGA.get(grupo, grupo) or 'Outros', 'equipamento': e.equipamento or 'Sem equipamento',
        'video_url': video, 'com_video': bool(video),
        'duracao': 'vídeo' if video else '',                                         # o banco não guarda a duração do vídeo
        'nivel': 'Catálogo padrão' if e.conta_id is None else 'Criado pela academia',  # a tela mostra como etiqueta
        'proprio': e.conta_id is not None,
    }


def _exercicios_ativos():
    return exercicios_visiveis().filter(Exercicio.ativo.isnot(False)).order_by(func.lower(Exercicio.nome), Exercicio.id)


def catalogo():
    """Todos os exercícios que a conta pode usar, por nome."""
    return [_exercicio_para_a_tela(e) for e in _exercicios_ativos().all()]


def grupos_do_catalogo(exercicios):
    """Os grupos musculares dos filtros: os do sistema e, depois, algum outro que exista no catálogo da conta."""
    outros = sorted({e['grupo_muscular'] for e in exercicios} - set(GRUPOS))
    return GRUPOS + outros


def contexto_da_lista_de_exercicios(argumentos):
    """Variáveis de exercicios/lista.html. Busca, filtro de grupo e "carregar mais" são feitos aqui, no servidor."""
    todos = catalogo()
    q = (argumentos.get('q') or '').strip()
    grupo = argumentos.get('grupo') or ''
    limite = max(argumentos.get('limite', PASSO_DA_LISTA, type=int) or PASSO_DA_LISTA, PASSO_DA_LISTA)
    itens = [e for e in todos if (not grupo or e['grupo_muscular'] == grupo) and (not q or q.lower() in e['nome'].lower())]
    return {'exercicios': itens[:limite], 'total_filtrado': len(itens), 'total': len(todos), 'com_video': sum(e['com_video'] for e in itens),
            'grupos': grupos_do_catalogo(todos), 'filtro': {'q': q, 'grupo': grupo}, 'limite': limite,
            'proximo_limite': limite + PASSO_DA_LISTA if limite < len(itens) else None}


def exercicio_visivel(id):
    """O exercício, se a conta pode usá-lo (do catálogo padrão ou dela); senão None."""
    return exercicios_visiveis().filter(Exercicio.id == id).first()


def exercicio_proprio(id):
    """O exercício, se foi a conta que criou (só esses podem ser editados); senão None."""
    return exercicios_proprios().filter(Exercicio.id == id).first()


def detalhe_do_exercicio(e):
    dados = _exercicio_para_a_tela(e)
    dados['como_executar'] = (e.descricao or '').strip() or COMO_EXECUTAR_PADRAO
    dados['musculos'] = MUSCULOS_DO_GRUPO.get(dados['grupo_muscular'], [])
    return dados


def validar_exercicio(formulario):
    """Confere o formulário de exercício. Devolve (valores, erros {campo: mensagem})."""
    valores = {'nome': ' '.join((formulario.get('nome') or '').split()), 'grupo_muscular': (formulario.get('grupo_muscular') or '').strip(),
               'equipamento': ' '.join((formulario.get('equipamento') or '').split()), 'video_url': (formulario.get('video_url') or '').strip()}
    erros = {}
    if not valores['nome']:
        erros['nome'] = 'Dê um nome ao exercício.'
    elif len(valores['nome']) > 100:
        erros['nome'] = 'O nome pode ter no máximo 100 letras.'
    if valores['grupo_muscular'] not in GRUPOS:
        erros['grupo_muscular'] = 'Escolha o grupo muscular.'
    if len(valores['equipamento']) > 60:
        erros['equipamento'] = 'O equipamento pode ter no máximo 60 letras.'
    if valores['video_url']:
        # só http e https: um endereço "javascript:..." viraria código ao ser clicado
        if not re.match(r'https?://[^\s]+$', valores['video_url'], re.IGNORECASE) or len(valores['video_url']) > 200:
            erros['video_url'] = 'O link precisa começar com http:// ou https:// e ter até 200 caracteres.'
    return valores, erros


def salvar_exercicio(valores, exercicio=None):
    """Cria um exercício da conta ou altera um que ela criou."""
    if exercicio is None:
        exercicio = Exercicio(conta_id=conta_id(), ativo=True)
        db.session.add(exercicio)
    exercicio.nome, exercicio.grupo_muscular = valores['nome'], valores['grupo_muscular']
    exercicio.equipamento, exercicio.video_url = valores['equipamento'] or None, valores['video_url'] or None
    db.session.commit()
    return exercicio


# ------------------------------------------------------------------ modelos prontos
def modelo_por_id(mid):
    return next((m for m in MODELOS if m['id'] == mid), None)


def modelos_da_biblioteca(q=''):
    """Os modelos, com quantas fichas ATIVAS da conta nasceram de cada um."""
    usados = Counter(chave for (chave,) in fichas_da_conta().filter(Ficha.ativo.isnot(False), Ficha.modelo.isnot(None)).with_entities(Ficha.modelo))
    q = q.lower()
    return [{'id': m['id'], 'nome': m['nome'], 'sub': m['sub'], 'usado': usados[m['chave']], 'icone': m['icone'], 'tom': m['tom'], 'min': m['min']}
            for m in MODELOS if not q or q in m['nome'].lower() or q in m['sub'].lower()]


def _padrao_por_nome():
    """Os exercícios do catálogo padrão, pelo nome em minúsculas (os modelos apontam para eles pelo nome)."""
    return {(e.nome or '').lower(): e for e in Exercicio.query.filter(Exercicio.conta_id.is_(None), Exercicio.ativo.isnot(False)).all()}


def treino_do_modelo(modelo, letra):
    """Um treino do modelo no formato da tela. Exercício que não está no catálogo fica de fora."""
    por_nome = _padrao_por_nome()
    treino = modelo['treinos'][letra]
    itens = [{'ex': _exercicio_para_a_tela(por_nome[nome.lower()]), 'series': series, 'repeticoes': repeticoes, 'carga': SEM_CARGA,
              'descanso': DESCANSO_PADRAO} for nome, series, repeticoes in treino['itens'] if nome.lower() in por_nome]
    for pos, item in enumerate(itens):
        item['pos'] = pos
    return {'nome': treino['nome'], 'itens': itens}


def alunos_para_atribuir(q='', limite=8):
    """Alunos ativos da conta para receber a ficha, por pedaço do nome ou números do CPF."""
    from app.services.situacao_service import cobrancas_em_aberto_da_conta, linha_do_aluno, vencimentos_da_conta
    q = (q or '').strip().lower()
    numeros = re.sub(r'\D', '', q)
    alunos = [a for a in da_conta(Aluno).filter(Aluno.ativo.is_(True)).order_by(func.lower(Aluno.nome)).all()
              if not q or q in (a.nome or '').lower() or (len(numeros) > 2 and numeros in re.sub(r'\D', '', a.cpf or ''))][:limite]
    vencimento, em_aberto = vencimentos_da_conta(), cobrancas_em_aberto_da_conta()
    return [linha_do_aluno(a, vencimento.get(a.id), date.today(), em_aberto.get(a.id)) for a in alunos]


def atribuir_modelo(modelo, ids_dos_alunos):
    """
    Cria, para cada aluno ATIVO da conta na lista, uma ficha copiada do modelo (em rascunho). A
    ficha que ele já tinha passa a inativa: fica guardada, mas a que vale é a nova. Devolve os
    alunos que receberam.
    """
    alunos = da_conta(Aluno).filter(Aluno.id.in_(ids_dos_alunos or [0]), Aluno.ativo.is_(True)).all()
    if not alunos:
        raise TreinoInvalido('Marque pelo menos um aluno para receber a ficha.')
    por_nome = _padrao_por_nome()
    agora = datetime.now()
    for aluno in alunos:
        for antiga in Ficha.query.filter(Ficha.aluno_id == aluno.id, Ficha.ativo.isnot(False)).all():
            antiga.ativo = False
        ficha = Ficha(aluno_id=aluno.id, nome=modelo['nome'], objetivo=modelo['sub'], ativo=True, rascunho=True, modelo=modelo['chave'],
                      valida_ate=agora.date() + timedelta(days=VALIDADE_DIAS), atualizada_em=agora, atualizada_por_id=current_user.id)
        db.session.add(ficha)
        for letra, treino in modelo['treinos'].items():
            novo = Treino(ficha=ficha, letra=letra, nome=treino['nome'])
            db.session.add(novo)
            ordem = 0
            for nome, series, repeticoes in treino['itens']:
                if nome.lower() in por_nome:
                    db.session.add(TreinoExercicio(treino=novo, exercicio_id=por_nome[nome.lower()].id, series=series, repeticoes=str(repeticoes),
                                                   descanso=DESCANSO_PADRAO, ordem=ordem))
                    ordem += 1
    db.session.commit()
    return alunos


# ------------------------------------------------------------------ ficha do aluno
def ficha_do(aluno):
    """A ficha em uso do aluno: a ativa mais recente. None se ele não tem."""
    return Ficha.query.filter(Ficha.aluno_id == aluno.id, Ficha.ativo.isnot(False)).order_by(Ficha.id.desc()).first()


def treinos_da(ficha):
    """
    {letra: Treino}, em ordem. Treino antigo (criado na tela antiga, sem letra) ganha a letra pela
    ordem em que foi criado; só os 5 primeiros aparecem.
    """
    ordenados = sorted(ficha.treinos, key=lambda t: (t.letra or 'Z', t.id))
    resultado = {}
    for treino in ordenados:
        letra = treino.letra if (treino.letra in LETRAS and treino.letra not in resultado) else next((l for l in LETRAS if l not in resultado), None)
        if letra is None:
            break
        resultado[letra] = treino
    return dict(sorted(resultado.items()))


def _itens(treino):
    """Os exercícios do treino, na ordem, no formato da tela. `pos` é a posição na lista (é o que o formulário manda)."""
    linhas = sorted(treino.exercicios, key=lambda i: (i.ordem or 0, i.id))
    return [{'pos': pos, 'ex': _exercicio_para_a_tela(i.exercicio), 'series': i.series, 'repeticoes': i.repeticoes,
             'carga': i.carga or SEM_CARGA, 'descanso': i.descanso or DESCANSO_PADRAO, '_linha': i} for pos, i in enumerate(linhas)]


def _nome_do_treino(treino, letra):
    return treino.nome or (treino.dia_semana or '').capitalize() or f'Treino {letra}'


def ficha_para_a_tela(ficha):
    quando = ficha.atualizada_em or ficha.data_criacao
    quem = db.session.get(User, ficha.atualizada_por_id) if ficha.atualizada_por_id else None
    return {'nome': ficha.nome, 'objetivo': ficha.objetivo or 'não informado', 'rascunho': bool(ficha.rascunho), 'enviada': None,
            'atualizada': _dm(quando) + (f' por {quem.nome}' if quem and quem.nome else ''),
            'valida': (ficha.valida_ate or (quando.date() + timedelta(days=VALIDADE_DIAS) if quando else date.today())).strftime('%d/%m/%Y')}


def contexto_da_ficha(aluno, ficha, letra_pedida):
    """Variáveis de treinos/ficha.html (o editor da ficha do aluno)."""
    treinos = treinos_da(ficha)
    exercicios = catalogo()
    if treinos:
        letra = letra_pedida if letra_pedida in treinos else next(iter(treinos))
        itens = _itens(treinos[letra])
        for item in itens:
            item.pop('_linha')
        treino = {'nome': _nome_do_treino(treinos[letra], letra), 'itens': itens}
        letras = list(treinos)
    else:
        # ficha antiga sem nenhum treino: a tela mostra um "Treino A" vazio. Ele só é gravado quando
        # alguém adicionar o primeiro exercício (abrir a tela não grava nada).
        letra, letras, treino = 'A', ['A'], {'nome': 'Treino A', 'itens': []}
    return {'aluno': {'id': aluno.id, 'nome': aluno.nome or 'Aluno sem nome', 'telefone': aluno.telefone or ''},
            'ficha': ficha_para_a_tela(ficha), 'letra': letra, 'letras': letras,
            'proxima': next((l for l in LETRAS if l not in letras), None),
            'treino': treino, 'catalogo': exercicios, 'grupos': grupos_do_catalogo(exercicios)}


def _mexeu(ficha):
    ficha.atualizada_em, ficha.atualizada_por_id = datetime.now(), current_user.id


def salvar_ficha(ficha, nome, objetivo):
    """Nome e objetivo da ficha. "Salvar ficha" também tira a ficha do rascunho."""
    nome = ' '.join((nome or '').split())[:100]
    if nome:
        ficha.nome = nome
    ficha.objetivo = ' '.join((objetivo or '').split())[:200] or ficha.objetivo
    ficha.rascunho = False
    _mexeu(ficha)
    db.session.commit()


def _treino_da_letra(ficha, letra):
    treinos = treinos_da(ficha)
    if not treinos and letra == 'A':         # ficha sem treino nenhum: o Treino A nasce na primeira gravação
        treino = Treino(ficha=ficha, letra='A', nome='Treino A')
        db.session.add(treino)
        db.session.flush()
        return treino
    if letra not in treinos:
        raise TreinoInvalido('Esse treino não existe nesta ficha.')
    return treinos[letra]


def adicionar_exercicio(ficha, letra, exercicio_id):
    """Põe um exercício do catálogo no fim do treino. Devolve o exercício."""
    treino = _treino_da_letra(ficha, letra)
    exercicio = exercicio_visivel(exercicio_id) if exercicio_id else None
    if exercicio is None:
        raise TreinoInvalido('Exercício não encontrado no catálogo.')
    itens = _itens(treino)
    if len(itens) >= MAX_ITENS_POR_TREINO:
        raise TreinoInvalido(f'Um treino aceita até {MAX_ITENS_POR_TREINO} exercícios.')
    for pos, item in enumerate(itens):                 # renumera, para o novo entrar mesmo no fim
        item['_linha'].ordem = pos
    db.session.add(TreinoExercicio(treino=treino, exercicio_id=exercicio.id, series=SERIES_PADRAO, repeticoes=REPETICOES_PADRAO,
                                   descanso=DESCANSO_PADRAO, ordem=len(itens)))
    _mexeu(ficha)
    db.session.commit()
    return exercicio


def _item_da_posicao(ficha, letra, pos):
    itens = _itens(_treino_da_letra(ficha, letra))
    if pos is None or not (0 <= pos < len(itens)):
        raise TreinoInvalido('Exercício não encontrado neste treino.')
    return itens[pos]['_linha']


def editar_exercicio_do_treino(ficha, letra, pos, formulario):
    """Séries, repetições, carga e descanso de uma linha do treino."""
    linha = _item_da_posicao(ficha, letra, pos)
    series, repeticoes = (formulario.get('series') or '').strip(), (formulario.get('repeticoes') or '').strip()
    if not (series.isdigit() and 1 <= int(series) <= 20 and repeticoes.isdigit() and 1 <= int(repeticoes) <= 100):
        raise TreinoInvalido('Séries vão de 1 a 20 e repetições de 1 a 100.')
    linha.series, linha.repeticoes = int(series), repeticoes
    linha.carga = ' '.join((formulario.get('carga') or '').split())[:50] or None
    linha.descanso = ' '.join((formulario.get('descanso') or '').split())[:20] or DESCANSO_PADRAO
    _mexeu(ficha)
    db.session.commit()
    return linha


def remover_exercicio_do_treino(ficha, letra, pos):
    """Tira uma linha do treino. Devolve o nome do exercício. O exercício continua no catálogo."""
    linha = _item_da_posicao(ficha, letra, pos)
    nome = linha.exercicio.nome
    db.session.delete(linha)
    _mexeu(ficha)
    db.session.commit()
    return nome


def novo_treino(ficha):
    """Cria o próximo treino vazio (B, C...). Devolve a letra, ou levanta erro se a ficha já tem os 5."""
    letra = next((l for l in LETRAS if l not in treinos_da(ficha)), None)
    if letra is None or len(ficha.treinos) >= len(LETRAS):
        raise TreinoInvalido('Uma ficha aceita até 5 treinos.')
    db.session.add(Treino(ficha=ficha, letra=letra, nome=f'Treino {letra}'))
    _mexeu(ficha)
    db.session.commit()
    return letra


def excluir_ficha(ficha):
    """Apaga a ficha com os treinos e as linhas dela. Não mexe no catálogo nem nos modelos."""
    db.session.delete(ficha)      # treinos e linhas vão junto (cascade nos modelos)
    db.session.commit()


def fichas_da_biblioteca(q=''):
    """A ficha em uso de cada aluno da conta, da mexida mais recente para a mais antiga. Devolve (lista, total)."""
    fichas = fichas_da_conta().filter(Ficha.ativo.isnot(False)).order_by(Ficha.id.desc()).all()
    por_aluno = {}
    for f in fichas:
        por_aluno.setdefault(f.aluno_id, f)            # a mais recente de cada aluno
    q = q.lower()
    linhas = []
    for f in sorted(por_aluno.values(), key=lambda f: f.atualizada_em or f.data_criacao or datetime.min, reverse=True):
        nome_do_aluno = f.aluno.nome or 'Aluno sem nome'
        if q and q not in nome_do_aluno.lower() and q not in (f.nome or '').lower():
            continue
        situacao = 'rascunho' if f.rascunho else f'atualizada {_dm(f.atualizada_em or f.data_criacao)}'
        linhas.append({'aluno': {'id': f.aluno_id, 'nome': nome_do_aluno}, 'nome': f.nome, 'rascunho': bool(f.rascunho), 'sub': f'{f.nome} · {situacao}'})
    return linhas, len(por_aluno)


# ------------------------------------------------------------------ enviar pelo WhatsApp
def texto_da_ficha(aluno, ficha):
    """A ficha inteira em texto simples (é o que vai na mensagem e no arquivo para baixar)."""
    linhas = [f'{ficha.nome} · {aluno.nome}']
    for letra, treino in treinos_da(ficha).items():
        itens = _itens(treino)
        if not itens:
            continue   # treino criado e ainda vazio não vai para o aluno
        linhas.append('')
        linhas.append(f'TREINO {letra} · {_nome_do_treino(treino, letra)}')
        for item in itens:
            detalhe = f"{item['series']} x {item['repeticoes']}"
            if item['carga'] != SEM_CARGA:
                detalhe += f" · {item['carga']}"
            linhas.append(f"- {item['ex']['nome']}: {detalhe} · descanso {item['descanso']}")
    return '\n'.join(linhas)


def contexto_do_envio(aluno, ficha):
    """
    Variáveis de treinos/enviar.html. O sistema não manda nada sozinho: monta o texto e o endereço
    que abre o WhatsApp de quem está usando, com a mensagem pronta para a pessoa tocar em enviar.
    """
    treinos = treinos_da(ficha)
    if not any(t.exercicios for t in treinos.values()):
        raise TreinoInvalido('Esta ficha ainda não tem exercícios para enviar.')
    primeira = next(letra for letra, t in treinos.items() if t.exercicios)   # a prévia mostra o primeiro treino com exercício
    primeiro_nome = (aluno.nome or 'aluno').split()[0]
    mensagem = (f'Oi {primeiro_nome}! Sua ficha de treino está pronta.\n\n{texto_da_ficha(aluno, ficha)}\n\n'
                f'Qualquer dúvida é só chamar. — {current_user.conta.nome}')
    telefone = re.sub(r'\D', '', aluno.telefone or '')
    if telefone and len(telefone) <= 11:
        # DDD + número (10 ou 11 dígitos) ganha o código do Brasil. Olhar o tamanho, e não se "começa com 55":
        # 55 também é DDD (Santa Maria/RS), e o número de lá ficaria sem o código do país.
        telefone = '55' + telefone
    itens = _itens(treinos[primeira])
    for item in itens:
        item.pop('_linha')
    return {'aluno': {'id': aluno.id, 'nome': aluno.nome or 'Aluno sem nome', 'telefone': aluno.telefone or 'sem telefone cadastrado'},
            'ficha': ficha_para_a_tela(ficha), 'msg': mensagem, 'letras': list(treinos),
            'wa_url': f'https://wa.me/{telefone}?text={quote(mensagem)}',
            'primeiro': {'nome': _nome_do_treino(treinos[primeira], primeira)}, 'exs': itens,
            'total_ex': sum(len(t.exercicios) for t in treinos.values()), 'so_texto': True}
