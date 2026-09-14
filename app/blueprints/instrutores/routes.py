from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.blueprints.instrutores.form import CadastroForm, ContaForm, LoginForm
from app.exceptions import BusinessError
from app.helpers.navegacao import url_segura
from app.services.auth_service import AuthService
from app.services.instrutor_service import InstrutorService

instrutores_blueprint = Blueprint('instrutores', __name__, url_prefix='/instrutores', template_folder='templates')


# Rota criação de conta
@instrutores_blueprint.route('/cadastro/', methods=['GET', 'POST'])
def cadastroInstrutor():
    if current_user.is_authenticated:
        return redirect(url_for('main.homepage'))

    form = CadastroForm()
    if form.validate_on_submit():
        try:
            instrutor = InstrutorService.criar_instrutor(form.data)
            login_user(instrutor, remember=True)
            flash("Conta criada! Siga os primeiros passos para configurar sua academia.", "success")
            return redirect(url_for('main.homepage'))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('instrutores/cadastro.html', form=form)


# Rota para logar
@instrutores_blueprint.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.homepage'))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            instrutor = AuthService.autenticar_instrutor(form.email.data, form.senha.data)
        except BusinessError as e:
            flash(str(e), "danger")
        else:
            login_user(instrutor, remember=form.lembrar.data)
            destino = request.args.get('next')
            return redirect(destino if url_segura(destino) else url_for('main.homepage'))

    return render_template('instrutores/login.html', form=form)


# Rota para deslogar (POST para não ser disparada por links/imagens de terceiros)
@instrutores_blueprint.route('/sair/', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for('instrutores.login'))


# Rota dados da conta
@instrutores_blueprint.route('/conta/', methods=['GET', 'POST'])
@login_required
def conta():
    form = ContaForm(obj=current_user, instrutor_id=current_user.id)

    if form.validate_on_submit():
        try:
            InstrutorService.atualizar_conta(current_user, form.data)
            flash("Dados da conta atualizados.", "success")
            return redirect(url_for('instrutores.conta'))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('instrutores/conta.html', form=form)


# Endereço antigo do painel administrativo
@instrutores_blueprint.route('/painel/')
@login_required
def painelAdm():
    return redirect(url_for('main.homepage'))
