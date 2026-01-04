from app.extensions.database import db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.fichas.form import TreinoForm, FichaForm, TreinoExercicioForm
from app.models import Treino, Aluno, Ficha, Exercicio, TreinoExercicio

fichas_blueprint = Blueprint('fichas', __name__, url_prefix='/fichas', template_folder='templates')

# Criar tficha
@fichas_blueprint.route('/novo/', methods=['GET', 'POST'])
def criarFicha():
    form = FichaForm()

    # preencher select de alunos
    form.aluno_id.choices = [(a.id, a.nome) for a in Aluno.query.order_by(Aluno.nome).all()]

    if form.validate_on_submit():
        ficha = Ficha(
            nome=form.nome.data,
            observacoes=form.observacoes.data,
            aluno_id=form.aluno_id.data,
            ativo=form.ativo.data
        )

        db.session.add(ficha)
        db.session.commit()

        return redirect(url_for('fichas.listarFichas'))

    return render_template('ficha_form.html', form=form)

# Rota detalhes 
@fichas_blueprint.route("/detalhes/<int:ficha_id>")
def fichaDetalhes(ficha_id):
    ficha = Ficha.query.get_or_404(ficha_id)
    return render_template("ficha-detalhes.html", ficha=ficha)

# Rota listar
@fichas_blueprint.route('/listar/')
@login_required
def listarFichas():
    fichas = Ficha.query.all()
    
    return render_template('ficha-lista.html', fichas=fichas)

# Rota editar
@fichas_blueprint.route('/editar/<int:ficha_id>', methods=['Get', 'POST'])
@login_required
def editarFicha(ficha_id):
    ficha = Ficha.query.get_or_404(ficha_id)
    form = FichaForm(obj=ficha)
    form.aluno_id.choices = [(a.id, a.nome) for a in Aluno.query.all()]
    if request.method == "GET":
        form.aluno_id.data = ficha.aluno_id


    if form.validate_on_submit():
        form.populate_obj(ficha)
        db.session.commit()

        return redirect(url_for('fichas.listarFichas'))
    
    return render_template('treino_form.html', form=form)

# Rota excluir
@fichas_blueprint.route('/excuir/<int:ficha_id>', methods=['POST'])
@login_required
def excluirFicha(ficha_id):
    ficha = Ficha.query.get_or_404(ficha_id)
    db.session.delete(ficha)
    db.session.commit()
    return redirect(url_for('fichas.listarFichas'))

# criar treino
@fichas_blueprint.route("/<int:ficha_id>/treino/novo", methods=["GET", "POST"])
@login_required
def criarTreino(ficha_id):
    ficha = Ficha.query.get_or_404(ficha_id)

    form = TreinoForm()
    form.ficha_id.data = ficha_id  # define o hidden field

    if form.validate_on_submit():
        treino = Treino(
            ficha_id=ficha_id,
            dia_semana=form.dia_semana.data
        )

        db.session.add(treino)
        db.session.commit()

        return redirect(url_for("fichas.fichaDetalhes", ficha_id=ficha_id))

    return render_template("treino_form.html", form=form, ficha=ficha)

# editar treino
@fichas_blueprint.route("/treino/<int:treino_id>/editar", methods=["GET", "POST"])
@login_required
def editarTreino(treino_id):
    treino = Treino.query.get_or_404(treino_id)
    form = TreinoForm(obj=treino)

    form.id.data = treino.id
    form.ficha_id.data = treino.ficha_id

    if form.validate_on_submit():
        treino.dia_semana = form.dia_semana.data
        db.session.commit()
        return redirect(url_for("fichas.fichaDetalhes", ficha_id=treino.ficha_id))

    return render_template("treino_form.html", form=form)

#excluir treino 
@fichas_blueprint.route("/treino/<int:treino_id>/excluir", methods=["GET", "POST"])
@login_required
def excluirTreino(treino_id):
    treino = Treino.query.get_or_404(treino_id)
    form = TreinoForm(obj=treino)
    form.ficha_id.data = treino.ficha_id
    db.session.delete(treino)
    db.session.commit()


    return redirect(url_for("fichas.fichaDetalhes", ficha_id=treino.ficha_id))

#adicionar exercicio no treino
@fichas_blueprint.route("/treino/<int:treino_id>/exercicio/adicionar", methods=["GET", "POST"])
@login_required
def adicionarExercicio(treino_id):
    treino = Treino.query.get_or_404(treino_id)
    form = TreinoExercicioForm()

    form.exercicio_id.choices = [
        (ex.id, ex.nome) for ex in Exercicio.query.order_by(Exercicio.nome).all()
    ]

    if form.validate_on_submit():
        novo = TreinoExercicio(
            treino_id=treino_id,
            exercicio_id=form.exercicio_id.data,
            series=form.series.data,
            repeticoes=form.repeticoes.data,
            carga=form.carga.data
        )
        db.session.add(novo)
        db.session.commit()
        return redirect(url_for("fichas.fichaDetalhes", ficha_id=treino.ficha_id))

    return render_template(
        "adicionar_exercicio.html",
        form=form,
        treino=treino
    )