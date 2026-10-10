from app.extensions.database import db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.fichas.form import TreinoForm, FichaForm, TreinoExercicioForm
from app.models import Treino, Aluno, Ficha, Exercicio, TreinoExercicio
from app.helpers.conta import da_conta, exigir_login_em, fichas_da_conta, treinos_da_conta

fichas_blueprint = Blueprint('fichas', __name__, url_prefix='/fichas', template_folder='templates')
exigir_login_em(fichas_blueprint)  # [back-03-isolamento] toda rota daqui exige login, mesmo as futuras

# [back-03-isolamento] Em todas as rotas abaixo, a ficha e o treino passaram a ser buscados SÓ
# dentro da conta de quem está logado (fichas_da_conta / treinos_da_conta). Antes eram
# Ficha.query.get_or_404(id) e Treino.query.get_or_404(id): qualquer pessoa logada abria,
# editava e apagava a ficha de outra academia trocando o número na URL.

# Criar tficha
@fichas_blueprint.route('/novo/', methods=['GET', 'POST'])
@login_required  # [back-03-isolamento] antes: sem login. Qualquer pessoa na internet criava ficha.
def criarFicha():
    form = FichaForm()

    # preencher select de alunos
    # [back-03-isolamento] antes: Aluno.query.order_by(Aluno.nome).all(), com os alunos de
    # todas as academias. O WTForms só aceita valor que esteja nas opções, então este filtro
    # também impede criar ficha para aluno de outra conta.
    form.aluno_id.choices = [(a.id, a.nome) for a in da_conta(Aluno).order_by(Aluno.nome).all()]

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
@login_required  # [back-03-isolamento] antes: sem login. Qualquer pessoa na internet lia a ficha.
def fichaDetalhes(ficha_id):
    ficha = fichas_da_conta().filter(Ficha.id == ficha_id).first_or_404()  # [back-03-isolamento]
    return render_template("ficha-detalhes.html", ficha=ficha)

# Rota listar
@fichas_blueprint.route('/listar/')
@login_required
def listarFichas():
    # [back-03-isolamento] antes: Ficha.query.all(), a lista de todas as academias.
    fichas = fichas_da_conta().all()

    return render_template('ficha-lista.html', fichas=fichas)

# Rota editar
# [back-02-limpeza] antes: methods=['Get', 'POST']. Funcionava porque o Flask converte para maiúsculas.
@fichas_blueprint.route('/editar/<int:ficha_id>', methods=['GET', 'POST'])
@login_required
def editarFicha(ficha_id):
    ficha = fichas_da_conta().filter(Ficha.id == ficha_id).first_or_404()  # [back-03-isolamento]
    form = FichaForm(obj=ficha)
    # [back-03-isolamento] antes: Aluno.query.all()
    form.aluno_id.choices = [(a.id, a.nome) for a in da_conta(Aluno).all()]
    if request.method == "GET":
        form.aluno_id.data = ficha.aluno_id


    if form.validate_on_submit():
        form.populate_obj(ficha)
        db.session.commit()

        return redirect(url_for('fichas.listarFichas'))

    return render_template('treino_form.html', form=form)

# Rota excluir
# [back-02-limpeza] antes: '/excuir/<int:ficha_id>' (erro de digitação). O template usa url_for, então segue funcionando.
@fichas_blueprint.route('/excluir/<int:ficha_id>', methods=['POST'])
@login_required
def excluirFicha(ficha_id):
    ficha = fichas_da_conta().filter(Ficha.id == ficha_id).first_or_404()  # [back-03-isolamento]
    db.session.delete(ficha)
    db.session.commit()
    return redirect(url_for('fichas.listarFichas'))

# criar treino
@fichas_blueprint.route("/<int:ficha_id>/treino/novo", methods=["GET", "POST"])
@login_required
def criarTreino(ficha_id):
    ficha = fichas_da_conta().filter(Ficha.id == ficha_id).first_or_404()  # [back-03-isolamento]

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
    treino = treinos_da_conta().filter(Treino.id == treino_id).first_or_404()  # [back-03-isolamento]
    form = TreinoForm(obj=treino)

    form.id.data = treino.id
    form.ficha_id.data = treino.ficha_id

    if form.validate_on_submit():
        treino.dia_semana = form.dia_semana.data
        db.session.commit()
        return redirect(url_for("fichas.fichaDetalhes", ficha_id=treino.ficha_id))

    return render_template("treino_form.html", form=form)

#excluir treino
# [back-03-isolamento] antes: methods=["GET", "POST"]. Com GET, só de abrir o endereço o treino
# era apagado: um link, uma imagem em outro site ou o "prefetch" de links do front novo apagaria
# dados sozinho. O formulário de ficha-detalhes.html já envia POST com csrf_token.
@fichas_blueprint.route("/treino/<int:treino_id>/excluir", methods=["POST"])
@login_required
def excluirTreino(treino_id):
    treino = treinos_da_conta().filter(Treino.id == treino_id).first_or_404()  # [back-03-isolamento]
    form = TreinoForm(obj=treino)
    form.ficha_id.data = treino.ficha_id
    db.session.delete(treino)
    db.session.commit()


    return redirect(url_for("fichas.fichaDetalhes", ficha_id=treino.ficha_id))

#adicionar exercicio no treino
@fichas_blueprint.route("/treino/<int:treino_id>/exercicio/adicionar", methods=["GET", "POST"])
@login_required
def adicionarExercicio(treino_id):
    treino = treinos_da_conta().filter(Treino.id == treino_id).first_or_404()  # [back-03-isolamento]
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
