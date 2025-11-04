from app import app
from flask import render_template, url_for, request, redirect

from app.models import Aluno
from app.form import AlunoForm


# Rota inicial
@app.route('/')
def homepage():
    return render_template('index.html')

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