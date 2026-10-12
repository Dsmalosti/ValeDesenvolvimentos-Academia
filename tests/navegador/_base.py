"""
Ajudantes dos testes de navegador (tests/navegador/*_navegador.py).

Só funções: quem define o banco descartável e sobe o app é cada teste, antes de importar isto.
"""
from datetime import datetime


def pagamento_recebido(db, aluno, quem, valor, pago_em, vence_em, forma="pix"):
    """
    Semeia um pagamento já recebido de `aluno`: a cobrança paga (do plano atual dele, cobrindo de
    `pago_em` até `vence_em`) e o pagamento que a quitou, confirmado por `quem`. Não dá commit.
    """
    from app.models import Cobranca, Pagamento
    cobranca = Cobranca(conta_id=aluno.conta_id, aluno_id=aluno.id, plano_id=aluno.plano_id, tipo="renovacao", valor=valor,
                        data_inicio=pago_em, data_vencimento=vence_em, status="paga", instrutor_id=quem.id)
    db.session.add(cobranca)
    db.session.flush()
    db.session.add(Pagamento(conta_id=aluno.conta_id, cobranca_id=cobranca.id, forma=forma, valor_pago=valor,
                             data_pagamento=datetime(pago_em.year, pago_em.month, pago_em.day, 12, 0),
                             origem_confirmacao="manual", confirmado_por_instrutor_id=quem.id))
    return cobranca
