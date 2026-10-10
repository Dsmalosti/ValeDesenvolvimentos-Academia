"""colunas novas do aluno: data_inicio, dia_vencimento, forma_pagamento, observacoes

[back-07-alunos] O formulário de aluno do front novo envia quatro campos que o banco não tinha
onde guardar. Esta migration só ACRESCENTA as colunas, todas aceitando vazio: os alunos que já
existem ficam com elas em branco e nada do que existe é alterado.

O downgrade remove as quatro colunas (o que tiver sido digitado nelas se perde).

Revision ID: b07a1f2e3d40
Revises: b06c0a1e2f30
Create Date: 2026-10-10
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b07a1f2e3d40'
down_revision = 'b06c0a1e2f30'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('alunos') as lote:
        lote.add_column(sa.Column('data_inicio', sa.Date(), nullable=True))
        lote.add_column(sa.Column('dia_vencimento', sa.Integer(), nullable=True))
        lote.add_column(sa.Column('forma_pagamento', sa.String(length=20), nullable=True))
        lote.add_column(sa.Column('observacoes', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('alunos') as lote:
        lote.drop_column('observacoes')
        lote.drop_column('forma_pagamento')
        lote.drop_column('dia_vencimento')
        lote.drop_column('data_inicio')
