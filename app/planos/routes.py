from app import  db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.planos.form import PlanoForm
from app.models import Plano

planos_blueprints = Blueprint('planos', __name__, url_prefix='/planos', template_folder='templates')

#Rota criação planos
@planos_blueprints.route('/criar/', methods=['GET', 'POST'])
@login_required
def criarPlano():
    form = PlanoForm()

    if form.validate_on_submit():
        plano = Plano(
            nome = form.nome.data,
            valor = form.valor.data,
            duracao_dias = form.duracao_dias.data,
            descricao = form.descricao.data,
            ativo = form.ativo.data
        )

        db.session.add(plano)
        db.session.commit()
        return redirect(url_for('main.homepage'))
    return render_template('plano_form.html', form=form)

