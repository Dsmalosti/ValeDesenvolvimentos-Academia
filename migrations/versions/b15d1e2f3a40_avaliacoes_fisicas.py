"""avaliações físicas: tabelas `avaliacoes_agendadas` e `avaliacoes_fisicas`

[back-15-avaliacoes]

  - `avaliacoes_agendadas`: o horário marcado para avaliar um aluno (a agenda).
  - `avaliacoes_fisicas`: a avaliação feita (anamnese, medidas, dobras, testes). `imc` e `rcq` são
    calculados pelo sistema ao salvar; não há campo de diagnóstico.

Nenhuma tabela que já existe é alterada. Downgrade: apaga as duas (e os dados delas).

Revision ID: b15d1e2f3a40
Revises: b14c0d1e2f30
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b15d1e2f3a40'
down_revision = 'b14c0d1e2f30'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'avaliacoes_agendadas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('hora', sa.String(length=5), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('avaliador_id', sa.Integer(), nullable=True),
        sa.Column('observacao', sa.String(length=200), nullable=True),
        sa.Column('cobranca', sa.String(length=10), nullable=False),
        sa.Column('criado_por_id', sa.Integer(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], name=op.f('fk_avaliacoes_agendadas_conta_id_contas')),
        sa.ForeignKeyConstraint(['aluno_id'], ['alunos.id'], name=op.f('fk_avaliacoes_agendadas_aluno_id_alunos')),
        sa.ForeignKeyConstraint(['avaliador_id'], ['instrutores.id'], name=op.f('fk_avaliacoes_agendadas_avaliador_id_instrutores')),
        sa.ForeignKeyConstraint(['criado_por_id'], ['instrutores.id'], name=op.f('fk_avaliacoes_agendadas_criado_por_id_instrutores')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_avaliacoes_agendadas')),
    )
    op.create_index(op.f('ix_avaliacoes_agendadas_aluno_id'), 'avaliacoes_agendadas', ['aluno_id'])
    op.create_index('ix_avaliacoes_agendadas_conta_data', 'avaliacoes_agendadas', ['conta_id', 'data'])

    op.create_table(
        'avaliacoes_fisicas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('avaliador_id', sa.Integer(), nullable=True),
        sa.Column('agendamento_id', sa.Integer(), nullable=True),
        sa.Column('objetivo', sa.String(length=200), nullable=True),
        sa.Column('restricoes', sa.Text(), nullable=True),
        sa.Column('medicamentos', sa.String(length=200), nullable=True),
        sa.Column('liberacao_medica', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('peso_kg', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('altura_cm', sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column('imc', sa.Numeric(precision=4, scale=1), nullable=False),
        sa.Column('cintura_cm', sa.Numeric(precision=5, scale=1), nullable=True),
        sa.Column('quadril_cm', sa.Numeric(precision=5, scale=1), nullable=True),
        sa.Column('rcq', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('braco_d_cm', sa.Numeric(precision=5, scale=1), nullable=True),
        sa.Column('coxa_d_cm', sa.Numeric(precision=5, scale=1), nullable=True),
        sa.Column('torax_cm', sa.Numeric(precision=5, scale=1), nullable=True),
        sa.Column('panturrilha_cm', sa.Numeric(precision=5, scale=1), nullable=True),
        sa.Column('dobra_triceps', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('dobra_subescapular', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('dobra_suprailiaca', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('dobra_abdominal', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('dobra_coxa', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('teste_flexao', sa.Integer(), nullable=True),
        sa.Column('teste_abdominal', sa.Integer(), nullable=True),
        sa.Column('teste_flexibilidade', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('anotacao', sa.Text(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], name=op.f('fk_avaliacoes_fisicas_conta_id_contas')),
        sa.ForeignKeyConstraint(['aluno_id'], ['alunos.id'], name=op.f('fk_avaliacoes_fisicas_aluno_id_alunos')),
        sa.ForeignKeyConstraint(['avaliador_id'], ['instrutores.id'], name=op.f('fk_avaliacoes_fisicas_avaliador_id_instrutores')),
        sa.ForeignKeyConstraint(['agendamento_id'], ['avaliacoes_agendadas.id'], name=op.f('fk_avaliacoes_fisicas_agendamento_id_avaliacoes_agendadas')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_avaliacoes_fisicas')),
    )
    op.create_index(op.f('ix_avaliacoes_fisicas_conta_id'), 'avaliacoes_fisicas', ['conta_id'])
    op.create_index('ix_avaliacoes_fisicas_aluno_data', 'avaliacoes_fisicas', ['aluno_id', 'data'])


def downgrade():
    op.drop_index('ix_avaliacoes_fisicas_aluno_data', table_name='avaliacoes_fisicas')
    op.drop_index(op.f('ix_avaliacoes_fisicas_conta_id'), table_name='avaliacoes_fisicas')
    op.drop_table('avaliacoes_fisicas')
    op.drop_index('ix_avaliacoes_agendadas_conta_data', table_name='avaliacoes_agendadas')
    op.drop_index(op.f('ix_avaliacoes_agendadas_aluno_id'), table_name='avaliacoes_agendadas')
    op.drop_table('avaliacoes_agendadas')
