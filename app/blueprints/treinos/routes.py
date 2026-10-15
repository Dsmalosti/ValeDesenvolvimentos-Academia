"""
[back-14-treinos] Rotas das FICHAS DE TREINO do front novo (templates/treinos/).

Os nomes das funções e os endereços são os do contrato do front: 'treinos.biblioteca',
'treinos.modelo', 'treinos.atribuir', 'treinos.ficha_aluno', 'treinos.ficha_salvar',
'treinos.ex_salvar', 'treinos.treino_novo', 'treinos.ficha_excluir', 'treinos.enviar' e
'treinos.baixar'. Antes desta branch, 'treinos.biblioteca' e 'treinos.ficha_aluno' eram pontes
(em blueprints/pendentes.py) para as telas antigas de ficha, que continuam no ar em /fichas/.

Ficha de treino não é dinheiro: dono, recepção e instrutor usam todas as rotas daqui.
As regras ficam em services/treino_service.py.
"""
from datetime import date, timedelta

from flask import Blueprint, abort, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user

from app.helpers.conta import da_conta, exigir_login_em
from app.models import Aluno
from app.services import treino_service as treinos

treinos_blueprint = Blueprint('treinos', __name__)
exigir_login_em(treinos_blueprint)   # toda rota daqui exige login, inclusive as futuras


def _letra():
    """A letra do treino pedida (?t= ou campo t), em maiúscula. Inválida vira 'A'."""
    letra = (request.args.get('t') or request.form.get('t') or 'A').upper()
    return letra if letra in treinos.LETRAS else 'A'


def _aluno(id):
    """O aluno, se for da conta de quem está logado; senão 404."""
    return da_conta(Aluno).filter_by(id=id).first_or_404()


def _aluno_e_ficha(id):
    """O aluno da conta e a ficha em uso dele. 404 se o aluno é de fora ou não tem ficha."""
    aluno = _aluno(id)
    ficha = treinos.ficha_do(aluno)
    if ficha is None:
        abort(404)
    return aluno, ficha


@treinos_blueprint.route('/treinos')
def biblioteca():
    q = (request.args.get('q') or '').strip()
    fichas, total = treinos.fichas_da_biblioteca(q)
    adicionar = treinos.exercicio_visivel(request.args.get('adicionar', type=int)) if request.args.get('adicionar') else None
    return render_template('treinos/biblioteca.html', modelos=treinos.modelos_da_biblioteca(q), fichas=fichas, total_fichas=total, q=q,
                           adicionar={'id': adicionar.id, 'nome': adicionar.nome} if adicionar else None)


@treinos_blueprint.route('/treinos/modelo/<int:mid>')
def modelo(mid):
    m = treinos.modelo_por_id(mid) or abort(404)
    letra = _letra() if _letra() in m['treinos'] else next(iter(m['treinos']))
    usado = next(x['usado'] for x in treinos.modelos_da_biblioteca() if x['id'] == mid)
    return render_template('treinos/modelo.html', m=dict(m, usado=usado), letra=letra, letras=list(m['treinos']),
                           treino=treinos.treino_do_modelo(m, letra))


@treinos_blueprint.route('/treinos/modelo/<int:mid>/atribuir', methods=['GET', 'POST'])
def atribuir(mid):
    m = treinos.modelo_por_id(mid) or abort(404)
    if request.method == 'POST':
        try:
            alunos = treinos.atribuir_modelo(m, request.form.getlist('aluno_id', type=int))
        except treinos.TreinoInvalido as erro:
            flash(str(erro), 'error')
            return redirect(url_for('treinos.atribuir', mid=mid))
        if request.form.get('acao') == 'enviar':
            if len(alunos) == 1:
                return redirect(url_for('treinos.enviar', id=alunos[0].id))
            flash(f'Ficha atribuída a {len(alunos)} alunos. Envie a cada um pelo WhatsApp.', 'success')
            return redirect(url_for('treinos.biblioteca'))
        if len(alunos) > 1:
            flash(f'Ficha atribuída a {len(alunos)} alunos. Esta é a de {alunos[0].nome}.', 'success')
        return redirect(url_for('treinos.ficha_aluno', id=alunos[0].id))
    q = (request.args.get('q') or '').strip()
    return render_template('treinos/atribuir.html', m=m, alunos=treinos.alunos_para_atribuir(q), q=q, instrutor=current_user.nome,
                           valida=(date.today() + timedelta(days=treinos.VALIDADE_DIAS)).strftime('%d/%m/%Y'))


@treinos_blueprint.route('/alunos/<int:id>/ficha')
def ficha_aluno(id):
    aluno = _aluno(id)
    ficha = treinos.ficha_do(aluno)
    if ficha is None:
        # o botão "Visualizar ficha" do perfil aparece para todo aluno: quem ainda não tem ficha vai escolher um modelo
        flash(f'{aluno.nome} ainda não tem ficha. Escolha um modelo e toque em "Usar com um aluno".', 'info')
        return redirect(url_for('treinos.biblioteca'))
    return render_template('treinos/ficha.html', **treinos.contexto_da_ficha(aluno, ficha, _letra()))


@treinos_blueprint.route('/alunos/<int:id>/ficha', methods=['POST'])
def ficha_salvar(id):
    aluno, ficha = _aluno_e_ficha(id)
    treinos.salvar_ficha(ficha, request.form.get('nome'), request.form.get('objetivo'))
    flash(f'Ficha de {(aluno.nome or "aluno").split()[0]} salva.', 'success')
    return redirect(url_for('treinos.ficha_aluno', id=id, t=_letra()))


@treinos_blueprint.route('/alunos/<int:id>/ficha/exercicio', methods=['POST'])
def ex_salvar(id):
    _, ficha = _aluno_e_ficha(id)
    letra, acao, pos = _letra(), request.form.get('acao'), request.form.get('pos', type=int)
    try:
        if acao == 'adicionar':
            exercicio = treinos.adicionar_exercicio(ficha, letra, request.form.get('exercicio_id', type=int))
            flash(f'{exercicio.nome} entrou no Treino {letra}.', 'success')
        elif acao == 'remover':
            flash(f'{treinos.remover_exercicio_do_treino(ficha, letra, pos)} saiu do Treino {letra}.', 'success')
        elif acao == 'editar':
            treinos.editar_exercicio_do_treino(ficha, letra, pos, request.form)
            flash('Exercício atualizado.', 'success')
        else:
            flash('Ação desconhecida.', 'error')
    except treinos.TreinoInvalido as erro:
        flash(str(erro), 'error')
    return redirect(url_for('treinos.ficha_aluno', id=id, t=letra))


@treinos_blueprint.route('/alunos/<int:id>/ficha/treino', methods=['POST'])
def treino_novo(id):
    _, ficha = _aluno_e_ficha(id)
    try:
        return redirect(url_for('treinos.ficha_aluno', id=id, t=treinos.novo_treino(ficha)))
    except treinos.TreinoInvalido as erro:
        flash(str(erro), 'error')
        return redirect(url_for('treinos.ficha_aluno', id=id))


@treinos_blueprint.route('/alunos/<int:id>/ficha/excluir', methods=['POST'])
def ficha_excluir(id):
    aluno, ficha = _aluno_e_ficha(id)
    treinos.excluir_ficha(ficha)
    flash(f'Ficha de {(aluno.nome or "aluno").split()[0]} excluída.', 'success')
    return redirect(url_for('treinos.biblioteca'))


@treinos_blueprint.route('/alunos/<int:id>/ficha/enviar')
def enviar(id):
    aluno, ficha = _aluno_e_ficha(id)
    try:
        return render_template('treinos/enviar.html', **treinos.contexto_do_envio(aluno, ficha))
    except treinos.TreinoInvalido as erro:
        flash(str(erro), 'error')
        return redirect(url_for('treinos.ficha_aluno', id=id))


@treinos_blueprint.route('/alunos/<int:id>/ficha/baixar')
def baixar(id):
    # Por enquanto a ficha sai em TEXTO. Imagem e PDF pedem bibliotecas novas (ficaram para depois do lançamento).
    aluno, ficha = _aluno_e_ficha(id)
    resposta = make_response(treinos.texto_da_ficha(aluno, ficha))
    resposta.headers['Content-Type'] = 'text/plain; charset=utf-8'
    resposta.headers['Content-Disposition'] = f'attachment; filename=ficha-{aluno.id}.txt'
    return resposta
