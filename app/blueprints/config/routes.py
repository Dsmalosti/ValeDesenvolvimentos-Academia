"""
[back-12-config] Rotas das CONFIGURAÇÕES do front novo (templates/config/).

Os nomes das funções e os endereços são os do contrato do front: 'config.index', 'config.salvar',
'config.horario', 'config.mensagem', 'config.funcionalidade', 'config.metas', 'config.membro',
'config.recebimento' e 'config.pix_alternar'. Antes desta branch só existia 'config.index', como
tela "em construção" em blueprints/pendentes.py.

Quem pode o quê:
  - ver a tela: todos (o instrutor não vê a aba de metas);
  - mudar dados da academia, horário, funcionalidades e metas: só o dono;
  - mudar os modelos de mensagem: dono e recepção (é a recepção que manda as mensagens);
  - ver o recebimento: dono e recepção.
As regras ficam em services/config_service.py.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.helpers.conta import DONO, DONO_E_RECEPCAO, exigir_login_em, papel_requerido
from app.services import config_service as config

config_blueprint = Blueprint('config', __name__, url_prefix='/configuracoes')
exigir_login_em(config_blueprint)   # toda rota daqui exige login, inclusive as futuras


def _volta(aba, ancora=''):
    return redirect(url_for('config.index', aba=aba) + ancora)


@config_blueprint.route('')
def index():
    return render_template('config/index.html', **config.contexto(request.args.get('aba')))


@config_blueprint.route('/academia', methods=['POST'])
@papel_requerido(*DONO)
def salvar():
    # O formulário também manda o arquivo da logo; ele é ignorado por enquanto (envio de imagem
    # fica para depois do lançamento, junto com a foto do aluno).
    try:
        config.salvar_academia(request.form)
        flash('Dados da academia salvos.', 'success')
    except config.ConfigInvalida as erro:
        flash(str(erro), 'error')
    return _volta('academia')


@config_blueprint.route('/horario', methods=['POST'])
@papel_requerido(*DONO)
def horario():
    try:
        config.salvar_horario(request.form)
        flash('Horário de funcionamento atualizado.', 'success')
    except config.ConfigInvalida as erro:
        flash(str(erro), 'error')
    return _volta('academia', '#horario')


@config_blueprint.route('/mensagem', methods=['POST'])
@papel_requerido(*DONO_E_RECEPCAO)
def mensagem():
    try:
        config.salvar_mensagem(request.form.get('tipo'), request.form.get('texto'))
        flash('Mensagem salva. Ela já aparece no botão de WhatsApp.', 'success')
    except config.ConfigInvalida as erro:
        flash(str(erro), 'error')
    return _volta('mensagens')


@config_blueprint.route('/funcionalidade', methods=['POST'])
@papel_requerido(*DONO)
def funcionalidade():
    chave = request.form.get('chave')
    try:
        flash(config.salvar_funcionalidade(chave, request.form.get('ligado') == '1', request.form.get('dias')), 'success')
    except config.ConfigInvalida as erro:
        flash(str(erro), 'error')
    return _volta('cobranca')


@config_blueprint.route('/metas', methods=['POST'])
@papel_requerido(*DONO)
def metas():
    valores, erros, devolver = config.validar_metas(request.form)
    if erros:
        flash('Revise os campos destacados.', 'error')
        return render_template('config/index.html', **config.contexto('metas', erros, devolver))
    config.salvar_metas(valores)
    flash('Metas salvas. Os gráficos já mostram a linha nova.', 'success')
    return _volta('metas')


@config_blueprint.route('/equipe', methods=['POST'])
@papel_requerido(*DONO)
def membro():
    # Convidar, trocar o papel e remover alguém da equipe entram na branch de equipe (back-13).
    flash('Convidar e gerenciar a equipe ainda não está disponível.', 'info')
    return _volta('equipe')


@config_blueprint.route('/recebimento')
@papel_requerido(*DONO_E_RECEPCAO)
def recebimento():
    return render_template('config/recebimento.html', **config.contexto_do_recebimento())


@config_blueprint.route('/recebimento/pix', methods=['POST'])
@papel_requerido(*DONO)
def pix_alternar():
    # PIX automático (QR Code que se confirma sozinho) depende de um provedor de pagamento, que
    # ainda não foi escolhido. No lançamento o PIX é conferido e confirmado pela recepção.
    flash('O PIX automático ainda não está disponível. Por enquanto a recepção confirma o PIX na tela de cobrança.', 'info')
    return redirect(url_for('config.recebimento'))
