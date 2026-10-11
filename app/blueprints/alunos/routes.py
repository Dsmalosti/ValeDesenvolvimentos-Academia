from app.extensions.database import db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.alunos.form import AlunoForm
from app.services.aluno_service import AlunoService
from app.models import Aluno
from app.exceptions import BusinessError
from app.helpers.conta import DONO, DONO_E_RECEPCAO, da_conta, exigir_login_em, papel_requerido

alunos_blueprint = Blueprint('alunos', __name__, url_prefix='/alunos', template_folder='templates')
exigir_login_em(alunos_blueprint)  # [back-03-isolamento] toda rota daqui exige login, mesmo as futuras


# Rota cadastro aluno
@alunos_blueprint.route('/cadastro/', methods=['GET', 'POST'])
@login_required
@papel_requerido(*DONO_E_RECEPCAO)  # [back-06-contas-e-papeis] instrutor não cadastra aluno
def cadastroAluno():

    form = AlunoForm()

    if form.validate_on_submit():
        try:
            AlunoService.criar_aluno(form.data, current_user.id)

            flash("Aluno cadastrado com sucesso!", "success")
            return redirect(url_for("main.homepage"))

        except BusinessError as e:
            flash(str(e), "danger")

        except Exception:
            flash("Erro inesperado ao cadastrar aluno", "danger")

    return render_template("aluno_form.html", form=form)


#Rota para listar aluno
@alunos_blueprint.route('/listar/')
@login_required
def listarAlunos():
    alunos = AlunoService.listar_alunos()

    return render_template('aluno-lista.html', alunos=alunos)

# Rota para editar aluno
@alunos_blueprint.route('/editar/<int:aluno_id>', methods=['GET', 'POST'])
@login_required
@papel_requerido(*DONO_E_RECEPCAO)  # [back-06-contas-e-papeis] instrutor não edita o cadastro
def editarAluno(aluno_id):
    # filtra por instrutor_id também aqui, pra ninguém abrir/editar
    # aluno de outra academia só trocando o id na URL
    aluno = da_conta(Aluno).filter_by(id=aluno_id).first_or_404()  # [back-06-contas-e-papeis] antes: instrutor_id=current_user.id
    form = AlunoForm(obj=aluno)  # 👈 pré-preenche o form

    if form.validate_on_submit():
        dados = {
            "nome": form.nome.data,
            "email": form.email.data,
            "telefone": form.telefone.data,
            "cpf": form.cpf.data,
            "ativo": form.ativo.data,
            "plano_id": form.plano_id.data,
        }

        try:
            AlunoService.editar_aluno(aluno_id, dados)
            flash("Aluno atualizado com sucesso", "success")
            return redirect(url_for("alunos.listarAlunos"))

        except BusinessError as e:
            flash(str(e), "error")

    return render_template(
        "aluno_form.html",
        form=form,
        titulo="Editar Aluno"
    )

# Rota para excluir aluno
@alunos_blueprint.route('/excluir/<int:aluno_id>', methods=['POST'])
@login_required
@papel_requerido(*DONO)  # [back-06-contas-e-papeis] apagar os dados de um aluno de vez é só com o dono (LGPD)
def excluirAluno(aluno_id):
    try:
        AlunoService.excluir_aluno(aluno_id)
        flash("Aluno excluído com sucesso", "success")
    except BusinessError as e:
        flash(str(e), "error")

    return redirect(url_for("alunos.listarAlunos"))

# Rota para ativar/desativar aluno
@alunos_blueprint.route('/status/<int:aluno_id>', methods=['POST'])
@login_required
@papel_requerido(*DONO_E_RECEPCAO)  # [back-06-contas-e-papeis] instrutor não ativa nem inativa aluno
def alternarStatusAluno(aluno_id):
    try:
        aluno = AlunoService.alternar_status(aluno_id)
        status = "ativado" if aluno.ativo else "desativado"
        flash(f"Aluno {status} com sucesso", "success")
    except BusinessError as e:
        flash(str(e), "error")

    return redirect(url_for("alunos.listarAlunos"))


# ---------------------------------------------------------------------------
# [back-04-painel] PONTES TEMPORÁRIAS para o front novo.
# O menu e o painel novos chamam url_for('alunos.lista'), 'alunos.novo' etc. (nomes do
# contrato do front). As telas novas de alunos ainda não foram ligadas, então por enquanto
# esses endpoints só levam para a tela antiga equivalente. Cada ponte vira a tela de
# verdade na branch de alunos; nenhuma delas mexe em dado.
# ---------------------------------------------------------------------------
@alunos_blueprint.route('')
def lista():
    return redirect(url_for('alunos.listarAlunos'))


@alunos_blueprint.route('/novo')
def novo():
    return redirect(url_for('alunos.cadastroAluno'))


@alunos_blueprint.route('/buscar')
def buscar():
    return redirect(url_for('alunos.listarAlunos'))


@alunos_blueprint.route('/<int:id>')
def detalhe(id):
    # a tela antiga não tem "perfil do aluno"; a mais próxima é a de editar (que já confere a conta)
    return redirect(url_for('alunos.editarAluno', aluno_id=id))


@alunos_blueprint.route('/<int:id>/renovar')
def renovar(id):
    # renovar matrícula, na tela antiga, é registrar um pagamento (que já confere a conta)
    return redirect(url_for('pagamentos.registrarPagamento', aluno_id=id))


@alunos_blueprint.route('/acesso/busca')
def acesso_busca():
    # busca do popup "Bloquear ou liberar acesso": devolve só um pedaço de HTML para o popup
    return '<p class="faint" style="margin:0">A busca para bloquear acesso ainda não está disponível.</p>'