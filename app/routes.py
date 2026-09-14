from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import text

from app.extensions.database import db
from app.services.dashboard_service import obter_dados_dashboard

main_blueprint = Blueprint('main', __name__)

@main_blueprint.route('/')
@login_required
def homepage():
    dados = obter_dados_dashboard(current_user.id)
    return render_template('dashboard.html', **dados)


# Health check para o provedor de hospedagem
@main_blueprint.route('/saude')
def saude():
    db.session.execute(text("SELECT 1"))
    return {"status": "ok"}
