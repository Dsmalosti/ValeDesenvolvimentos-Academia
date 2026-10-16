# [back-27-telas-antigas] antes também importava db, flask_login, PlanoForm e PlanoService (só as telas antigas usavam)
from flask import Blueprint,render_template, url_for, request, redirect, flash
from app.models import Plano
from app.services import plano_tela_service as telas  # [back-08-planos] regras das telas novas
from app.services import pacote_service  # [back-17-personal] conta de personal: plano vira pacote
from app.helpers.conta import DONO_E_RECEPCAO, da_conta, exigir_login_em, papel_requerido

planos_blueprint = Blueprint('planos', __name__, url_prefix='/planos')  # [back-27-telas-antigas] antes: template_folder='templates'
exigir_login_em(planos_blueprint)  # [back-03-isolamento] toda rota daqui exige login, mesmo as futuras

# ---------------------------------------------------------------------------
# [back-08-planos] TELAS DE PLANOS DO FRONT NOVO (templates/planos/).
# Os nomes das funções e os endereços são os do contrato do front: os templates chamam
# url_for('planos.lista'), 'planos.novo', 'planos.editar' e 'planos.alternar'.
# Antes (back-04), 'lista' e 'novo' eram só "pontes" que redirecionavam para as telas antigas
# (/planos/listar/ e /planos/criar/); 'editar' e 'alternar' não existiam com estes nomes.
#
# [back-27-telas-antigas] As rotas ANTIGAS que ficavam aqui em cima (/planos/criar/, /listar/, /editar/<id>/, /excluir/<id>)
# saíram junto com o layout antigo.
#
# As regras (validação, números de cada cartão) ficam em services/plano_tela_service.py.
# ---------------------------------------------------------------------------
def _plano_da_conta(id):
    """O plano, se for da conta de quem está logado; senão 404 (como se não existisse)."""
    return da_conta(Plano).filter_by(id=id).first_or_404()


# [back-17-personal] Na conta de personal trainer o "plano" é um PACOTE DE SESSÕES: mesmas rotas, mesma tabela, outros
# templates (personal/pacotes.html e personal/pacote_form.html) e outra palavra nos avisos. Antes: sempre os de plano.
def _tpl_lista():
    return 'personal/pacotes.html' if pacote_service.e_personal() else 'planos/lista.html'


def _tpl_form():
    return 'personal/pacote_form.html' if pacote_service.e_personal() else 'planos/form.html'


def _termo():
    return 'Pacote' if pacote_service.e_personal() else 'Plano'


@planos_blueprint.route('')
def lista():
    # o instrutor consulta os planos, mas o serviço não entrega a ele os valores de faturamento
    return render_template(_tpl_lista(), **telas.contexto_da_lista(request.args))


def _salvar(plano=None):
    """Cria (plano=None) ou edita. Com erro, volta a página do formulário com o que foi digitado."""
    valores, erros = telas.validar(request.form, plano)
    if erros:
        flash(telas.aviso_dos_erros(erros), 'error')
        return render_template(_tpl_form(), plano=telas.do_formulario(valores, request.form, plano),
                               erros=erros, modo='editar' if plano else 'novo')
    if plano:
        telas.atualizar(plano, valores)
        flash(f'{_termo()} salvo.', 'success')
    else:
        telas.criar(valores)
        flash(f'{_termo()} criado. Ele já aparece na hora de matricular.' if valores['ativo']
              else f'{_termo()} criado como inativo. Ative para ele aparecer na hora de matricular.', 'success')
    return redirect(url_for('planos.lista'))


@planos_blueprint.route('/novo', methods=['GET', 'POST'])
@papel_requerido(*DONO_E_RECEPCAO)   # plano e preço: instrutor só consulta
def novo():
    if request.method == 'POST':
        return _salvar()
    return render_template(_tpl_form(), plano={}, erros={}, modo='novo')


@planos_blueprint.route('/<int:id>/editar', methods=['GET', 'POST'])
@papel_requerido(*DONO_E_RECEPCAO)
def editar(id):
    plano = _plano_da_conta(id)
    if request.method == 'POST':
        return _salvar(plano)
    return render_template(_tpl_form(), plano=telas.linha_do_plano(plano), erros={}, modo='editar')


@planos_blueprint.route('/<int:id>/alternar', methods=['POST'])
@papel_requerido(*DONO_E_RECEPCAO)
def alternar(id):
    # Pausar NÃO apaga: o plano some do cadastro de aluno e continua em quem já está nele.
    plano = telas.alternar(_plano_da_conta(id))
    flash(f"{_termo()} {plano.nome} {'reativado' if plano.ativo else 'inativado'}.", 'success')
    return redirect(url_for('planos.lista'))