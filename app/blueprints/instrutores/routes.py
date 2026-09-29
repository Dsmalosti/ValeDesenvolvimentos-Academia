from app.extensions.database import db
from app.extensions.security import bcrypt
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.instrutores.form import UserForm, LoginForm
from app.models import User, Aluno
from wtforms.validators import Optional, DataRequired
from app.services.instrutor_service import InstrutorService
from app.services.auth_service import AuthService
from app.exceptions import BusinessError


instrutores_blueprint = Blueprint('instrutores', __name__, url_prefix='/instrutores', template_folder='templates')

# Rota cadastro instrutor
@instrutores_blueprint.route('/cadastro/', methods=['GET', 'POST'])
def cadastroInstrutor():
    form = UserForm()
    form.senha.validators = [DataRequired()]
    if form.validate_on_submit():
        dados = {
            "nome": form.nome.data,
            "sobrenome": form.sobrenome.data,
            "email": form.email.data,
            "senha": form.senha.data
        }

        try:
            user = InstrutorService.criar_instrutor(dados)
            login_user(user, remember=True)
            return redirect(url_for('main.homepage'))
        except BusinessError as e:
            flash(str(e), "danger")
        except Exception:
            flash("Erro inesperado ao cadastrar instrutor", "danger")

    return render_template('cadastro-instrutor.html', form=form)

# Rota listar
@instrutores_blueprint.route('/lista/')
@login_required
def listarInstrutores():
    instrutores = User.query.all()

    return render_template('instrutor-lista.html', instrutores=instrutores)

# Rota editar
@instrutores_blueprint.route('/editar/<int:instrutor_id>', methods=['GET','POST'])
@login_required
def editarInstrutor(instrutor_id):
    instrutor = User.query.get_or_404(instrutor_id)
    form = UserForm(obj=instrutor)
    form.senha.validators = [Optional()]  # remove a obrigatoriedade da senha na edição

    if form.validate_on_submit():
        dados = {
            "nome": form.nome.data,
            "sobrenome": form.sobrenome.data,
            "email": form.email.data,
        }
        if form.senha.data:
            dados["senha"] = form.senha.data

        try:
            InstrutorService.editar_instrutor(instrutor_id, dados)
            flash('Instrutor atualizado com sucesso!')
            return redirect(url_for('instrutores.listarInstrutores'))
        except BusinessError as e:
            flash(str(e), "error")

    return render_template('cadastro-instrutor.html', form=form)

# Rota excluir
@instrutores_blueprint.route('/excluir/<int:instrutor_id>', methods=['POST'])
@login_required
def excluirInstrutor(instrutor_id):
    try:
        InstrutorService.excluir_instrutor(instrutor_id)
        flash('Instrutor excluido com sucesso')
    except BusinessError as e:
        flash(str(e), "error")
    return redirect(url_for('instrutores.listarInstrutores'))

# Rota para logar
@instrutores_blueprint.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        try:
            instrutor = AuthService.autentificar_instrutor(
                email=form.email.data,
                senha=form.senha.data
            )
            login_user(instrutor)
            flash("Login realizado com sucesso", "success")
            return redirect(url_for('main.homepage'))

        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('tela-login.html', form=form)

# Rota paraa deslogar
@instrutores_blueprint.route('/sair/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('instrutores.login'))

# Rota painel administrativo
@instrutores_blueprint.route('/painel/')
@login_required
def painelAdm():
    alunos_ativos = Aluno.query.filter_by(instrutor_id=current_user.id, ativo=True).all()

    total_alunos = len(alunos_ativos)

    return render_template(
        'painel-administrativo.html',
        alunos=alunos_ativos,
        total_alunos=total_alunos,
    )