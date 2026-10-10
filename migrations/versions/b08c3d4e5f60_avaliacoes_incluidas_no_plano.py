"""coluna nova do plano: avaliacoes_incluidas

[back-08-planos] O formulário de plano do front novo tem o campo "Avaliação física inclusa"
(nenhuma, 1, 2 ou 4) e o banco não tinha onde guardar. Esta migration só ACRESCENTA a coluna.
Os planos que já existem ficam com 0, que quer dizer "nenhuma, cobrada à parte".

O downgrade remove a coluna (o que tiver sido escolhido nela se perde).

Revision ID: b08c3d4e5f60
Revises: b07a1f2e3d40
Create Date: 2026-10-10
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b08c3d4e5f60'
down_revision = 'b07a1f2e3d40'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('planos') as lote:
        # server_default='0' preenche os planos que já existem; sem ele o NOT NULL falharia
        lote.add_column(sa.Column('avaliacoes_incluidas', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('planos') as lote:
        lote.drop_column('avaliacoes_incluidas')
