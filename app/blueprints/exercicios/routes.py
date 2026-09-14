from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.blueprints.exercicios.form import ExercicioForm
from app.exceptions import BusinessError
from app.models import Exercicio, GRUPOS_MUSCULARES
from app.services.exercicio_service import ExercicioService
from app.tenancy import do_instrutor, obter_do_instrutor_ou_404

exercicios_blueprint = Blueprint('exercicios', __name__, url_prefix='/exercicios', template_folder='templates')


# Rota listar
@exercicios_blueprint.route('/')
@exercicios_blueprint.route('/listar/')
@login_required
def listarExercicios():
    busca = request.args.get('q', '').strip()
    grupo = request.args.get('grupo', '')
    if grupo not in dict(GRUPOS_MUSCULARES):
        grupo = ''

    query = do_instrutor(Exercicio)
    if busca:
        query = query.filter(Exercicio.nome.ilike(f"%{busca}%"))
    if grupo:
        query = query.filter(Exercicio.grupo_muscular == grupo)

    exercicios = query.order_by(Exercicio.ativo.desc(), Exercicio.nome).all()
    total_biblioteca = do_instrutor(Exercicio).count()

    return render_template(
        'exercicios/lista.html',
        exercicios=exercicios,
        busca=busca,
        grupo=grupo,
        total_biblioteca=total_biblioteca,
    )


# Rota criar exercicio
@exercicios_blueprint.route('/criar/', methods=['GET', 'POST'])
@login_required
def criarExercicio():
    form = ExercicioForm()

    if form.validate_on_submit():
        try:
            ExercicioService.criar_exercicio(current_user.id, form.data)
            flash('Exercício criado com sucesso.', 'success')
            if request.form.get('acao') == 'salvar_e_novo':
                return redirect(url_for('exercicios.criarExercicio'))
            return redirect(url_for('exercicios.listarExercicios'))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('exercicios/form.html', form=form, exercicio=None)


# Rota importar biblioteca padrão
@exercicios_blueprint.route('/importar-padrao/', methods=['POST'])
@login_required
def importarPadrao():
    try:
        total = ExercicioService.importar_padrao(current_user.id)
        if total:
            flash(f'{total} exercícios adicionados à sua biblioteca.', 'success')
        else:
            flash('Sua biblioteca já tem todos os exercícios padrão.', 'info')
    except BusinessError as e:
        flash(str(e), "danger")

    return redirect(url_for('exercicios.listarExercicios'))


# Rota editar
@exercicios_blueprint.route('/editar/<int:exercicio_id>', methods=['GET', 'POST'])
@login_required
def editarExercicio(exercicio_id):
    exercicio = obter_do_instrutor_ou_404(Exercicio, exercicio_id)
    form = ExercicioForm(obj=exercicio)

    if form.validate_on_submit():
        try:
            ExercicioService.editar_exercicio(exercicio, form.data)
            flash('Exercício atualizado com sucesso.', 'success')
            return redirect(url_for('exercicios.listarExercicios'))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('exercicios/form.html', form=form, exercicio=exercicio)


# Rota excluir
@exercicios_blueprint.route('/excluir/<int:exercicio_id>', methods=['POST'])
@login_required
def excluirExercicio(exercicio_id):
    exercicio = obter_do_instrutor_ou_404(Exercicio, exercicio_id)
    try:
        ExercicioService.excluir_exercicio(exercicio)
        flash('Exercício excluído com sucesso.', 'success')
    except BusinessError as e:
        flash(str(e), "danger")

    return redirect(url_for('exercicios.listarExercicios'))
