"""Inatividade automática nasce desligada nas contas novas

[back-22-ajustes-de-produto] Muda só o valor PADRÃO da coluna contas.inatividade_ligada: de "ligada" para
"desligada". Nenhuma conta que já existe muda: quem ligou ou desligou a regra continua como estava.

Downgrade: o padrão volta a ser "ligada" (de novo, sem mexer nas contas que existem).

Revision ID: b22b5c6d7e80
Revises: b19a4b5c6d70
Create Date: 2026-10-14
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b22b5c6d7e80'
down_revision = 'b19a4b5c6d70'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('contas') as lote:
        lote.alter_column('inatividade_ligada', existing_type=sa.Boolean(), existing_nullable=False, server_default=sa.false())


def downgrade():
    with op.batch_alter_table('contas') as lote:
        lote.alter_column('inatividade_ligada', existing_type=sa.Boolean(), existing_nullable=False, server_default=sa.true())
