from app import  db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.instrutores.form import UserForm, LoginForm
from app.models import User, Aluno

instrutores_blueprints = Blueprint('instrutores', __name__, url_prefix='/instrutores', template_folder='templates')

# Rota cadastro instrutor
@instrutores_blueprints.route('/cadastro/', methods=['GET', 'POST'])
def cadastroInstrutor():
    form = UserForm()
    if form.validate_on_submit():
        user = form.save()
        if current_user.is_authenticated:
            return redirect(url_for('main.homepage'))
        login_user(user, remember=True)
        return redirect(url_for('main.homepage'))
    return render_template('cadastro-instrutor.html', form=form)

# Rota para logar
@instrutores_blueprints.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = form.login()
        login_user(user, remember=True)
        return redirect(url_for('main.homepage'))
    
    return render_template('tela-login.html', form=form)

# Rota paraa deslogar
@instrutores_blueprints.route('/sair/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('instrutores.login'))

# Rota painel administrativo
@instrutores_blueprints.route('/painel/')
@login_required
def painelAdm():
    # 🔹 Buscar apenas alunos ativos
    alunos_ativos = Aluno.query.filter_by(ativo='ativo').all()
    #Testar sem alunos
    #alunos_ativos=[]

    # 🔹 Buscar planos ativos ou com data de fim futura (ajuste conforme seu model)
    #planos_ativos = Plano.query.filter((Plano.status == 'ativo') | (Plano.data_fim >= date.today())).all()

    # 🔹 Buscar fichas ativas (se existir status)
    #fichas_ativas = FichaTreino.query.filter_by(status='ativo').all()

    # 🔹 Contadores para as notificações
    total_alunos = len(alunos_ativos)
    #total_planos = len(planos_ativos)
    #total_fichas = len(fichas_ativas)

    return render_template(
        'painel-administrativo.html',
        alunos=alunos_ativos,
        #planos=planos_ativos,
        #fichas=fichas_ativas,
        total_alunos=total_alunos,
        #total_planos=total_planos,
        #total_fichas=total_fichas
    )