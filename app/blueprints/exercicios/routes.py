from app.extensions.database import db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.exercicios.form import ExercicioForm
from app.models import Exercicio

exercicios_blueprint = Blueprint('exercicios', __name__, url_prefix='/exercicios', template_folder='templates')

# Rota criar exercicio
@exercicios_blueprint.route('/criar/', methods=['GET', 'POST'])
@login_required
def criarExercicio():
    form = ExercicioForm()
    if form.validate_on_submit():
        exercicio = Exercicio(
            nome = form.nome.data,
            grupo_muscular = form.grupo_muscular.data,
            descricao = form.descricao.data,
            video_url = form.video_url.data,
            ativo = form.ativo.data
        )

        db.session.add(exercicio)
        db.session.commit()
        flash('Exercicio criado com sucesso!', 'success')
        return redirect(url_for('exercicios.listarExercicios'))
    
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
        form.populate_obj(exercicio)
        db.session.commit()
        flash('Exercicio atualizado com sucesso!', 'success')
        return redirect(url_for('exercicios.listarExercicios'))

    return render_template('exercicio_form.html', form=form, titulo=f'Editar Exercicio: {exercicio.nome}')

# Rota excluir
@exercicios_blueprint.route('/excluir/<int:exercicio_id>', methods=['POST'])
@login_required
def excluirExercicio(exercicio_id):
    exercicio = Exercicio.query.get_or_404(exercicio_id)
    db.session.delete(exercicio)
    db.session.commit()

    return redirect(url_for('exercicios.listarExercicios'))
    




