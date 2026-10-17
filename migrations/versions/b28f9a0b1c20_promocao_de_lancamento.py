"""Promoção de lançamento: desconto em % de cada conta

[back-28-precos-e-promocao] Uma coluna nova, que nasce 0 (sem promoção) em todas as contas que já existem.

  contas   desconto_promocional   % de desconto na mensalidade do Vale Tec. As 10 primeiras contas criadas depois desta
                                  versão ganham 50% (regra em services/assinatura_service.py). O admin muda em /admin.

Por que as contas que já existem ficam com 0: no banco de produção ainda não há cliente (ele nasce com `flask banco-novo`).
Se houver, o admin dá a promoção à mão, conta por conta.

Downgrade: apaga a coluna (quem tinha promoção volta a pagar o preço cheio).

Revision ID: b28f9a0b1c20
Revises: b26e8f9a0b10
Create Date: 2026-10-17
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b28f9a0b1c20'
down_revision = 'b26e8f9a0b10'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('contas') as lote:
        lote.add_column(sa.Column('desconto_promocional', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('contas') as lote:
        lote.drop_column('desconto_promocional')
