from flask import Blueprint, render_template
from flask_login import login_required
from app.services.dashboard_service import obter_dados_dashboard
from app.helpers.conta import exigir_login_em

main_blueprint = Blueprint('main', __name__)
exigir_login_em(main_blueprint)  # [back-03-isolamento] toda rota daqui exige login, mesmo as futuras

@main_blueprint.route('/')
@login_required
def homepage():
    dados = obter_dados_dashboard()

    return render_template(
        'index.html',
        ativos=dados["ativos"],
        aniversariantes=dados["aniversariantes"]
    )







