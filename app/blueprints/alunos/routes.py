from collections import Counter

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.blueprints.alunos.form import AlunoForm
from app.exceptions import BusinessError
from app.helpers.filters import data_br, moeda
from app.helpers.navegacao import url_segura
from app.helpers.paginacao import Paginacao
from app.models import Aluno, Plano
from app.services.aluno_service import AlunoService
from app.tenancy import do_instrutor, obter_do_instrutor_ou_404

alunos_blueprint = Blueprint('alunos', __name__, url_prefix='/alunos', template_folder='templates')

FILTROS_SITUACAO = {
    "todos": "Todos",
    "em_dia": "Em dia",
    "a_vencer": "A vencer",
    "vencido": "Vencidos",
    "inativo": "Inativos",
}


def _opcoes_planos(plano_atual_id=None):
    # planos ativos + o plano atual do aluno (mesmo que tenha sido desativado)
    planos = (
        do_instrutor(Plano)
        .filter(or_(Plano.ativo.is_(True), Plano.id == plano_atual_id))
        .order_by(Plano.nome)
        .all()
    )
    return [(0, 'Selecione um plano')] + [
        (p.id, f"{p.nome} · {moeda(p.valor)} / {p.duracao_dias} dias") for p in planos
    ]


# Rota para listar alunos
@alunos_blueprint.route('/')
@alunos_blueprint.route('/listar/')
@login_required
def listarAlunos():
    busca = request.args.get('q', '').strip()
    situacao = request.args.get('situacao', 'todos')
    if situacao not in FILTROS_SITUACAO:
        situacao = 'todos'

    query = do_instrutor(Aluno).options(joinedload(Aluno.plano)).order_by(Aluno.nome)
    if busca:
        termo = f"%{busca}%"
        query = query.filter(or_(
            Aluno.nome.ilike(termo),
            Aluno.email.ilike(termo),
            Aluno.cpf.ilike(termo),
            Aluno.telefone.ilike(termo),
        ))

    alunos = query.all()
    contagem = Counter(aluno.situacao for aluno in alunos)
    contagem['todos'] = len(alunos)

    if situacao != 'todos':
        alunos = [aluno for aluno in alunos if aluno.situacao == situacao]

    pagina = Paginacao(
        alunos,
        request.args.get('pagina', 1, type=int),
        current_app.config['ITENS_POR_PAGINA'],
    )
    return render_template(
        'alunos/lista.html',
        pagina=pagina,
        busca=busca,
        situacao=situacao,
        filtros=FILTROS_SITUACAO,
        contagem=contagem,
    )


# Rota cadastro aluno
@alunos_blueprint.route('/cadastro/', methods=['GET', 'POST'])
@login_required
def cadastroAluno():
    form = AlunoForm()
    form.plano_id.choices = _opcoes_planos()

    if form.validate_on_submit():
        try:
            aluno = AlunoService.criar_aluno(current_user.id, form.data)
            flash(f"{aluno.nome} cadastrado(a) com sucesso.", "success")
            if request.form.get('acao') == 'salvar_e_novo':
                return redirect(url_for('alunos.cadastroAluno'))
            return redirect(url_for('alunos.listarAlunos'))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('alunos/form.html', form=form, aluno=None, sem_planos=len(form.plano_id.choices) == 1)


# Rota para editar aluno
@alunos_blueprint.route('/editar/<int:aluno_id>', methods=['GET', 'POST'])
@login_required
def editarAluno(aluno_id):
    aluno = obter_do_instrutor_ou_404(Aluno, aluno_id)
    form = AlunoForm(obj=aluno)
    form.plano_id.choices = _opcoes_planos(aluno.plano_id)

    if form.validate_on_submit():
        try:
            AlunoService.editar_aluno(aluno, form.data)
            flash("Aluno atualizado com sucesso.", "success")
            return redirect(url_for('alunos.listarAlunos'))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template('alunos/form.html', form=form, aluno=aluno, sem_planos=len(form.plano_id.choices) == 1)


# Rota para renovar o plano do aluno
@alunos_blueprint.route('/<int:aluno_id>/renovar', methods=['POST'])
@login_required
def renovarPlano(aluno_id):
    aluno = obter_do_instrutor_ou_404(Aluno, aluno_id)
    try:
        AlunoService.renovar_plano(aluno)
        flash(f"Plano de {aluno.nome} renovado até {data_br(aluno.data_vencimento)}.", "success")
    except BusinessError as e:
        flash(str(e), "danger")

    destino = request.form.get('proximo')
    return redirect(destino if url_segura(destino) else url_for('alunos.listarAlunos'))


# Rota para excluir aluno
@alunos_blueprint.route('/excluir/<int:aluno_id>', methods=['POST'])
@login_required
def excluirAluno(aluno_id):
    aluno = obter_do_instrutor_ou_404(Aluno, aluno_id)
    try:
        AlunoService.excluir_aluno(aluno)
        flash("Aluno excluído com sucesso.", "success")
    except BusinessError as e:
        flash(str(e), "danger")

    return redirect(url_for('alunos.listarAlunos'))


# Rota para excluir vários alunos de uma vez
@alunos_blueprint.route('/excluir-varios/', methods=['POST'])
@login_required
def excluirAlunos():
    ids = [int(valor) for valor in request.form.getlist('selecionados') if valor.isdigit()]

    if not ids:
        flash("Nenhum aluno selecionado.", "danger")
        return redirect(url_for('alunos.listarAlunos'))

    try:
        total = AlunoService.excluir_varios(current_user.id, ids)
        flash(f"{total} aluno(s) excluído(s) com sucesso.", "success")
    except BusinessError as e:
        flash(str(e), "danger")

    return redirect(url_for('alunos.listarAlunos'))
