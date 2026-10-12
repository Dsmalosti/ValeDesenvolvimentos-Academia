"""
[back-09-cobranca] Rotas da COBRANÇA do front novo (templates/cobranca/receber.html).

Os nomes das funções e os endereços são os do contrato do front (url_for('cobrancas.receber'),
'cobrancas.confirmar' etc.). Antes desta branch só existiam 'cobrancas.diaria' e
'cobrancas.lembrete_lote', como telas "em construção" em blueprints/pendentes.py.

As regras ficam em services/cobranca_service.py; aqui a rota confere a conta e o papel, chama o
serviço e escolhe a resposta. Instrutor não entra em nenhuma rota daqui (403): é dinheiro.
"""
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

from app.helpers.conta import DONO_E_RECEPCAO, da_conta, exigir_papel_em
from app.models import COBRANCA_CANCELADA, COBRANCA_PAGA, Aluno
from app.services import cobranca_service as cobrancas

cobrancas_blueprint = Blueprint('cobrancas', __name__, url_prefix='/cobrancas')
exigir_papel_em(cobrancas_blueprint, *DONO_E_RECEPCAO)   # toda rota daqui, inclusive as futuras


def _cobranca(id):
    """A cobrança, se for da conta de quem está logado e não estiver cancelada; senão 404."""
    cobranca = cobrancas.cobranca_da_conta(id)
    if cobranca is None or cobranca.status == COBRANCA_CANCELADA:
        abort(404)
    return cobranca


@cobrancas_blueprint.route('/matricula/<int:aluno_id>')
def receber_matricula(aluno_id):
    # Não cria nada (é GET): leva à cobrança em aberto do aluno. Se não houver, vai para a tela de
    # renovar, que é onde uma cobrança nova nasce, por POST.
    aluno = da_conta(Aluno).filter_by(id=aluno_id).first_or_404()
    aberta = cobrancas.em_aberto_do(aluno)
    if aberta:
        return redirect(url_for('cobrancas.receber', id=aberta.id, forma=request.args.get('forma')))
    return redirect(url_for('alunos.renovar', id=aluno.id))


@cobrancas_blueprint.route('/<int:id>/receber')
def receber(id):
    cobranca = _cobranca(id)
    return render_template('cobranca/receber.html', c=cobrancas.para_a_tela(cobranca, request.args.get('forma')),
                           # PIX automático (QR Code que confirma sozinho) ainda não existe: no lançamento o PIX
                           # é conferido e confirmado pela recepção, como dinheiro e cartão.
                           pix_ligado=False, pix_manual=True,
                           recem_confirmado=bool(request.args.get('ok')) and cobranca.status == COBRANCA_PAGA)


@cobrancas_blueprint.route('/<int:id>/confirmar', methods=['POST'])
def confirmar(id):
    cobranca = _cobranca(id)
    try:
        cobrancas.confirmar(cobranca, request.form.get('forma'), request.form.get('valor_recebido'))
    except cobrancas.CobrancaInvalida as erro:
        flash(str(erro), 'error')
        return redirect(url_for('cobrancas.receber', id=id, forma=request.form.get('forma')))
    return redirect(url_for('cobrancas.receber', id=id, ok=1))


@cobrancas_blueprint.route('/<int:id>/status')
def status(id):
    # o front consulta de tempos em tempos enquanto espera um PIX automático; hoje só responde o estado
    cobranca = _cobranca(id)
    pago = cobranca.status == COBRANCA_PAGA
    return jsonify(estado='confirmado' if pago else 'pendente',
                   origem=cobranca.pagamentos[-1].origem_confirmacao if (pago and cobranca.pagamentos) else None)


@cobrancas_blueprint.route('/<int:id>/depois')
def depois(id):
    # "Cobrar depois": não muda nada, a cobrança já está em aberto. Só avisa e sai da tela.
    cobranca = _cobranca(id)
    flash('Cobrança deixada em aberto. Ela aparece como pendente no painel.', 'success')
    if cobranca.aluno_id:
        return redirect(url_for('alunos.detalhe', id=cobranca.aluno_id))
    return redirect(url_for('painel.index'))


@cobrancas_blueprint.route('/diaria', methods=['POST'])
def diaria():
    try:
        cobranca = cobrancas.gerar_diaria(request.form.get('valor'), request.form.get('nome_visitante'))
    except cobrancas.CobrancaInvalida as erro:
        flash(str(erro), 'error')
        return redirect(url_for('painel.index'))
    return redirect(url_for('cobrancas.receber', id=cobranca.id, forma=request.form.get('forma_pagamento')))


# --- PIX automático: fica para depois do lançamento. O template cita estas duas rotas. ---
@cobrancas_blueprint.route('/<int:id>/pix', methods=['POST'])
def pix(id):
    _cobranca(id)
    flash('O PIX automático ainda não está disponível. Confira o PIX no aplicativo do banco e confirme aqui.', 'info')
    return redirect(url_for('cobrancas.receber', id=id, forma='pix'))


@cobrancas_blueprint.route('/<int:id>/cancelar-pix', methods=['POST'])
def cancelar_pix(id):
    _cobranca(id)
    return redirect(url_for('cobrancas.receber', id=id))


@cobrancas_blueprint.route('/lembrete', methods=['POST'])
def lembrete_lote():
    # [back-16-mensagens] antes: só avisava "ainda não está disponível" e voltava ao painel. O WhatsApp não envia
    # em lote sem a API paga: a cobrança de cada aluno atrasado está na fila de mensagens, com o texto pronto,
    # e a pessoa toca em uma por uma.
    flash('As cobranças atrasadas estão na fila abaixo, com o texto pronto. Toque em cada uma para abrir o WhatsApp.', 'info')
    return redirect(url_for('mensagens.index'))
