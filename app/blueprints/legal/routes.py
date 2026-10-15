"""
[back-19-lgpd] Páginas PÚBLICAS dos textos legais: /termos e /privacidade.

São os dois textos que a tela "Criar conta" cita ("Ao criar a conta você aceita os termos de uso e
a política de privacidade"). Antes desta branch os links dessa frase não levavam a lugar nenhum.
Qualquer pessoa abre, com ou sem login. O texto e a versão ficam em services/legal_service.py.
"""
from flask import Blueprint, render_template, url_for

from app.services import legal_service

legal_blueprint = Blueprint('legal', __name__)


@legal_blueprint.route('/termos')
def termos():
    return render_template('legal/pagina.html', **legal_service.pagina('termos', url_for))


@legal_blueprint.route('/privacidade')
def privacidade():
    return render_template('legal/pagina.html', **legal_service.pagina('privacidade', url_for))
