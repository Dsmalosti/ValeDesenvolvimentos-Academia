from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app.blueprints.planos.form import PlanoForm
from app.exceptions import BusinessError
from app.extensions.database import db
from app.models import Aluno, Plano
from app.services.plano_service import PlanoService
from app.tenancy import do_instrutor, obter_do_instrutor_ou_404

planos_blueprint = Blueprint('planos', __name__, url_prefix='/planos', template_folder='templates')


# Rota listar planos
@planos_blueprint.route('/')
@planos_blueprint.route('/listar/')
@login_required
def listarPlanos():
    planos = do_instrutor(Plano).order_by(Plano.ativo.desc(), Plano.valor).all()
    alunos_por_plano = dict(
        db.session.query(Aluno.plano_id, func.count(Aluno.id))
        .filter(Aluno.instrutor_id == current_user.id, Aluno.ativo.is_(True))
        .group_by(Aluno.plano_id)
        .all()
    )
    return render_template('planos/lista.html', planos=planos, alunos_por_plano=alunos_por_plano)


# Rota criação planos
@planos_blueprint.route('/criar/', methods=['GET', 'POST'])
@login_required
def criarPlano():
    form = PlanoForm()

    if form.validate_on_submit():
        try:
            PlanoService.criar_plano(current_user.id, form.data)
            flash("Plano criado com sucesso.", "success")
            return redirect(url_for('planos.listarPlanos'))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('planos/form.html', form=form, plano=None)


# Rota editar plano
@planos_blueprint.route('/editar/<int:plano_id>/', methods=['GET', 'POST'])
@login_required
def editarPlano(plano_id):
    plano = obter_do_instrutor_ou_404(Plano, plano_id)
    form = PlanoForm(obj=plano)

    if form.validate_on_submit():
        try:
            PlanoService.editar_plano(plano, form.data)
            flash("Plano atualizado com sucesso.", "success")
            return redirect(url_for('planos.listarPlanos'))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('planos/form.html', form=form, plano=plano)


# Rota excluir plano
@planos_blueprint.route('/excluir/<int:plano_id>', methods=['POST'])
@login_required
def excluirPlano(plano_id):
    plano = obter_do_instrutor_ou_404(Plano, plano_id)
    try:
        PlanoService.excluir_plano(plano)
        flash("Plano excluído com sucesso.", "success")
    except BusinessError as e:
        flash(str(e), "danger")

    return redirect(url_for('planos.listarPlanos'))
