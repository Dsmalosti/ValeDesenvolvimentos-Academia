from app.extensions.database import db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.exercicios.form import ExercicioForm
from app.models import Exercicio
from app.services.exercicio_service import ExercicioService
from app.exceptions import BusinessError

exercicios_blueprint = Blueprint('exercicios', __name__, url_prefix='/exercicios', template_folder='templates')

# Rota criar exercicio
@exercicios_blueprint.route('/criar/', methods=['GET', 'POST'])
@login_required
def criarExercicio():
    form = ExercicioForm()
    if form.validate_on_submit():
        dados = {
            "nome":form.nome.data,
            "grupo_muscular":form.grupo_muscular.data,
            "descricao":form.descricao.data,
            "video_url":form.video_url.data,
            "ativo":form.ativo.data
        }
        try:
            ExercicioService.criar_exercicio(dados)
            flash('Exercicio criado com sucesso!', 'success')
            return redirect(url_for('exercicios.listarExercicios'))
        except BusinessError as e:
            flash(str(e), "danger")

        except Exception:
            flash("Erro inesperado ao criar exercicio", "danger")
    
    return render_template('exercicio_form.html', form=form, titulo='Criar exercicio')

# Rota listar
@exercicios_blueprint.route('/listar/')
@login_required
def listarExercicios():
    exercicios = Exercicio.query.all()
    
    return render_template('exercicio-lista.html', exercicios=exercicios)

# Rota editar
@exercicios_blueprint.route('/editar/<int:exercicio_id>', methods=['GET', 'POST'])
@login_required
def editarExercicio(exercicio_id):
    exercicio = Exercicio.query.get_or_404(exercicio_id)
    form = ExercicioForm(obj=exercicio)

    if form.validate_on_submit():
        dados = {
            "nome": form.nome.data,
            "grupo_muscular": form.grupo_muscular.data,
            "descricao": form.descricao.data,
            "video_url": form.video_url.data,
            "ativo": form.ativo.data,
        }

        try:
            ExercicioService.editar_exercicio(exercicio_id,dados)
            flash('Exercicio atualizado com sucesso!')
            return redirect(url_for('exercicios.listarPlanos'))
        except BusinessError as e:
            flash(str(e), "error")

    return render_template('exercicio_form.html', form=form, titulo=f'Editar Exercicio: {exercicio.nome}')

# Rota excluir
@exercicios_blueprint.route('/excluir/<int:exercicio_id>', methods=['POST'])
@login_required
def excluirExercicio(exercicio_id):
    try:
        ExercicioService.excluir_exercicio(exercicio_id)
        flash('Exercicio excluído com sucesso!', 'success')
    except BusinessError as e:
        flash(str(e), "error")
        
    return redirect(url_for('exercicios.listarExercicios'))
    




