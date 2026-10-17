"""
[back-25-admin] Rotas do PAINEL DE ADMINISTRAÇÃO (/admin). As regras ficam em services/admin_service.py.

Quem não é admin recebe 404 (a tela "não existe" para ele), como nas outras áreas protegidas do sistema.
A única rota daqui que não é só de admin é /admin/voltar: é por ela que o admin, "dentro" da conta de um
cliente (logado como o dono), volta a ser ele mesmo.

Também ficam aqui duas peças que valem para o app inteiro:
  - o último acesso de cada usuário (instrutores.ultimo_acesso_em), que o painel mostra;
  - `admin_dentro` em todo template: o aviso "você está na conta X como administrador" (base.html).
"""
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions.database import db
from app.models import Conta
from app.services import admin_service

admin_blueprint = Blueprint('admin', __name__)


def so_admin(funcao):
    @wraps(funcao)
    @login_required
    def conferida(*args, **kwargs):
        if not getattr(current_user, 'admin_sistema', False):
            abort(404)
        return funcao(*args, **kwargs)
    return conferida


def _conta(id):
    return db.session.get(Conta, id) or abort(404)


@admin_blueprint.before_app_request
def anotar_ultimo_acesso():
    if current_user.is_authenticated and not admin_service.dentro_de_uma_conta():
        admin_service.anotar_acesso(current_user)


@admin_blueprint.app_context_processor
def aviso_de_admin_dentro():
    """`admin_dentro` = {'conta': nome} enquanto um admin usa a conta de um cliente; senão nada."""
    if current_user.is_authenticated and admin_service.dentro_de_uma_conta():
        return {'admin_dentro': {'conta': current_user.conta.nome}}
    return {}


@admin_blueprint.route('/admin')
@so_admin
def index():
    return render_template('admin/index.html', **admin_service.contexto_da_lista(request.args.get('situacao', '')))


@admin_blueprint.route('/admin/contas/<int:id>')
@so_admin
def conta(id):
    return render_template('admin/conta.html', **admin_service.contexto_da_conta(_conta(id)))


def _acao(id, funcao, sucesso, *args):
    """Roda uma ação do admin numa conta, avisa o resultado e volta à página da conta."""
    alvo = _conta(id)
    try:
        funcao(current_user, alvo, *args)
        flash(sucesso, 'success')
    except admin_service.AcaoRecusada as erro:
        flash(str(erro), 'error')
    return redirect(url_for('admin.conta', id=id))


@admin_blueprint.route('/admin/contas/<int:id>/pagamento', methods=['POST'])
@so_admin
def pagamento(id):
    return _acao(id, admin_service.confirmar_pagamento, 'Pagamento confirmado. A conta está liberada.', request.form.get('meses', '1'), request.form.get('valor', ''))


@admin_blueprint.route('/admin/contas/<int:id>/teste', methods=['POST'])
@so_admin
def teste(id):
    return _acao(id, admin_service.mudar_teste, 'Fim do teste grátis alterado.', request.form.get('ate', ''))


@admin_blueprint.route('/admin/contas/<int:id>/bloquear', methods=['POST'])
@so_admin
def bloquear(id):
    return _acao(id, admin_service.bloquear, 'Conta bloqueada.', request.form.get('motivo', ''))


@admin_blueprint.route('/admin/contas/<int:id>/desbloquear', methods=['POST'])
@so_admin
def desbloquear(id):
    return _acao(id, admin_service.desbloquear, 'Bloqueio retirado.')


# [back-28-precos-e-promocao] dá (ligar=1) ou tira (ligar=0) o desconto da promoção de lançamento
@admin_blueprint.route('/admin/contas/<int:id>/promocao', methods=['POST'])
@so_admin
def promocao(id):
    ligar = request.form.get('ligar', '0')
    return _acao(id, admin_service.mudar_promocao, 'A conta ganhou a promoção.' if ligar == '1' else 'A promoção foi retirada da conta.', ligar)


@admin_blueprint.route('/admin/contas/<int:id>/entrar', methods=['POST'])
@so_admin
def entrar(id):
    alvo = _conta(id)
    try:
        admin_service.entrar(current_user, alvo)
    except admin_service.AcaoRecusada as erro:
        flash(str(erro), 'error')
        return redirect(url_for('admin.conta', id=id))
    flash(f'Você está na conta "{alvo.nome}" como o dono. Para sair, use o aviso do topo.', 'info')
    return redirect(url_for('painel.index'))


@admin_blueprint.route('/admin/voltar', methods=['POST'])
@login_required
def voltar():
    if not admin_service.dentro_de_uma_conta():
        abort(404)
    conta_do_cliente = current_user.conta
    admin = admin_service.voltar(conta_do_cliente)
    if admin is None:
        from flask_login import logout_user
        logout_user()
        flash('Entre de novo com o seu login.', 'info')
        return redirect(url_for('auth.login'))
    return redirect(url_for('admin.conta', id=conta_do_cliente.id))


@admin_blueprint.route('/admin/contas/<int:id>/apagar', methods=['POST'])
@so_admin
def apagar(id):
    alvo = _conta(id)
    nome = alvo.nome
    try:
        admin_service.apagar_conta(current_user, alvo, request.form.get('confirmacao', ''))
    except admin_service.AcaoRecusada as erro:
        flash(str(erro), 'error')
        return redirect(url_for('admin.conta', id=id))
    flash(f'A conta "{nome}" e todos os dados dela foram apagados.', 'success')
    return redirect(url_for('admin.index'))
