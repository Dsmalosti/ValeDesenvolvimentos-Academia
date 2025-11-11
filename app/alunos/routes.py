from app import  db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.alunos.form import AlunoForm
from app.models import Aluno

alunos_blueprint = Blueprint('alunos', __name__, url_prefix='/alunos', template_folder='templates')


# Rota cadastro aluno
@alunos_blueprint.route('/cadastro/', methods=['GET', 'POST'])
@login_required
def cadastroAluno():
    form = AlunoForm()
    if form.validate_on_submit():
        aluno = Aluno(
            nome=form.nome.data,
            email=form.email.data,
            telefone=form.telefone.data,
            data_nascimento=form.data_nascimento.data,
            cpf=form.cpf.data
        )
        db.session.add(aluno)
        db.session.commit()
        flash('Aluno cadastrado com sucesso!', 'success')
        return redirect(url_for('main.homepage'))
    
    return render_template('aluno_form.html', form=form, titulo='Cadastrar Aluno')

# Rota para editar aluno
@alunos_blueprint.route('/editar/<int:aluno_id>', methods=['GET', 'POST'])
def editarAluno(aluno_id):
    aluno = Aluno.query.get_or_404(aluno_id)
    form = AlunoForm(obj=aluno)

    if form.validate_on_submit():
        form.populate_obj(aluno)  # Atualiza os campos automaticamente
        db.session.commit()
        flash('Aluno atualizado com sucesso!', 'success')
        return redirect(url_for('instrutores.painelAdm'))

    return render_template('aluno_form.html', form=form, titulo=f'Editar Aluno: {aluno.nome}')

# Rota para excluir aluno
@alunos_blueprint.route('/excluir', methods=['POST'])
@login_required
def excluirAlunos():
    # 1) obtenha lista de ids do form
    ids = request.form.getlist('selected')  # lista de strings

    if not ids:
        flash('Nenhum aluno selecionado.', 'warning')
        return redirect(url_for('instrutores.painelAdm'))

    # 2) converter p/ inteiros e validar
    valid_ids = []
    for s in ids:
        try:
            valid_ids.append(int(s))
        except ValueError:
            # id inválido — ignorar ou abortar
            app.logger.warning(f'ID inválido no form de exclusão: {s}')
            continue

    if not valid_ids:
        flash('IDs inválidos enviados.', 'danger')
        return redirect(url_for('instrutores.painelAdm'))

    # 3) segurança extra: checar permissão do usuário
    # Exemplo: permitir exclusão só se current_user.is_admin == True
    if not getattr(current_user, 'is_admin', True):  # ajuste a sua lógica
        flash('Você não tem permissão para excluir alunos.', 'danger')
        return redirect(url_for('instrutores.painelAdm'))

    try:
        # 4a) Carregar os objetos e excluir um a um (mais seguro para cascades)
        to_delete = Aluno.query.filter(Aluno.id.in_(valid_ids)).all()

        if not to_delete:
            flash('Nenhum aluno encontrado para os IDs informados.', 'warning')
            return redirect(url_for('instrutores.painelAdm'))

        # Opcional: filtrar só alunos que pertencem ao contexto do usuário
        # to_delete = [a for a in to_delete if a.empresa_id == current_user.empresa_id]

        for aluno in to_delete:
            db.session.delete(aluno)

        db.session.commit()
        flash(f'{len(to_delete)} aluno(s) excluído(s) com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error('Erro ao excluir alunos: %s', e)
        traceback.print_exc()
        flash('Erro ao excluir os alunos. Veja logs para detalhes.', 'danger')

    return redirect(url_for('instrutores.painelAdm'))