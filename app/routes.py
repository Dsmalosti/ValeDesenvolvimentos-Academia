from app import db
from flask import render_template, url_for, request, redirect, flash, Blueprint
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime

from app.models import Aluno
import traceback 


main_blueprint = Blueprint('main', __name__)

# Rota inicial
@main_blueprint.route('/')
@login_required
def homepage():
    aluno = Aluno.query.all()

    # verifica quantos alunos ativos e manda para notifição
    ativos = sum(1 for a in aluno if a.ativo == 'ativo')

    # calcular numero de aniversariantes 

    hoje = datetime.utcnow().date()

    aniversariantes = sum(
        1 for a in aluno
        if a.data_nascimento 
        and a.data_nascimento.day == hoje.day 
        and a.data_nascimento.month == hoje.month
    )
    return render_template('index.html', ativos=ativos, aniversariantes=aniversariantes)






