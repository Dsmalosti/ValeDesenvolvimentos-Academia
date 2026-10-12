"""personal: pacotes de sessões, dados do profissional e a agenda (`sessoes`)

[back-17-personal] Tudo aqui é ACRÉSCIMO: colunas que aceitam vazio e uma tabela nova. Nada do que
a conta de academia usa muda de comportamento.

  planos       quantidade_sessoes   na conta de personal o plano é um pacote: quantas sessões ele dá
  cobrancas    quantidade_sessoes   quantas sessões aquela compra deu ao aluno (congelado na venda)
  contas       cpf, cref            o personal é pessoa física
  contas       locais_ativos        locais de atendimento ligados ("estudio,casa"); vazio = todos
  sessoes      (tabela nova)        a agenda: cada sessão marcada; a concluída abate 1 do saldo

Downgrade: remove as colunas e a tabela (a agenda e os saldos deixam de existir).

Revision ID: b17f3a4b5c60
Revises: b16e2f3a4b50
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b17f3a4b5c60'
down_revision = 'b16e2f3a4b50'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('planos') as lote:
        lote.add_column(sa.Column('quantidade_sessoes', sa.Integer(), nullable=True))
    with op.batch_alter_table('cobrancas') as lote:
        lote.add_column(sa.Column('quantidade_sessoes', sa.Integer(), nullable=True))
    with op.batch_alter_table('contas') as lote:
        lote.add_column(sa.Column('cpf', sa.String(length=14), nullable=True))
        lote.add_column(sa.Column('cref', sa.String(length=20), nullable=True))
        lote.add_column(sa.Column('locais_ativos', sa.String(length=60), nullable=True))

    op.create_table(
        'sessoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=False),
        sa.Column('instrutor_id', sa.Integer(), nullable=True),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('hora', sa.String(length=5), nullable=False),
        sa.Column('duracao', sa.Integer(), nullable=False),
        sa.Column('local', sa.String(length=20), nullable=False),
        sa.Column('repete', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('abateu', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('concluida_em', sa.DateTime(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], name=op.f('fk_sessoes_conta_id_contas')),
        sa.ForeignKeyConstraint(['aluno_id'], ['alunos.id'], name=op.f('fk_sessoes_aluno_id_alunos')),
        sa.ForeignKeyConstraint(['instrutor_id'], ['instrutores.id'], name=op.f('fk_sessoes_instrutor_id_instrutores')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_sessoes')),
    )
    op.create_index('ix_sessoes_conta_data', 'sessoes', ['conta_id', 'data'])
    op.create_index('ix_sessoes_aluno_status', 'sessoes', ['aluno_id', 'status'])


def downgrade():
    op.drop_index('ix_sessoes_aluno_status', table_name='sessoes')
    op.drop_index('ix_sessoes_conta_data', table_name='sessoes')
    op.drop_table('sessoes')
    with op.batch_alter_table('contas') as lote:
        lote.drop_column('locais_ativos')
        lote.drop_column('cref')
        lote.drop_column('cpf')
    with op.batch_alter_table('cobrancas') as lote:
        lote.drop_column('quantidade_sessoes')
    with op.batch_alter_table('planos') as lote:
        lote.drop_column('quantidade_sessoes')
