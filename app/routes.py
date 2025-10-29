from app import app
from flask import render_template, url_for


# Rota inicial
@app.route('/')
def homepage():
    return render_template('index.html')

# Rota painel administrativo
@app.route('/painel-adm/')
def painelAdm():
    return render_template('painel-administrativo.html')

# Rota cadastro aluno
@app.route('/cadastro-aluno/')
def cadastroAluno():
    return render_template('cadastro-aluno.html')