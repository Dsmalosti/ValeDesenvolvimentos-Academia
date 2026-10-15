"""
Blueprint `painel` — a tela inicial do front novo (templates/painel/index.html).

[back-04-painel] Criado nesta branch. Antes a página inicial era `main.homepage`, com a tela
antiga (templates/index.html). O nome do endpoint segue o contrato do front: os templates
chamam url_for('painel.index') e url_for('painel.notificacoes').
"""
from flask import Blueprint, render_template
from flask_login import current_user

from app.blueprints.pendentes import tela_em_construcao
from app.helpers.conta import exigir_login_em
from app.models import PAPEL_INSTRUTOR
from app.services.painel_service import montar_painel
from app.services import pacote_service, personal_service  # [back-17-personal]
from app.services.config_service import aplicar_inatividade_uma_vez_por_dia  # [back-12-config]

painel_blueprint = Blueprint('painel', __name__)
exigir_login_em(painel_blueprint)  # toda rota daqui exige login, mesmo as futuras


@painel_blueprint.route('/')
def index():
    # [back-06-contas-e-papeis] O painel gerencial mostra faturamento e inadimplência, que o instrutor não pode ver.
    # O front tem um painel próprio para ele (painel/instrutor.html), ainda não ligado; até lá o
    # instrutor vê o aviso de "em construção" em vez dos números da academia.
    if current_user.papel == PAPEL_INSTRUTOR:
        return tela_em_construcao('Painel do instrutor')
    # montar_painel() devolve exatamente as variáveis que o template declara no topo:
    # k, serie, planos_fat, alunos, alertas, listas, pendentes e hoje.
    # [back-12-config] "o aluno vira Inativo sozinho depois de X dias sem renovar": a regra roda aqui, no máximo uma
    # vez por dia para a conta, antes de montar os números (assim não depende de tarefa agendada no servidor).
    aplicar_inatividade_uma_vez_por_dia()
    if pacote_service.e_personal():
        # [back-17-personal] conta de personal trainer: mesmo endereço, outra tela (pacotes e sessões no lugar de
        # vencimentos e check-in). Antes: toda conta via o painel da academia.
        return render_template('personal/painel.html', **personal_service.contexto_do_painel())
    return render_template('painel/index.html', **montar_painel())


@painel_blueprint.route('/notificacoes')
def notificacoes():
    # A central de notificações ainda não existe no backend (tarefa 5.1).
    return tela_em_construcao('Notificações')
