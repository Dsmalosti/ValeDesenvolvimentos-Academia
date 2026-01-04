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
    form = AlunoForm(obj=aluno)

    if form.validate_on_submit():
        form.populate_obj(aluno)  # Atualiza os campos automaticamente
        db.session.commit()
        flash('Aluno atualizado com sucesso!', 'success')
        return redirect(url_for('alunos.listarAlunos'))

    return render_template('aluno_form.html', form=form, titulo=f'Editar Aluno: {aluno.nome}')

# Rota para excluir aluno
@alunos_blueprint.route('/excluir/<int:aluno_id>', methods=['POST'])
@login_required
def excluirAluno(aluno_id):
    aluno = Aluno.query.get_or_404(aluno_id)
    db.session.delete(aluno)
    db.session.commit()

    return redirect(url_for('alunos.listarAlunos'))
