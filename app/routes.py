from flask import Blueprint, render_template
from flask_login import login_required
from app.services.dashboard_service import obter_dados_dashboard

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/')
@login_required
def homepage():
    dados = obter_dados_dashboard()

    return render_template(
        'index.html',
        ativos=dados["ativos"],
        aniversariantes=dados["aniversariantes"]
    )







