"""frequência: tabela `frequencias`, coluna `alunos.acesso_liberado` e check-in ligado nas academias

[back-10-frequencia]

  1. cria `frequencias`: uma linha para cada entrada de aluno (quem, quando, por onde e quem registrou).
     Não existe coluna "presente sim/não": faltar é NÃO TER linha.
  2. acrescenta `alunos.acesso_liberado` (sim/não, padrão sim): o botão "Bloquear" da recepção.
     Os alunos que já existem ficam com o acesso liberado.
  3. liga o serviço de check-in (`contas.checkin_ativo`) nas contas do modelo "academia". A coluna
     já existia desde a back-06, sempre desligada, e a tela de frequência só aparece com ela ligada.
     Conta do modelo "personal" continua com o check-in desligado.

Downgrade: apaga `frequencias` (as entradas registradas se perdem) e a coluna `acesso_liberado`.
O check-in das contas NÃO é desligado de volta: não há como saber quais já estavam ligadas.

Revision ID: b10e6f7a8b90
Revises: b09d5e6f7a80
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b10e6f7a8b90'
down_revision = 'b09d5e6f7a80'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'frequencias',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('data_hora_entrada', sa.DateTime(), nullable=False),
        sa.Column('origem', sa.String(length=20), nullable=False),
        sa.Column('instrutor_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], name=op.f('fk_frequencias_conta_id_contas')),
        sa.ForeignKeyConstraint(['aluno_id'], ['alunos.id'], name=op.f('fk_frequencias_aluno_id_alunos')),
        sa.ForeignKeyConstraint(['instrutor_id'], ['instrutores.id'], name=op.f('fk_frequencias_instrutor_id_instrutores')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_frequencias')),
    )
    op.create_index('ix_frequencias_conta_entrada', 'frequencias', ['conta_id', 'data_hora_entrada'])
    op.create_index('ix_frequencias_aluno_entrada', 'frequencias', ['aluno_id', 'data_hora_entrada'])

    with op.batch_alter_table('alunos') as lote:
        # server_default preenche os alunos que já existem; sem ele o NOT NULL falharia
        lote.add_column(sa.Column('acesso_liberado', sa.Boolean(), nullable=False, server_default=sa.true()))

    op.execute("UPDATE contas SET checkin_ativo = true WHERE modelo = 'academia'")


def downgrade():
    with op.batch_alter_table('alunos') as lote:
        lote.drop_column('acesso_liberado')
    op.drop_index('ix_frequencias_aluno_entrada', table_name='frequencias')
    op.drop_index('ix_frequencias_conta_entrada', table_name='frequencias')
    op.drop_table('frequencias')
