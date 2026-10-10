from app.extensions.database import db
from flask import Blueprint,render_template, url_for, request, redirect, flash
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.planos.form import PlanoForm
from app.models import Plano
from app.services.plano_service import PlanoService
from app.services import plano_tela_service as telas  # [back-08-planos] regras das telas novas
from app.exceptions import BusinessError
from app.helpers.conta import DONO_E_RECEPCAO, da_conta, exigir_login_em, papel_requerido

planos_blueprint = Blueprint('planos', __name__, url_prefix='/planos', template_folder='templates')
exigir_login_em(planos_blueprint)  # [back-03-isolamento] toda rota daqui exige login, mesmo as futuras

#Rota criação planos
@planos_blueprint.route('/criar/', methods=['GET', 'POST'])
@login_required
@papel_requerido(*DONO_E_RECEPCAO)  # [back-06-contas-e-papeis] plano e preço: instrutor só consulta
def criarPlano():


    form = PlanoForm()
    # [back-02-limpeza] antes: dois print() com form.data e form.errors, que jogavam os dados
    # do formulário no log do servidor.

    if form.validate_on_submit():
        dados = {
            "nome": form.nome.data,
            "valor": form.valor.data,
            "duracao_dias":form.duracao_dias.data,
            "descricao": form.descricao.data,
            "ativo": form.ativo.data
        }
        # [back-02-limpeza] antes: print("DADOS:", dados)
        try:
            PlanoService.criar_plano(dados, current_user.id)
            return redirect(url_for("planos.listarPlanos"))
        except BusinessError as e:
            flash(str(e), "danger")
        except Exception:
            flash("Erro inesperado ao cadastrar aluno", "danger")

    return render_template('plano_form.html', form=form)

# Rota listar plano
@planos_blueprint.route('/listar/')
@login_required
def listarPlanos():
    planos = PlanoService.listar_planos()

    return render_template('plano-lista.html', planos=planos)

# Rota editar plano
@planos_blueprint.route('/editar/<int:plano_id>/', methods=['GET', 'POST'])
@login_required
@papel_requerido(*DONO_E_RECEPCAO)  # [back-06-contas-e-papeis] plano e preço: instrutor só consulta
def editarPlano(plano_id):
    # filtra por instrutor_id também aqui, pelo mesmo motivo do aluno
    plano = da_conta(Plano).filter_by(id=plano_id).first_or_404()  # [back-06-contas-e-papeis] antes: instrutor_id=current_user.id
    form = PlanoForm(obj=plano)

    if form.validate_on_submit():
        dados = {
            "nome": form.nome.data,
            "valor": form.valor.data,
            "duracao_dias": form.duracao_dias.data,
            "descricao": form.descricao.data,
            "ativo": form.ativo.data,
        }

        try:
            PlanoService.editar_plano(plano_id, dados)
            flash('Plano atualizado com sucesso!')
            return redirect(url_for('planos.listarPlanos'))
        except BusinessError as e:
            flash(str(e), "error")

    return render_template('plano_form.html', form=form, titulo="Editar Aluno")

# Rota excluir plano
@planos_blueprint.route('/excluir/<int:plano_id>', methods=['POST'])
@login_required
@papel_requerido(*DONO_E_RECEPCAO)  # [back-06-contas-e-papeis] plano e preço: instrutor só consulta
def excluirPlano(plano_id):
    try:
        PlanoService.excluir_plano(plano_id)
        flash('Plano excluído com sucesso!', 'success')
    except BusinessError as e:
        flash(str(e), "error")

    return redirect(url_for('planos.listarPlanos'))


# ---------------------------------------------------------------------------
# [back-08-planos] TELAS DE PLANOS DO FRONT NOVO (templates/planos/).
# Os nomes das funções e os endereços são os do contrato do front: os templates chamam
# url_for('planos.lista'), 'planos.novo', 'planos.editar' e 'planos.alternar'.
# Antes (back-04), 'lista' e 'novo' eram só "pontes" que redirecionavam para as telas antigas
# (/planos/listar/ e /planos/criar/); 'editar' e 'alternar' não existiam com estes nomes.
#
# As rotas ANTIGAS, lá em cima, continuam funcionando: as telas antigas de alunos e de
# pagamentos ainda têm links para elas. Saem quando o layout antigo sair.
#
# As regras (validação, números de cada cartão) ficam em services/plano_tela_service.py.
# ---------------------------------------------------------------------------
def _plano_da_conta(id):
    """O plano, se for da conta de quem está logado; senão 404 (como se não existisse)."""
    return da_conta(Plano).filter_by(id=id).first_or_404()


@planos_blueprint.route('')
def lista():
    # o instrutor consulta os planos, mas o serviço não entrega a ele os valores de faturamento
    return render_template('planos/lista.html', **telas.contexto_da_lista(request.args))


def _salvar(plano=None):
    """Cria (plano=None) ou edita. Com erro, volta a página do formulário com o que foi digitado."""
    valores, erros = telas.validar(request.form, plano)
    if erros:
        flash(telas.aviso_dos_erros(erros), 'error')
        return render_template('planos/form.html', plano=telas.do_formulario(valores, request.form, plano),
                               erros=erros, modo='editar' if plano else 'novo')
    if plano:
        telas.atualizar(plano, valores)
        flash('Plano salvo.', 'success')
    else:
        telas.criar(valores)
        flash('Plano criado. Ele já aparece na hora de matricular.' if valores['ativo']
              else 'Plano criado como inativo. Ative para ele aparecer na hora de matricular.', 'success')
    return redirect(url_for('planos.lista'))


@planos_blueprint.route('/novo', methods=['GET', 'POST'])
@papel_requerido(*DONO_E_RECEPCAO)   # plano e preço: instrutor só consulta
def novo():
    if request.method == 'POST':
        return _salvar()
    return render_template('planos/form.html', plano={}, erros={}, modo='novo')


@planos_blueprint.route('/<int:id>/editar', methods=['GET', 'POST'])
@papel_requerido(*DONO_E_RECEPCAO)
def editar(id):
    plano = _plano_da_conta(id)
    if request.method == 'POST':
        return _salvar(plano)
    return render_template('planos/form.html', plano=telas.linha_do_plano(plano), erros={}, modo='editar')


@planos_blueprint.route('/<int:id>/alternar', methods=['POST'])
@papel_requerido(*DONO_E_RECEPCAO)
def alternar(id):
    # Pausar NÃO apaga: o plano some do cadastro de aluno e continua em quem já está nele.
    plano = telas.alternar(_plano_da_conta(id))
    flash(f"Plano {plano.nome} {'reativado' if plano.ativo else 'inativado'}.", 'success')
    return redirect(url_for('planos.lista'))