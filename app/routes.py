from app import app
from flask import render_template, url_for, request, redirect
from flask_login import login_user, logout_user, current_user

from app.models import Aluno
from app.form import AlunoForm, UserForm


# Rota inicial
@app.route('/')
def homepage():
    return render_template('index.html')

# Cadastro instrutor
@app.route('/cadastro-instrutor', methods=['GET', 'POST'])
def cadastroInstrutor():
    form = UserForm()
    if form.validate_on_submit():
        user = form.save()
        if current_user.is_authenticated:
            return redirect(url_for('homepage'))
        login_user(user, remember=True)
        return redirect(url_for('homepage'))
    return render_template('cadastro-instrutor.html', form=form)

# Rota painel administrativo
@app.route('/painel-adm/')
def painelAdm():
    return render_template('painel-administrativo.html')

# Rota cadastro aluno
@app.route('/cadastro-aluno/', methods=['GET', 'POST'])
def cadastroAluno():
    form = AlunoForm()
    context = {}
    if form.validate_on_submit():
        form.save()
        return redirect(url_for('homepage'))
    
    return render_template('cadastro-aluno.html', context=context, form=form)