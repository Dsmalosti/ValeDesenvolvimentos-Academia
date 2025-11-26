from app import  db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.fichas.form import TreinoForm, FichaForm
from app.models import Treino, Aluno, Ficha, Exercicio

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
def criarTreino(ficha_id):
    ficha = Ficha.query.get_or_404(ficha_id)

    form = TreinoForm()

    # pegar o maior número de ordem já existente nesse ficha
    ultima_ordem = (Treino.query.filter_by(ficha_id=ficha_id).order_by(Treino.ordem.desc()).first())

    ordem_nova = (ultima_ordem.ordem + 1) if ultima_ordem else 1


    # Preenche o select de exercícios
    form.exercicio_id.choices = [
        (e.id, e.nome) for e in Exercicio.query.order_by(Exercicio.nome).all()
    ]

    # ficha fixo, então oculta o select e coloca valor direto
    form.ficha_id.choices = [(ficha.id, ficha.nome)]

    if form.validate_on_submit():
        treino = Treino(
            ficha_id=ficha.id,
            exercicio_id=form.exercicio_id.data,
            series=form.series.data,
            repeticoes=form.repeticoes.data,
            carga=form.carga.data,
            descanso=form.descanso.data,
            ordem=ordem_nova,
            observacoes=form.observacoes.data
        )

        db.session.add(treino)
        db.session.commit()

        
        return redirect(url_for("fichas.fichaDetalhes", ficha_id=ficha.id))

    return render_template(
        "treino_form.html",
        form=form,
        ficha=ficha,
        form_type="create"
    )