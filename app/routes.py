from app import app
from flask import render_template, url_for, request, redirect
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime

from app.models import Aluno
from app.form import AlunoForm, UserForm, LoginForm


# Rota inicial
@app.route('/')
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
@app.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = form.login()
        login_user(user, remember=True)
        return redirect(url_for('homepage'))
    
    return render_template('tela-login.html', form=form)


# Cadastro instrutor
@app.route('/cadastro-instrutor/', methods=['GET', 'POST'])
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
@app.route('/sair/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Rota painel administrativo
@app.route('/painel-adm/')
@login_required
def painelAdm():
    return render_template('painel-administrativo.html')

# Rota cadastro aluno
@app.route('/cadastro-aluno/', methods=['GET', 'POST'])
@login_required
def cadastroAluno():
    form = AlunoForm()
    context = {}
    if form.validate_on_submit():
        form.save()
        return redirect(url_for('homepage'))
    
    return render_template('cadastro-aluno.html', context=context, form=form)