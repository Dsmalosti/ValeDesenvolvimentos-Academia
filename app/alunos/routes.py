from app import  db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.alunos.form import AlunoForm
from app.models import Aluno

alunos_blueprint = Blueprint('alunos', __name__, url_prefix='/alunos', template_folder='templates')


# Rota cadastro aluno
@alunos_blueprint.route('/cadastro/', methods=['GET', 'POST'])
@login_required
def cadastroAluno():
    form = AlunoForm()
    if form.validate_on_submit():
        aluno = Aluno(
            nome=form.nome.data,
            email=form.email.data,
            telefone=form.telefone.data,
            data_nascimento=form.data_nascimento.data,
            cpf=form.cpf.data,
            ativo=form.ativo.data,
            plano_id=form.plano_id.data
        )
        db.session.add(aluno)
        db.session.commit()
        flash('Aluno cadastrado com sucesso!', 'success')
        return redirect(url_for('main.homepage'))
    
    return render_template('aluno_form.html', form=form, titulo='Cadastrar Aluno')

#Rota para listar aluno
@alunos_blueprint.route('/listar/')
@login_required
def listarAlunos():
    alunos = Aluno.query.all()

    return render_template('aluno-lista.html', alunos=alunos)

# Rota para editar aluno
@alunos_blueprint.route('/editar/<int:aluno_id>', methods=['GET', 'POST'])
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
