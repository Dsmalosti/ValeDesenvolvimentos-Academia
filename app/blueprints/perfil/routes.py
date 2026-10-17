"""
[back-30-meu-perfil] Rotas do MEU PERFIL (templates/perfil/index.html). Regras em services/perfil_service.py.

  GET  /perfil          perfil.index    a tela (todos os papéis, academia e personal)
  POST /perfil/dados    perfil.dados    nome, sobrenome e e-mail (o e-mail pede a senha atual)
  POST /perfil/senha    perfil.senha    troca a senha (pede a atual); os outros aparelhos saem da conta
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user

from app.extensions.protecao import limiter
from app.helpers.conta import exigir_login_em
from app.services import admin_service, perfil_service

perfil_blueprint = Blueprint('perfil', __name__, url_prefix='/perfil')
exigir_login_em(perfil_blueprint)   # toda rota daqui exige login

# Quem já está logado e tenta adivinhar a senha atual (ex.: celular de outra pessoa esquecido aberto)
LIMITE_DA_SENHA_ATUAL = '10 per hour'


def _tela(valores=None, erros=None, status=200, bloco=''):
    """A tela. `bloco` diz de qual formulário são os erros ('dados' ou 'senha'): os dois têm o campo "senha atual"."""
    return render_template('perfil/index.html', f=valores or perfil_service.valores_da_tela(current_user),
                           erros=erros or {}, bloco=bloco, admin_dentro_da_conta=admin_service.dentro_de_uma_conta()), status


def _admin_dentro():
    """O admin do Vale Tec está usando a conta de um cliente: não mexe no login nem na senha do dono."""
    if admin_service.dentro_de_uma_conta():
        flash('Você está na conta do cliente como administrador: o perfil é dele e não pode ser mudado por aqui.', 'error')
        return True
    return False


@perfil_blueprint.route('')
def index():
    return _tela()


@perfil_blueprint.route('/dados', methods=['POST'])
@limiter.limit(LIMITE_DA_SENHA_ATUAL)
def dados():
    if _admin_dentro():
        return redirect(url_for('perfil.index'))
    usuario = current_user._get_current_object()
    email_antes = usuario.email
    valores, erros = perfil_service.salvar_dados(usuario, request.form)
    if erros:
        return _tela(valores, erros, 400, 'dados')
    flash('Dados salvos. Agora você entra com o e-mail novo.' if valores['email'] != (email_antes or '').lower()
          else 'Dados salvos.', 'success')
    return redirect(url_for('perfil.index'))


@perfil_blueprint.route('/senha', methods=['POST'])
@limiter.limit(LIMITE_DA_SENHA_ATUAL)
def senha():
    if _admin_dentro():
        return redirect(url_for('perfil.index'))
    usuario = current_user._get_current_object()
    erros = perfil_service.trocar_senha(usuario, request.form.get('senha_atual') or '', request.form.get('senha_nova') or '')
    if erros:
        return _tela(None, erros, 400, 'senha')
    # a sessão guarda a "marca" da senha: com a senha nova, ela precisa ser renovada, senão este aparelho também sairia
    login_user(usuario)
    flash('Senha trocada. Se a conta estava aberta em outro aparelho, ele saiu e vai pedir a senha nova.', 'success')
    return redirect(url_for('perfil.index'))
