"""mensagens: tabela `mensagens_enviadas`

[back-16-mensagens] Guarda o toque em "Enviar no WhatsApp" de cada linha da fila do dia: quem
tocou, para qual aluno, de que tipo e em que dia. Não guarda texto nem telefone.

A combinação (conta, tipo, referência, dia) é única: tocar duas vezes no mesmo dia não duplica.

Nenhuma tabela que já existe é alterada. Downgrade: apaga a tabela (some o histórico de "enviada").

Revision ID: b16e2f3a4b50
Revises: b15d1e2f3a40
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b16e2f3a4b50'
down_revision = 'b15d1e2f3a40'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'mensagens_enviadas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('referencia', sa.String(length=40), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('enviada_em', sa.DateTime(), nullable=False),
        sa.Column('enviada_por_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], name=op.f('fk_mensagens_enviadas_conta_id_contas')),
        sa.ForeignKeyConstraint(['aluno_id'], ['alunos.id'], name=op.f('fk_mensagens_enviadas_aluno_id_alunos')),
        sa.ForeignKeyConstraint(['enviada_por_id'], ['instrutores.id'], name=op.f('fk_mensagens_enviadas_enviada_por_id_instrutores')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_mensagens_enviadas')),
        sa.UniqueConstraint('conta_id', 'tipo', 'referencia', 'data', name='uq_mensagens_enviadas_conta_id_tipo_referencia_data'),
    )
    op.create_index(op.f('ix_mensagens_enviadas_aluno_id'), 'mensagens_enviadas', ['aluno_id'])
    op.create_index('ix_mensagens_enviadas_conta_data', 'mensagens_enviadas', ['conta_id', 'data'])


def downgrade():
    op.drop_index('ix_mensagens_enviadas_conta_data', table_name='mensagens_enviadas')
    op.drop_index(op.f('ix_mensagens_enviadas_aluno_id'), table_name='mensagens_enviadas')
    op.drop_table('mensagens_enviadas')
