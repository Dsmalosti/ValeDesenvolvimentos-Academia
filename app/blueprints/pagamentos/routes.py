from flask import Blueprint, render_template, url_for, redirect, flash
from flask_login import current_user, login_required

from app.blueprints.pagamentos.form import PagamentoForm
from app.services.pagamento_service import PagamentoService
from app.models import Aluno
from app.exceptions import BusinessError
from app.helpers.conta import DONO_E_RECEPCAO, da_conta, exigir_papel_em

pagamentos_blueprint = Blueprint('pagamentos', __name__, url_prefix='/pagamentos', template_folder='templates')
# [back-06-contas-e-papeis] antes: exigir_login_em(...), que só pedia login. O financeiro inteiro agora também exige
# o papel: instrutor recebe 403 em qualquer rota daqui, inclusive nas que forem criadas depois.
exigir_papel_em(pagamentos_blueprint, *DONO_E_RECEPCAO)


# Rota pra registrar um pagamento novo de um aluno específico
@pagamentos_blueprint.route('/registrar/<int:aluno_id>', methods=['GET', 'POST'])
@login_required
def registrarPagamento(aluno_id):
    aluno = da_conta(Aluno).filter_by(id=aluno_id).first_or_404()  # [back-06-contas-e-papeis] antes: instrutor_id=current_user.id
    form = PagamentoForm()

    if form.validate_on_submit():
        dados = {
            "valor": form.valor.data,
            "data_pagamento": form.data_pagamento.data,
            "forma_pagamento": form.forma_pagamento.data,
            "observacao": form.observacao.data,
        }

        try:
            PagamentoService.registrar_pagamento(aluno_id, dados, current_user.id)
            flash("Pagamento registrado com sucesso!", "success")
            return redirect(url_for("pagamentos.listarPagamentosAluno", aluno_id=aluno_id))
        except BusinessError as e:
            flash(str(e), "danger")

    return render_template("pagamento_form.html", form=form, aluno=aluno)


# Rota pra listar o histórico de pagamentos de um aluno
@pagamentos_blueprint.route('/listar/<int:aluno_id>')
@login_required
def listarPagamentosAluno(aluno_id):
    aluno = da_conta(Aluno).filter_by(id=aluno_id).first_or_404()  # [back-06-contas-e-papeis] antes: instrutor_id=current_user.id
    pagamentos = PagamentoService.listar_pagamentos_aluno(aluno_id)

    return render_template("pagamento-lista.html", pagamentos=pagamentos, aluno=aluno)


# Rota pra ver a situação (em dia / vencido) de todos os alunos
@pagamentos_blueprint.route('/situacao/')
@login_required
def situacaoAlunos():
    status_alunos = PagamentoService.listar_status_alunos()

    return render_template("situacao-alunos.html", status_alunos=status_alunos)