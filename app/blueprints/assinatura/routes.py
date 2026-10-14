"""
[back-24-assinatura] A ASSINATURA da conta no Vale Tec: a tela /assinatura, o aviso no topo das telas e o bloqueio.

Três peças (as regras ficam em services/assinatura_service.py):
  1. /assinatura: situação da conta, quanto custa e o "PIX copia e cola" para pagar. Com a conta bloqueada,
     é a única tela que abre (numa página sem o menu, que explica o motivo).
  2. o aviso no topo de toda tela (`aviso_assinatura`, usado em base.html) quando o vencimento está perto ou passou;
  3. o BLOQUEIO: com a conta bloqueada, toda página leva a /assinatura e todo envio de formulário é recusado (403).
     Continuam abrindo: sair, os termos, a política e o /saude.
Antes desta branch não existia nada disso: qualquer conta usava o sistema para sempre, sem pagar.
"""
from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user

from app.helpers.conta import exigir_login_em
from app.services import assinatura_service

assinatura_blueprint = Blueprint('assinatura', __name__)
exigir_login_em(assinatura_blueprint)

# o que uma conta bloqueada ainda consegue abrir
LIBERADAS_NO_BLOQUEIO = {'assinatura.index', 'auth.logout', 'auth.login', 'static', 'saude.saude', 'legal.termos', 'legal.privacidade'}


@assinatura_blueprint.before_app_request
def barrar_conta_bloqueada():
    if not current_user.is_authenticated or request.endpoint is None or request.endpoint in LIBERADAS_NO_BLOQUEIO:
        return None
    if not assinatura_service.bloqueada(current_user.conta):
        return None
    if request.method == 'GET':
        return redirect(url_for('assinatura.index'))
    abort(403)


@assinatura_blueprint.app_context_processor
def aviso_da_assinatura():
    """`aviso_assinatura` em todo template: {tom, titulo, texto, link} ou None (ver assinatura_service.aviso_do_topo)."""
    if not current_user.is_authenticated:
        return {}
    return {'aviso_assinatura': assinatura_service.aviso_do_topo(current_user.conta, current_user.papel)}


@assinatura_blueprint.route('/assinatura')
def index():
    contexto = assinatura_service.contexto_da_tela(current_user.conta, current_user)
    if contexto['s']['estado'] == assinatura_service.BLOQUEADA:
        return render_template('assinatura/bloqueada.html', **contexto)
    return render_template('assinatura/index.html', **contexto)
