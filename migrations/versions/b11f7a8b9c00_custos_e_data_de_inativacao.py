"""relatórios: tabela `custos` e coluna `alunos.data_inativacao`

[back-11-relatorios]

  1. cria `custos`: os custos fixos mensais da academia (aluguel, folha...). A soma deles é o
     "mínimo" do ponto de equilíbrio do painel administrativo.
  2. acrescenta `alunos.data_inativacao`: quando o aluno foi desativado. Vazia para quem está
     ativo. Para quem JÁ estava inativo antes desta migration ela também fica vazia: não há como
     saber quando saiu, e por isso esses alunos ficam de fora das contas de retenção e de churn
     (em vez de entrarem com uma data inventada).

Downgrade: apaga a tabela (os custos cadastrados se perdem) e a coluna.

Revision ID: b11f7a8b9c00
Revises: b10e6f7a8b90
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b11f7a8b9c00'
down_revision = 'b10e6f7a8b90'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'custos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=False),
        sa.Column('descricao', sa.String(length=100), nullable=False),
        sa.Column('valor', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], name=op.f('fk_custos_conta_id_contas')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_custos')),
    )
    op.create_index(op.f('ix_custos_conta_id'), 'custos', ['conta_id'])
    with op.batch_alter_table('alunos') as lote:
        lote.add_column(sa.Column('data_inativacao', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('alunos') as lote:
        lote.drop_column('data_inativacao')
    op.drop_index(op.f('ix_custos_conta_id'), table_name='custos')
    op.drop_table('custos')
