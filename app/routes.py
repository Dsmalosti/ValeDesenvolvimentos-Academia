from app import db
from flask import render_template, url_for, request, redirect, flash, Blueprint
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime

from app.models import Aluno
from app.form import UserForm, LoginForm
import traceback 


main_blueprint = Blueprint('main', __name__)

# Rota inicial
@main_blueprint.route('/')
@login_required
def homepage():
    aluno = Aluno.query.all()

    # verifica quantos alunos ativos e manda para notifição
    ativos = sum(1 for a in aluno if a.status == 'ativo')

    # calcular numero de aniversariantes 

    hoje = datetime.utcnow().date()

    aniversariantes = sum(
        1 for a in aluno
        if a.data_nascimento 
        and a.data_nascimento.day == hoje.day 
        and a.data_nascimento.month == hoje.month
    )
    return render_template('index.html', ativos=ativos, aniversariantes=aniversariantes)

# rota de login
@main_blueprint.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = form.login()
        login_user(user, remember=True)
        return redirect(url_for('homepage'))
    
    return render_template('tela-login.html', form=form)


# Cadastro instrutor
@main_blueprint.route('/cadastro-instrutor/', methods=['GET', 'POST'])
def cadastroInstrutor():
    form = UserForm()
    if form.validate_on_submit():
        user = form.save()
        if current_user.is_authenticated:
            return redirect(url_for('homepage'))
        login_user(user, remember=True)
        return redirect(url_for('homepage'))
    return render_template('cadastro-instrutor.html', form=form)

# Rota para sair deslogar
@main_blueprint.route('/sair/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Rota painel administrativo
@main_blueprint.route('/painel-adm/')
@login_required
def painelAdm():
    # 🔹 Buscar apenas alunos ativos
    alunos_ativos = Aluno.query.filter_by(status='ativo').all()
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






