from app import app, db
from flask import render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime

from app.models import Aluno
from app.form import AlunoForm, UserForm, LoginForm
import traceback 


# Rota inicial
@app.route('/')
@login_required
def homepage():
    aluno = Aluno.query.all()

    # verifica quantos alunos ativos e manda para notifição
    ativos = sum(1 for a in aluno if a.status == 'ativo')

    # calcular numero de aniversariantes 

    hoje = datetime.utcnow().date()

    aniversariantes = sum(
        1 for a in aluno
        if a.data_nascimento 
        and a.data_nascimento.day == hoje.day 
        and a.data_nascimento.month == hoje.month
    )
    return render_template('index.html', ativos=ativos, aniversariantes=aniversariantes)

# rota de login
@app.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = form.login()
        login_user(user, remember=True)
        return redirect(url_for('homepage'))
    
    return render_template('tela-login.html', form=form)


# Cadastro instrutor
@app.route('/cadastro-instrutor/', methods=['GET', 'POST'])
def cadastroInstrutor():
    form = UserForm()
    if form.validate_on_submit():
        user = form.save()
        if current_user.is_authenticated:
            return redirect(url_for('homepage'))
        login_user(user, remember=True)
        return redirect(url_for('homepage'))
    return render_template('cadastro-instrutor.html', form=form)

# Rota para sair deslogar
@app.route('/sair/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Rota painel administrativo
@app.route('/painel-adm/')
@login_required
def painelAdm():
    # 🔹 Buscar apenas alunos ativos
    alunos_ativos = Aluno.query.filter_by(status='ativo').all()
    #Testar sem alunos
    #alunos_ativos=[]

    # 🔹 Buscar planos ativos ou com data de fim futura (ajuste conforme seu model)
    #planos_ativos = Plano.query.filter((Plano.status == 'ativo') | (Plano.data_fim >= date.today())).all()

    # 🔹 Buscar fichas ativas (se existir status)
    #fichas_ativas = FichaTreino.query.filter_by(status='ativo').all()

    # 🔹 Contadores para as notificações
    total_alunos = len(alunos_ativos)
    #total_planos = len(planos_ativos)
    #total_fichas = len(fichas_ativas)

    return render_template(
        'painel-administrativo.html',
        alunos=alunos_ativos,
        #planos=planos_ativos,
        #fichas=fichas_ativas,
        total_alunos=total_alunos,
        #total_planos=total_planos,
        #total_fichas=total_fichas
    )

@app.route('/painel-adm/excluir', methods=['POST'])
@login_required
def excluir_alunos():
    # 1) obtenha lista de ids do form
    ids = request.form.getlist('selected')  # lista de strings

    if not ids:
        flash('Nenhum aluno selecionado.', 'warning')
        return redirect(url_for('painelAdm'))

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
        return redirect(url_for('painelAdm'))

    # 3) segurança extra: checar permissão do usuário
    # Exemplo: permitir exclusão só se current_user.is_admin == True
    if not getattr(current_user, 'is_admin', True):  # ajuste a sua lógica
        flash('Você não tem permissão para excluir alunos.', 'danger')
        return redirect(url_for('painelAdm'))

    try:
        # 4a) Carregar os objetos e excluir um a um (mais seguro para cascades)
        to_delete = Aluno.query.filter(Aluno.id.in_(valid_ids)).all()

        if not to_delete:
            flash('Nenhum aluno encontrado para os IDs informados.', 'warning')
            return redirect(url_for('painelAdm'))

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

    return redirect(url_for('painelAdm'))

# Eota para editar aluno
@app.route('/aluno/<int:id>/editar', methods=['GET', 'POST'])
def editar_aluno(id):
    aluno = Aluno.query.get_or_404(id)
    form = AlunoForm(obj=aluno)

    if form.validate_on_submit():
        form.populate_obj(aluno)  # Atualiza os campos automaticamente
        db.session.commit()
        flash('Aluno atualizado com sucesso!', 'success')
        return redirect(url_for('painelAdm'))

    return render_template('aluno_form.html', form=form, titulo=f'Editar Aluno: {aluno.nome}')


# Rota cadastro aluno
@app.route('/cadastro-aluno/', methods=['GET', 'POST'])
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
        return redirect(url_for('homepage'))
    
    return render_template('aluno_form.html', form=form, titulo='Cadastrar Aluno')