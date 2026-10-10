from app.extensions.database import db
from flask import Blueprint,render_template, url_for, request, redirect, flash, make_response
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.alunos.form import AlunoForm
from app.services.aluno_service import AlunoService
from app.models import Aluno, PAPEL_INSTRUTOR
from app.services import aluno_tela_service as telas  # [back-07-alunos] regras das telas novas
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
# [back-07-alunos] TELAS DE ALUNOS DO FRONT NOVO (templates/alunos/).
# Os nomes das funções e os endereços são os do contrato do front: os templates chamam
# url_for('alunos.lista'), 'alunos.novo', 'alunos.detalhe', 'alunos.editar' etc.
# Antes (back-04), estes endpoints eram só "pontes" que redirecionavam para as telas antigas.
#
# As rotas ANTIGAS, lá em cima (/alunos/listar/, /cadastro/, /editar/<id>, /excluir/<id> e
# /status/<id>), continuam funcionando: as telas antigas de planos, fichas e pagamentos ainda
# têm links para elas. Saem quando o layout antigo sair.
#
# As regras (validação, filtros, contagens) ficam em services/aluno_tela_service.py; aqui a
# rota só confere a conta e o papel, chama o serviço e escolhe a resposta.
# ---------------------------------------------------------------------------
def _aluno_da_conta(id):
    """O aluno, se for da conta de quem está logado; senão 404 (como se não existisse)."""
    return da_conta(Aluno).filter_by(id=id).first_or_404()


@alunos_blueprint.route('')
def lista():
    return render_template('alunos/lista.html', **telas.contexto_da_lista(request.args))


@alunos_blueprint.route('/exportar')
@papel_requerido(*DONO_E_RECEPCAO)   # a planilha leva CPF e telefone: instrutor não exporta
def exportar():
    resposta = make_response(telas.exportar_csv(request.args))
    resposta.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resposta.headers['Content-Disposition'] = 'attachment; filename=alunos.csv'
    return resposta


@alunos_blueprint.route('/novo', methods=['GET', 'POST'])
@papel_requerido(*DONO_E_RECEPCAO)
def novo():
    if request.method == 'POST':
        valores, erros = telas.validar(request.form)
        if erros:
            flash(telas.aviso_dos_erros(erros), 'error')
            return render_template('alunos/novo.html', aluno=telas.do_formulario(request.form), erros=erros,
                                   planos=telas.planos_do_formulario(), modo='novo')
        aluno = telas.criar(valores)
        # No desenho do front, daqui a recepção vai direto receber a primeira mensalidade. Esse passo
        # entra com a branch de cobrança; por enquanto o cadastro termina no perfil do aluno.
        flash('Aluno cadastrado.', 'success')
        return redirect(url_for('alunos.detalhe', id=aluno.id))
    return render_template('alunos/novo.html', aluno=telas.aluno_em_branco(), erros={},
                           planos=telas.planos_do_formulario(), modo='novo')


@alunos_blueprint.route('/buscar')
def buscar():
    q = (request.args.get('q') or '').strip()
    acao = request.args.get('acao') or 'detalhe'
    resultados = telas.buscar(q)
    if request.args.get('partial'):
        # busca ao vivo: o app.js pede só o pedaço de HTML com os resultados
        return render_template('alunos/_resultados.html', q=q, resultados=resultados, acao=acao)
    return render_template('alunos/buscar.html', q=q, resultados=resultados, acao=acao, recentes=telas.recentes())


@alunos_blueprint.route('/<int:id>')
def detalhe(id):
    contexto = telas.contexto_do_perfil(_aluno_da_conta(id))
    if current_user.papel == PAPEL_INSTRUTOR:
        # o instrutor vê o aluno, mas não o dinheiro: sem histórico de pagamentos no perfil
        contexto.update(pagamentos=[], total_ano=0)
    return render_template('alunos/detalhe.html', **contexto)


@alunos_blueprint.route('/<int:id>/editar', methods=['GET', 'POST'])
@papel_requerido(*DONO_E_RECEPCAO)
def editar(id):
    aluno = _aluno_da_conta(id)
    if request.method == 'POST':
        valores, erros = telas.validar(request.form, aluno)
        if erros:
            flash(telas.aviso_dos_erros(erros), 'error')
            return render_template('alunos/editar.html', erros=erros, planos=telas.planos_do_formulario(), modo='editar',
                                   aluno=telas.do_formulario(request.form, aluno.id, aluno.nome))
        telas.atualizar(aluno, valores)
        flash('Alterações salvas.', 'success')
        return redirect(url_for('alunos.detalhe', id=aluno.id))
    return render_template('alunos/editar.html', aluno=telas.aluno_para_o_formulario(aluno), erros={},
                           planos=telas.planos_do_formulario(), modo='editar')


@alunos_blueprint.route('/<int:id>/inativar', methods=['POST'])
@papel_requerido(*DONO_E_RECEPCAO)
def inativar(id):
    # Inativar NÃO apaga nada: só marca o aluno como inativo, e o histórico fica. Para reativar,
    # por enquanto, é pela tela antiga (botão de status em /alunos/listar/); o front novo ainda
    # não tem esse botão.
    aluno = _aluno_da_conta(id)
    aluno.ativo = False
    db.session.commit()
    flash(f'{aluno.nome} foi inativado. O histórico foi mantido.', 'success')
    return redirect(url_for('alunos.lista'))


@alunos_blueprint.route('/<int:id>/excluir', methods=['POST'])
@papel_requerido(*DONO)   # apagar os dados de um aluno de vez é só com o dono (LGPD)
def excluir(id):
    aluno = _aluno_da_conta(id)
    try:
        AlunoService.excluir_aluno(aluno.id)
    except BusinessError:
        # o banco recusa apagar aluno que tem ficha ou pagamento ligado a ele
        flash('Não foi possível excluir: este aluno tem fichas ou pagamentos registrados. Desative em vez de excluir.', 'error')
        return redirect(url_for('alunos.detalhe', id=id))
    flash('Cadastro excluído.', 'success')
    return redirect(url_for('alunos.lista'))


@alunos_blueprint.route('/<int:id>/acesso', methods=['POST'])
@papel_requerido(*DONO_E_RECEPCAO)
def acesso(id):
    # Bloquear e liberar o acesso na recepção faz parte do módulo de frequência, que ainda não existe.
    _aluno_da_conta(id)
    flash('Bloquear e liberar acesso ainda não está disponível.', 'info')
    return redirect(url_for('alunos.detalhe', id=id))


# ---------------------------------------------------------------------------
# PONTES TEMPORÁRIAS para o front novo (criadas na back-04-painel).
# O que é uma ponte: o menu e as telas novas chamam endpoints com os nomes do contrato do front
# (url_for('alunos.pagamentos'), 'exercicios.lista' etc.). Enquanto a tela nova daquele assunto não
# foi ligada, o endpoint existe só para levar à tela antiga equivalente. Nenhuma ponte mexe em
# dado, e cada uma vira a tela de verdade na branch do seu assunto.
# [back-07-alunos] lista, novo, detalhe e buscar deixaram de ser pontes (são as rotas acima).
# As três abaixo continuam, até as branches de cobrança e de frequência.
# ---------------------------------------------------------------------------
@alunos_blueprint.route('/<int:id>/pagamentos')
def pagamentos(id):
    # extrato do aluno: por enquanto é a tela antiga de pagamentos (que já confere a conta e o papel)
    return redirect(url_for('pagamentos.listarPagamentosAluno', aluno_id=id))


@alunos_blueprint.route('/<int:id>/renovar')
def renovar(id):
    # renovar matrícula, na tela antiga, é registrar um pagamento (que já confere a conta e o papel)
    return redirect(url_for('pagamentos.registrarPagamento', aluno_id=id))


@alunos_blueprint.route('/acesso/busca')
def acesso_busca():
    # busca do popup "Bloquear ou liberar acesso": devolve só um pedaço de HTML para o popup
    return '<p class="faint" style="margin:0">A busca para bloquear acesso ainda não está disponível.</p>'
