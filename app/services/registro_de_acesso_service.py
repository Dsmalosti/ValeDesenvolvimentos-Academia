"""
[back-26-lgpd-final] REGISTROS DE ACESSO: data, hora e IP de cada entrada no sistema.

O Marco Civil da Internet (Lei 12.965/2014, art. 15) manda quem oferece um sistema pela internet guardar esses
registros por 6 meses, em sigilo. A Política de Privacidade já prometia isso; antes desta branch o sistema não guardava.

Regras:
  - grava no login de verdade e quando um administrador entra na conta de um cliente;
  - guarda o e-mail e os números da conta e do usuário SEM chave estrangeira: o registro tem de durar os 6 meses
    mesmo que a conta seja apagada antes;
  - a cada gravação, apaga os registros com mais de 6 meses (não precisa de tarefa agendada no servidor);
  - não aparece em tela nenhuma: só sai a pedido de autoridade, como a lei prevê.
"""
from datetime import date, datetime

from flask import request

from app.extensions.database import db
from app.helpers.datas import somar_meses
from app.models import RegistroDeAcesso

MESES_GUARDADOS = 6


def registrar(usuario, evento='login', agora=None):
    """Grava um acesso de `usuario` (evento: 'login' ou 'admin_entrou') e apaga os registros vencidos. Faz commit."""
    agora = agora or datetime.now()
    db.session.add(RegistroDeAcesso(usuario_id=usuario.id, conta_id=usuario.conta_id, email=(usuario.email or '')[:120],
                                    ip=(request.remote_addr or '')[:45], evento=evento, quando=agora))
    limite = somar_meses(agora.date(), -MESES_GUARDADOS)
    RegistroDeAcesso.query.filter(RegistroDeAcesso.quando < datetime(limite.year, limite.month, limite.day)).delete(synchronize_session=False)
    db.session.commit()
