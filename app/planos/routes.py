from app import  db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.planos.form import PlanoForm
from app.models import Plano

planos_blueprint = Blueprint('planos', __name__, url_prefix='/planos', template_folder='templates')

#Rota criação planos
@planos_blueprint.route('/criar/', methods=['GET', 'POST'])
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

# Rota listar plano
@planos_blueprint.route('/listar/')
@login_required
def listarPlanos():
    planos = Plano.query.all()
    

    return render_template('plano-lista.html', planos=planos)

# Rota editar plano
@planos_blueprint.route('/editar/<int:plano_id>/', methods=['GET', 'POST'])
@login_required
def editarPlano(plano_id):
    plano = Plano.query.get_or_404(plano_id)
    form = PlanoForm(obj=plano)

    if form.validate_on_submit():
        form.populate_obj(plano)
        db.session.commit()
        flash('Plano atualizado com sucesso!')
        return redirect(url_for('planos.listarPlanos'))
    
    return render_template('plano_form.html', form=form)

# Rota excluir plano
@planos_blueprint.route('/excluir/<int:plano_id>', methods=['POST'])
@login_required
def excluirPlano(plano_id):
    plano = Plano.query.get_or_404(plano_id)
    db.session.delete(plano)
    db.session.commit()
    flash('Plano excluído com sucesso!', 'success')
    return redirect(url_for('planos.listarPlanos'))


    


