from app.extensions.database import db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.alunos.form import AlunoForm
from app.services.aluno_service import AlunoService
from app.models import Aluno
from app.exceptions import BusinessError

alunos_blueprint = Blueprint('alunos', __name__, url_prefix='/alunos', template_folder='templates')


# Rota cadastro aluno
@alunos_blueprint.route('/cadastro/', methods=['GET', 'POST'])
@login_required
def cadastroAluno():
    
    form = AlunoForm()

    if form.validate_on_submit():
        try:
            AlunoService.criar_aluno(form.data)

            flash("Aluno cadastrado com sucesso!", "success")
            return redirect(url_for("main.homepage"))

        except BusinessError as e:
            flash(str(e), "danger")

        except Exception:
            flash("Erro inesperado ao cadastrar aluno", "danger")

    return render_template("aluno_form.html", form=form)


#Rota para listar aluno
@alunos_blueprint.route('/listar/')
@login_required
def listarAlunos():
    alunos = Aluno.query.all()

    return render_template('aluno-lista.html', alunos=alunos)

# Rota para editar aluno
@alunos_blueprint.route('/editar/<int:aluno_id>', methods=['GET', 'POST'])
@login_required
def editarAluno(aluno_id):
    aluno = Aluno.query.get_or_404(aluno_id)
    form = AlunoForm(obj=aluno)  # 👈 pré-preenche o form

    if form.validate_on_submit():
        dados = {
            "nome": form.nome.data,
            "email": form.email.data,
            "telefone": form.telefone.data,
            "cpf": form.cpf.data,
            "ativo": form.ativo.data,
            "plano_id": form.plano_id.data,
        }

        try:
            AlunoService.editar_aluno(aluno_id, dados)
            flash("Aluno atualizado com sucesso", "success")
            return redirect(url_for("alunos.listarAlunos"))

        except BusinessError as e:
            flash(str(e), "error")

    return render_template(
        "aluno_form.html",
        form=form,
        titulo="Editar Aluno"
    )

# Rota para excluir aluno
@alunos_blueprint.route('/excluir/<int:aluno_id>', methods=['POST'])
@login_required
def excluirAluno(aluno_id):
    try:
        AlunoService.excluir_aluno(aluno_id)
        flash("Aluno excluído com sucesso", "success")
    except BusinessError as e:
        flash(str(e), "error")

    return redirect(url_for("alunos.listarAlunos"))