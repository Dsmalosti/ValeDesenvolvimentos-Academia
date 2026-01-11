from app.extensions.database import db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.planos.form import PlanoForm
from app.models import Plano
from app.services.plano_service import PlanoService
from app.exceptions import BusinessError

planos_blueprint = Blueprint('planos', __name__, url_prefix='/planos', template_folder='templates')

#Rota criação planos
@planos_blueprint.route('/criar/', methods=['GET', 'POST'])
@login_required
def criarPlano():
    

    form = PlanoForm()
    print("FORM DATA:", form.data)
    print("FORM ERRORS:", form.errors)

    if form.validate_on_submit():
        dados = {
            "nome": form.nome.data,
            "valor": form.valor.data,
            "duracao_dias":form.duracao_dias.data,
            "descricao": form.descricao.data,
            "ativo": form.ativo.data
        }
        print("DADOS:", dados)
        try:
            PlanoService.criar_plano(dados)
            return redirect(url_for("planos.listarPlanos"))
        except BusinessError as e:
            flash(str(e), "danger")
        except Exception:
            flash("Erro inesperado ao cadastrar aluno", "danger")
        
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
        dados = {
            "nome": form.nome.data,
            "valor": form.valor.data,
            "duracao_dias": form.duracao_dias.data,
            "descricao": form.descricao.data,
            "ativo": form.ativo.data,
        }

        try:
            PlanoService.editar_plano(plano_id,dados)
            flash('Plano atualizado com sucesso!')
            return redirect(url_for('planos.listarPlanos'))
        except BusinessError as e:
            flash(str(e), "error")
    
    return render_template('plano_form.html', form=form, titulo="Editar Aluno")

# Rota excluir plano
@planos_blueprint.route('/excluir/<int:plano_id>', methods=['POST'])
@login_required
def excluirPlano(plano_id):
    try:
        PlanoService.excluir_plano(plano_id)
        flash('Plano excluído com sucesso!', 'success')
    except BusinessError as e:
        flash(str(e), "error")
        
    return redirect(url_for('planos.listarPlanos'))


    


