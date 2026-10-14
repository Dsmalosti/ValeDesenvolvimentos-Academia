"""Painel de administração: quem é admin, último acesso, bloqueio manual e o registro das ações dos admins

[back-25-admin] Nenhum dado existente muda: as colunas novas nascem vazias (ou "não", no caso de admin_sistema).

  instrutores   admin_sistema        sim/não: administrador do Vale Tec. Ninguém é admin depois da migration;
                                     liga-se com `flask admin-do-sistema --email ...`.
  instrutores   ultimo_acesso_em     quando a pessoa usou o sistema pela última vez.
  contas        bloqueio_manual_em   dia em que um admin bloqueou a conta à mão (vazio = não bloqueada à mão).
  contas        bloqueio_motivo      o motivo, que o cliente vê.
  acoes_admin   (nova)               o que cada admin fez em cada conta. Sem chave estrangeira, de propósito.

Downgrade: apaga a tabela e as quatro colunas (o registro das ações se perde).

Revision ID: b25d7e8f9a00
Revises: b24c6d7e8f90
Create Date: 2026-10-14
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b25d7e8f9a00'
down_revision = 'b24c6d7e8f90'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('instrutores') as lote:
        lote.add_column(sa.Column('admin_sistema', sa.Boolean(), nullable=False, server_default=sa.false()))
        lote.add_column(sa.Column('ultimo_acesso_em', sa.DateTime(), nullable=True))
    with op.batch_alter_table('contas') as lote:
        lote.add_column(sa.Column('bloqueio_manual_em', sa.Date(), nullable=True))
        lote.add_column(sa.Column('bloqueio_motivo', sa.String(length=200), nullable=True))
    op.create_table(
        'acoes_admin',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=True),
        sa.Column('admin_email', sa.String(length=120), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=True),
        sa.Column('conta_nome', sa.String(length=120), nullable=False),
        sa.Column('acao', sa.String(length=30), nullable=False),
        sa.Column('detalhe', sa.String(length=300), nullable=True),
        sa.Column('quando', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_acoes_admin'),
    )
    op.create_index('ix_acoes_admin_conta_id', 'acoes_admin', ['conta_id'])


def downgrade():
    op.drop_index('ix_acoes_admin_conta_id', table_name='acoes_admin')
    op.drop_table('acoes_admin')
    with op.batch_alter_table('contas') as lote:
        lote.drop_column('bloqueio_motivo')
        lote.drop_column('bloqueio_manual_em')
    with op.batch_alter_table('instrutores') as lote:
        lote.drop_column('ultimo_acesso_em')
        lote.drop_column('admin_sistema')
