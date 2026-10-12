from flask import Blueprint, render_template, url_for, redirect, flash
from flask_login import current_user, login_required

from app.models import Aluno
from app.helpers.conta import DONO_E_RECEPCAO, da_conta, exigir_papel_em

pagamentos_blueprint = Blueprint('pagamentos', __name__, url_prefix='/pagamentos', template_folder='templates')
# [back-06-contas-e-papeis] antes: exigir_login_em(...), que só pedia login. O financeiro inteiro agora também exige
# o papel: instrutor recebe 403 em qualquer rota daqui, inclusive nas que forem criadas depois.
exigir_papel_em(pagamentos_blueprint, *DONO_E_RECEPCAO)


# ---------------------------------------------------------------------------
# [back-09-cobranca] As três telas antigas de pagamento viraram REDIRECIONAMENTOS para as telas
# novas (decisão do Diogo, pergunta 4 da proposta de esquema).
# Antes: registrarPagamento mostrava o formulário pagamento_form.html e gravava em `pagamentos`;
# listarPagamentosAluno mostrava pagamento-lista.html; situacaoAlunos mostrava situacao-alunos.html.
# Elas usavam colunas que saíram da tabela (aluno_id, valor, data_vencimento, forma_pagamento).
# Os arquivos antigos (form.py, os três templates e services/pagamento_service.py) continuam no
# repositório, sem uso, até o layout antigo sair.
# ---------------------------------------------------------------------------
@pagamentos_blueprint.route('/registrar/<int:aluno_id>', methods=['GET', 'POST'])
@login_required
def registrarPagamento(aluno_id):
    da_conta(Aluno).filter_by(id=aluno_id).first_or_404()   # aluno de outra academia continua dando 404
    return redirect(url_for('alunos.renovar', id=aluno_id))


@pagamentos_blueprint.route('/listar/<int:aluno_id>')
@login_required
def listarPagamentosAluno(aluno_id):
    da_conta(Aluno).filter_by(id=aluno_id).first_or_404()
    return redirect(url_for('alunos.pagamentos', id=aluno_id))


@pagamentos_blueprint.route('/situacao/')
@login_required
def situacaoAlunos():
    return redirect(url_for('alunos.lista', status='pendente'))
