from flask import Blueprint, redirect, url_for
from flask_login import login_required
from app.helpers.conta import exigir_login_em

main_blueprint = Blueprint('main', __name__)
exigir_login_em(main_blueprint)  # [back-03-isolamento] toda rota daqui exige login, mesmo as futuras

# [back-04-painel] antes: esta rota ficava em '/' e mostrava a tela inicial antiga
# (templates/index.html, com obter_dados_dashboard()). Agora '/' é o painel novo
# (painel.index). O endpoint `main.homepage` continua existindo, num endereço próprio,
# porque as telas antigas ainda o usam em links e redirects; ele só leva ao painel novo.
# Sai quando a última tela antiga for trocada.
@main_blueprint.route('/inicio-antigo/')
@login_required
def homepage():
    return redirect(url_for('painel.index'))
