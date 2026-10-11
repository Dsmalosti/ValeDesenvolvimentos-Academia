"""
Blueprint `painel` — a tela inicial do front novo (templates/painel/index.html).

[back-04-painel] Criado nesta branch. Antes a página inicial era `main.homepage`, com a tela
antiga (templates/index.html). O nome do endpoint segue o contrato do front: os templates
chamam url_for('painel.index') e url_for('painel.notificacoes').
"""
from flask import Blueprint, render_template

from app.blueprints.pendentes import tela_em_construcao
from app.helpers.conta import exigir_login_em
from app.services.painel_service import montar_painel

painel_blueprint = Blueprint('painel', __name__)
exigir_login_em(painel_blueprint)  # toda rota daqui exige login, mesmo as futuras


@painel_blueprint.route('/')
def index():
    # montar_painel() devolve exatamente as variáveis que o template declara no topo:
    # k, serie, planos_fat, alunos, alertas, listas, pendentes e hoje.
    return render_template('painel/index.html', **montar_painel())


@painel_blueprint.route('/notificacoes')
def notificacoes():
    # A central de notificações ainda não existe no backend (tarefa 5.1).
    return tela_em_construcao('Notificações')
