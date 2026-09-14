from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from app.blueprints.fichas.form import FichaForm, TreinoExercicioForm, TreinoForm
from app.exceptions import BusinessError
from app.extensions.database import db
from app.models import Aluno, Exercicio, Ficha, Treino, TreinoExercicio
from app.services.ficha_service import FichaService
from app.tenancy import do_instrutor, obter_do_instrutor_ou_404

fichas_blueprint = Blueprint('fichas', __name__, url_prefix='/fichas', template_folder='templates')


def _opcoes_alunos():
    alunos = do_instrutor(Aluno).order_by(Aluno.nome).all()
    return [(0, 'Selecione um aluno')] + [(a.id, a.nome) for a in alunos]


def _treino_ou_404(treino_id):
    treino = db.session.get(Treino, treino_id)
    if treino is None or treino.ficha.instrutor_id != current_user.id:
        abort(404)
    return treino


# Rota listar
@fichas_blueprint.route('/')
@fichas_blueprint.route('/listar/')
@login_required
def listarFichas():
    aluno_id = request.args.get('aluno_id', type=int)
    query = do_instrutor(Ficha).options(joinedload(Ficha.aluno)).order_by(Ficha.data_criacao.desc())
    aluno_filtro = None
    if aluno_id:
        aluno_filtro = obter_do_instrutor_ou_404(Aluno, aluno_id)
        query = query.filter(Ficha.aluno_id == aluno_id)

    return render_template('fichas/lista.html', fichas=query.all(), aluno_filtro=aluno_filtro)


# Criar ficha
@fichas_blueprint.route('/novo/', methods=['GET', 'POST'])
@login_required
def criarFicha():
    form = FichaForm()
    form.aluno_id.choices = _opcoes_alunos()
    if request.method == 'GET' and request.args.get('aluno_id', type=int):
        form.aluno_id.data = request.args.get('aluno_id', type=int)

    if form.validate_on_submit():
        try:
            ficha = FichaService.criar_ficha(current_user.id, form.data)
            flash("Ficha criada. Agora adicione os dias de treino.", "success")
            return redirect(url_for('fichas.fichaDetalhes', ficha_id=ficha.id))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('fichas/form.html', form=form, ficha=None, sem_alunos=len(form.aluno_id.choices) == 1)


# Rota detalhes
@fichas_blueprint.route('/detalhes/<int:ficha_id>')
@login_required
def fichaDetalhes(ficha_id):
    ficha = obter_do_instrutor_ou_404(Ficha, ficha_id)
    dias_usados = {treino.dia_semana for treino in ficha.treinos}
    return render_template('fichas/detalhes.html', ficha=ficha, dias_usados=dias_usados)


# Rota editar
@fichas_blueprint.route('/editar/<int:ficha_id>', methods=['GET', 'POST'])
@login_required
def editarFicha(ficha_id):
    ficha = obter_do_instrutor_ou_404(Ficha, ficha_id)
    form = FichaForm(obj=ficha)
    form.aluno_id.choices = _opcoes_alunos()

    if form.validate_on_submit():
        try:
            FichaService.editar_ficha(ficha, form.data)
            flash("Ficha atualizada com sucesso.", "success")
            return redirect(url_for('fichas.fichaDetalhes', ficha_id=ficha.id))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('fichas/form.html', form=form, ficha=ficha, sem_alunos=False)


# Rota excluir
@fichas_blueprint.route('/excluir/<int:ficha_id>', methods=['POST'])
@login_required
def excluirFicha(ficha_id):
    ficha = obter_do_instrutor_ou_404(Ficha, ficha_id)
    try:
        FichaService.excluir_ficha(ficha)
        flash("Ficha excluída com sucesso.", "success")
    except BusinessError as e:
        flash(str(e), "danger")
    return redirect(url_for('fichas.listarFichas'))


# criar treino
@fichas_blueprint.route('/<int:ficha_id>/treino/novo', methods=['GET', 'POST'])
@login_required
def criarTreino(ficha_id):
    ficha = obter_do_instrutor_ou_404(Ficha, ficha_id)
    form = TreinoForm()
    if request.method == 'GET' and request.args.get('dia'):
        form.dia_semana.data = request.args.get('dia')

    if form.validate_on_submit():
        try:
            treino = FichaService.adicionar_treino(ficha, form.dia_semana.data)
            flash(f"Treino de {treino.dia_label} criado. Adicione os exercícios.", "success")
            return redirect(url_for('fichas.adicionarExercicio', treino_id=treino.id))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('fichas/treino_form.html', form=form, ficha=ficha, treino=None)


# editar treino
@fichas_blueprint.route('/treino/<int:treino_id>/editar', methods=['GET', 'POST'])
@login_required
def editarTreino(treino_id):
    treino = _treino_ou_404(treino_id)
    form = TreinoForm(obj=treino)

    if form.validate_on_submit():
        try:
            FichaService.editar_treino(treino, form.dia_semana.data)
            flash("Treino atualizado.", "success")
            return redirect(url_for('fichas.fichaDetalhes', ficha_id=treino.ficha_id))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('fichas/treino_form.html', form=form, ficha=treino.ficha, treino=treino)


# excluir treino
@fichas_blueprint.route('/treino/<int:treino_id>/excluir', methods=['POST'])
@login_required
def excluirTreino(treino_id):
    treino = _treino_ou_404(treino_id)
    ficha_id = treino.ficha_id
    try:
        FichaService.excluir_treino(treino)
        flash("Treino excluído.", "success")
    except BusinessError as e:
        flash(str(e), "danger")
    return redirect(url_for('fichas.fichaDetalhes', ficha_id=ficha_id))


# adicionar exercicio no treino
@fichas_blueprint.route('/treino/<int:treino_id>/exercicio/adicionar', methods=['GET', 'POST'])
@login_required
def adicionarExercicio(treino_id):
    treino = _treino_ou_404(treino_id)
    form = TreinoExercicioForm()
    exercicios = (
        do_instrutor(Exercicio)
        .filter(Exercicio.ativo.is_(True))
        .order_by(Exercicio.grupo_muscular, Exercicio.nome)
        .all()
    )
    form.exercicio_id.choices = [(0, 'Selecione um exercício')] + [
        (ex.id, f"{ex.nome} ({ex.grupo_label})") for ex in exercicios
    ]

    if form.validate_on_submit():
        try:
            item = FichaService.adicionar_exercicio(treino, form.data)
            flash(f"{item.exercicio.nome} adicionado ao treino de {treino.dia_label}.", "success")
            if request.form.get('acao') == 'salvar_e_novo':
                return redirect(url_for('fichas.adicionarExercicio', treino_id=treino.id))
            return redirect(url_for('fichas.fichaDetalhes', ficha_id=treino.ficha_id))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template(
        'fichas/adicionar_exercicio.html',
        form=form,
        treino=treino,
        sem_exercicios=not exercicios,
    )


# remover exercicio do treino
@fichas_blueprint.route('/treino/exercicio/<int:item_id>/remover', methods=['POST'])
@login_required
def removerExercicio(item_id):
    item = db.session.get(TreinoExercicio, item_id)
    if item is None or item.treino.ficha.instrutor_id != current_user.id:
        abort(404)
    ficha_id = item.treino.ficha_id
    try:
        FichaService.remover_exercicio(item)
        flash("Exercício removido do treino.", "success")
    except BusinessError as e:
        flash(str(e), "danger")
    return redirect(url_for('fichas.fichaDetalhes', ficha_id=ficha_id))
