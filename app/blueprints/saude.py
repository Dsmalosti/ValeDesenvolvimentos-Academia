"""
[back-20-producao] GET /saude: a pergunta "o app está de pé?" que toda hospedagem faz de tempos em tempos.

É pública de propósito (o monitor da hospedagem não tem login) e não mostra NADA do sistema: responde
"ok" se o app respondeu e o banco aceitou uma consulta, ou "banco fora do ar" com o código 503.
Antes desta branch não existia: o monitor teria de bater na tela de login.

É a ÚNICA rota que aceita HTTP sem redirecionar para HTTPS em produção: o monitor da hospedagem costuma chamar o
app por dentro da rede dela, sem HTTPS, e um redirecionamento seria lido como "app fora do ar". Como a resposta
é só a palavra "ok", não há o que proteger aqui.
"""
from flask import Blueprint
from sqlalchemy import text

from app.extensions.database import db
from app.extensions.protecao import talisman

saude_blueprint = Blueprint('saude', __name__)


@saude_blueprint.route('/saude')
@talisman(force_https=False)
def saude():
    try:
        db.session.execute(text('SELECT 1'))
    except Exception:       # qualquer falha de banco: o monitor só precisa saber que não está tudo bem
        db.session.rollback()
        return 'banco fora do ar', 503, {'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store'}
    return 'ok', 200, {'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store'}
