from app.extensions.database import db
from app.extensions.security import bcrypt
from flask import Blueprint,render_template, url_for, request, redirect, flash, abort
from flask_login import login_user, logout_user, current_user, login_required
from app.helpers.conta import DONO, DONO_E_RECEPCAO, conta_id, da_conta, papel_requerido
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
    # [back-06-contas-e-papeis] FECHADA por decisão do Diogo (10/10/2026). Antes, qualquer pessoa na internet abria
    # este endereço, preenchia nome, e-mail e senha e criava uma conta nova já logada, sem
    # nenhuma conferência. O endpoint continua existindo (o template antigo de login tem um
    # link para ele), mas responde 404.
    # Conta nova, por enquanto, só pelo comando `flask criar-conta` no servidor (app/cli.py).
    # O cadastro pelo próprio cliente volta na tela nova "Criar conta", com limite de
    # tentativas e confirmação de e-mail.
    abort(404)

# Rota listar
@instrutores_blueprint.route('/lista/')
@login_required
@papel_requerido(*DONO_E_RECEPCAO)  # [back-06-contas-e-papeis] instrutor não vê a lista da equipe
def listarInstrutores():
    # [back-03-isolamento] antes: User.query.all(), com os usuários de TODAS as academias.
    # [back-06-contas-e-papeis] antes: só o próprio usuário. Agora: a equipe inteira da conta.
    instrutores = da_conta(User).order_by(User.nome).all()

    return render_template('instrutor-lista.html', instrutores=instrutores)

# Rota editar
@instrutores_blueprint.route('/editar/<int:instrutor_id>', methods=['GET','POST'])
@login_required
def editarInstrutor(instrutor_id):
    # [back-03-isolamento] antes: User.query.get_or_404(instrutor_id). Qualquer pessoa logada
    # trocava o e-mail e a senha do dono de OUTRA academia mudando o número na URL.
    # [back-06-contas-e-papeis] antes: só o próprio usuário. Agora: cada um edita a si mesmo, e o dono edita
    # qualquer pessoa da PRÓPRIA conta. Usuário de outra conta responde 404; alguém da conta
    # tentando editar um colega sem ser dono recebe 403.
    instrutor = da_conta(User).filter_by(id=instrutor_id).first_or_404()
    if instrutor.id != current_user.id and current_user.papel not in DONO:
        abort(403)
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
@papel_requerido(*DONO)  # [back-06-contas-e-papeis] só o dono tira alguém da equipe
def excluirInstrutor(instrutor_id):
    # [back-03-isolamento] antes: excluía qualquer id, inclusive de outra academia.
    # [back-06-contas-e-papeis] antes: só o próprio usuário. Agora: só o dono exclui, só gente da própria conta, e
    # nunca a si mesmo (senão a academia ficaria sem dono e ninguém mais entraria nela).
    alvo = da_conta(User).filter_by(id=instrutor_id).first_or_404()
    if alvo.id == current_user.id:
        flash("Você não pode excluir o seu próprio usuário.", "error")
        return redirect(url_for('instrutores.listarInstrutores'))
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
    alunos_ativos = da_conta(Aluno).filter_by(ativo=True).all()  # [back-06-contas-e-papeis] antes: instrutor_id=current_user.id

    total_alunos = len(alunos_ativos)

    return render_template(
        'painel-administrativo.html',
        alunos=alunos_ativos,
        total_alunos=total_alunos,
    )