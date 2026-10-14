"""Registros de acesso (data, hora e IP de cada entrada), guardados por 6 meses

[back-26-lgpd-final] O Marco Civil da Internet (art. 15) manda guardar esses registros por 6 meses. A tabela é nova
e nasce vazia; nenhum dado existente muda. Sem chave estrangeira, de propósito (o registro dura mesmo que a conta
seja apagada antes).

Downgrade: apaga a tabela (os registros se perdem).

Revision ID: b26e8f9a0b10
Revises: b25d7e8f9a00
Create Date: 2026-10-14
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b26e8f9a0b10'
down_revision = 'b25d7e8f9a00'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'registros_de_acesso',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('conta_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('ip', sa.String(length=45), nullable=False),
        sa.Column('evento', sa.String(length=20), nullable=False),
        sa.Column('quando', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_registros_de_acesso'),
    )
    op.create_index('ix_registros_de_acesso_quando', 'registros_de_acesso', ['quando'])


def downgrade():
    op.drop_index('ix_registros_de_acesso_quando', table_name='registros_de_acesso')
    op.drop_table('registros_de_acesso')
