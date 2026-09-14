"""
Isolamento multi-tenant: cada instrutor logado só enxerga os próprios registros.

Toda rota que lê ou altera dados deve passar por estas funções em vez de
usar Model.query direto.
"""
from flask import abort
from flask_login import current_user

from app.extensions.database import db


def do_instrutor(model):
    """Query já filtrada pela academia do instrutor logado."""
    return model.query.filter(model.instrutor_id == current_user.id)


def obter_do_instrutor_ou_404(model, obj_id):
    """Busca um registro da academia logada. Registros de outra academia viram 404."""
    obj = db.session.get(model, obj_id)
    if obj is None or obj.instrutor_id != current_user.id:
        abort(404)
    return obj
