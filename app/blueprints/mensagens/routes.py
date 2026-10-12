"""
[back-16-mensagens] Rotas da central de MENSAGENS do front novo (templates/mensagens/index.html).

Os nomes das funções e os endereços são os do contrato do front: 'mensagens.index' e
'mensagens.enviada'. Antes desta branch, 'mensagens.index' era uma tela "em construção"
(blueprints/pendentes.py) e a outra não existia.

Dono, recepção e instrutor usam a tela; as linhas de cobrança só aparecem para dono e recepção.
As regras ficam em services/mensagem_service.py.
"""
from flask import Blueprint, jsonify, render_template, request

from app.helpers.conta import exigir_login_em
from app.services import mensagem_service as mensagens

mensagens_blueprint = Blueprint('mensagens', __name__, url_prefix='/mensagens')
exigir_login_em(mensagens_blueprint)   # toda rota daqui exige login, inclusive as futuras


@mensagens_blueprint.route('')
def index():
    return render_template('mensagens/index.html', **mensagens.contexto_da_tela())


@mensagens_blueprint.route('/enviada', methods=['POST'])
def enviada():
    """
    A tela chama aqui, em segundo plano, quando a pessoa toca em "Enviar no WhatsApp": manda um JSON
    {"id": "cobranca-12"} com o código CSRF no cabeçalho X-CSRFToken (o CSRFProtect confere).
    Responde {"ok": true}, ou 404 se a linha não está na fila de hoje de quem está logado.
    """
    dados = request.get_json(silent=True) or {}
    id_do_item = str(dados.get('id') or request.form.get('id') or '')[:80]
    if not mensagens.marcar_enviada(id_do_item):
        return jsonify(ok=False), 404
    return jsonify(ok=True)
