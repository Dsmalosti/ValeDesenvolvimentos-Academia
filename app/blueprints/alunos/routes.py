from app.extensions.database import db
from flask import Blueprint,render_template, url_for, request, redirect, flash, make_response
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.alunos.form import AlunoForm
from app.services.aluno_service import AlunoService
from app.models import Aluno, PAPEL_INSTRUTOR
from app.services import aluno_tela_service as telas  # [back-07-alunos] regras das telas novas
from app.services import cobranca_service as cobrancas  # [back-09-cobranca] cobrança, renovação e extrato
from app.services import frequencia_service as frequencia  # [back-10-frequencia] bloquear acesso e busca do popup
from app.services import pacote_service  # [back-17-personal] renovar pacote na conta de personal
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
        # [back-09-cobranca] antes: o cadastro terminava no perfil do aluno. Agora segue o desenho do front:
        # nasce a cobrança da matrícula e a recepção vai direto receber (ou toca em "Cobrar depois").
        cobranca = cobrancas.gerar(aluno, aluno.plano)
        flash('Aluno cadastrado. Falta receber a primeira mensalidade.', 'success')
        return redirect(url_for('cobrancas.receber', id=cobranca.id, forma=aluno.forma_pagamento))
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
    # [back-10-frequencia] antes: só avisava que a função ainda não existia. Agora troca alunos.acesso_liberado,
    # que o check-in confere antes de registrar a entrada.
    aluno = frequencia.alternar_acesso(_aluno_da_conta(id))
    flash(f"Acesso de {aluno.nome} {'liberado' if aluno.acesso_liberado else 'bloqueado'} na recepção.", 'success')
    # volta para o perfil, e não para o endereço que o navegador informa: redirecionar para onde o
    # navegador manda abriria brecha para levar o usuário a outro site
    return redirect(url_for('alunos.detalhe', id=id))


# ---------------------------------------------------------------------------
# PONTES TEMPORÁRIAS para o front novo (criadas na back-04-painel).
# O que é uma ponte: o menu e as telas novas chamam endpoints com os nomes do contrato do front
# (url_for('alunos.pagamentos'), 'exercicios.lista' etc.). Enquanto a tela nova daquele assunto não
# foi ligada, o endpoint existe só para levar à tela antiga equivalente. Nenhuma ponte mexe em
# dado, e cada uma vira a tela de verdade na branch do seu assunto.
# [back-07-alunos] lista, novo, detalhe e buscar deixaram de ser pontes (são as rotas acima).
# [back-09-cobranca] pagamentos e renovar viraram telas de verdade; [back-10-frequencia] a busca de acesso também.
# ---------------------------------------------------------------------------
@alunos_blueprint.route('/<int:id>/pagamentos')
@papel_requerido(*DONO_E_RECEPCAO)   # extrato é dinheiro: instrutor não vê
def pagamentos(id):
    # [back-09-cobranca] antes: ponte para a tela antiga /pagamentos/listar/<id>
    aluno = _aluno_da_conta(id)
    lista = cobrancas.pagamentos_do(aluno)
    if request.args.get('formato') == 'csv':
        resposta = make_response(cobrancas.extrato_csv(lista))
        resposta.headers['Content-Type'] = 'text/csv; charset=utf-8'
        resposta.headers['Content-Disposition'] = f'attachment; filename=extrato-{aluno.id}.csv'
        return resposta
    return render_template('alunos/pagamentos.html', aluno=telas.contexto_do_perfil(aluno)['aluno'],
                           pagamentos=lista, total_ano=cobrancas.total_do_ano(lista))


@alunos_blueprint.route('/<int:id>/renovar', methods=['GET', 'POST'])
@papel_requerido(*DONO_E_RECEPCAO)
def renovar(id):
    # [back-09-cobranca] antes: ponte para a tela antiga /pagamentos/registrar/<id>
    aluno = _aluno_da_conta(id)
    if request.method == 'POST':
        try:
            cobranca = cobrancas.renovar(aluno, request.form.get('plano_id'))
        except cobrancas.CobrancaInvalida as erro:
            flash(str(erro), 'error')
            return redirect(url_for('alunos.renovar', id=id))
        if request.form.get('acao') == 'sem_cobrar':
            if pacote_service.e_personal():
                # [back-17-personal] renovar pacote: o aviso fala do saldo, e não de matrícula
                flash(f"Pacote renovado: {pacote_service.saldo_txt(pacote_service.pacote_do(aluno)['saldo'])}. A cobrança fica em aberto.", 'success')
            else:
                flash('Matrícula renovada. A cobrança fica em aberto.', 'success')
            return redirect(url_for('alunos.detalhe', id=id))
        return redirect(url_for('cobrancas.receber', id=cobranca.id, forma=aluno.forma_pagamento))
    if pacote_service.e_personal():
        # [back-17-personal] conta de personal: renovar é comprar um pacote novo; a tela mostra o novo saldo (o que sobrou soma)
        pacotes = pacote_service.pacotes_para_renovar(aluno)
        if not pacotes:
            flash('Cadastre um pacote ativo antes de renovar.', 'warning')
            return redirect(url_for('planos.lista'))
        return render_template('personal/renovar.html', aluno=telas.contexto_do_perfil(aluno)['aluno'], pacotes=pacotes, plano_atual_id=aluno.plano_id)
    planos = cobrancas.planos_para_renovar(aluno)
    if not planos:
        flash('Cadastre um plano ativo antes de renovar.', 'warning')
        return redirect(url_for('planos.lista'))
    return render_template('alunos/renovar.html', aluno=telas.contexto_do_perfil(aluno)['aluno'],
                           planos=planos, plano_atual_id=aluno.plano_id)


@alunos_blueprint.route('/acesso/busca')
@papel_requerido(*DONO_E_RECEPCAO)
def acesso_busca():
    # busca do popup "Bloquear ou liberar acesso": devolve só um pedaço de HTML para o popup
    # [back-10-frequencia] antes: devolvia um aviso fixo de "ainda não disponível"
    q = (request.args.get('q') or '').strip()
    resultados = frequencia.buscar(q) if len(q) >= 2 else []
    return render_template('alunos/_linhas_acesso.html', resultados=resultados, q=q)
