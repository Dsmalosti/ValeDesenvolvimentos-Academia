"""equipe: tabelas `convites` e `redefinicoes_senha`

[back-13-equipe]

  - `convites`: o convite que o dono manda para alguém entrar na equipe (recepção ou instrutor).
    Vale 7 dias e só pode ser usado uma vez.
  - `redefinicoes_senha`: o pedido de troca de senha de quem esqueceu. Vale 1 hora, uso único.

Nas duas, o banco guarda só o HASH (sha256) do código que vai no link, nunca o código: se o banco
vazar, os links não vazam junto.

Nenhuma tabela que já existe é alterada. Downgrade: apaga as duas (convites e pedidos pendentes
deixam de valer; os usuários já criados continuam).

Revision ID: b13b9c0d1e20
Revises: b12a8b9c0d10
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b13b9c0d1e20'
down_revision = 'b12a8b9c0d10'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'convites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('papel', sa.String(length=20), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('criado_por_id', sa.Integer(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('expira_em', sa.DateTime(), nullable=False),
        sa.Column('usado_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], name=op.f('fk_convites_conta_id_contas')),
        sa.ForeignKeyConstraint(['criado_por_id'], ['instrutores.id'], name=op.f('fk_convites_criado_por_id_instrutores')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_convites')),
        sa.UniqueConstraint('token_hash', name=op.f('uq_convites_token_hash')),
    )
    op.create_index(op.f('ix_convites_conta_id'), 'convites', ['conta_id'])

    op.create_table(
        'redefinicoes_senha',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('expira_em', sa.DateTime(), nullable=False),
        sa.Column('usado_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['instrutores.id'], name=op.f('fk_redefinicoes_senha_usuario_id_instrutores')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_redefinicoes_senha')),
        sa.UniqueConstraint('token_hash', name=op.f('uq_redefinicoes_senha_token_hash')),
    )
    op.create_index(op.f('ix_redefinicoes_senha_usuario_id'), 'redefinicoes_senha', ['usuario_id'])


def downgrade():
    op.drop_index(op.f('ix_redefinicoes_senha_usuario_id'), table_name='redefinicoes_senha')
    op.drop_table('redefinicoes_senha')
    op.drop_index(op.f('ix_convites_conta_id'), table_name='convites')
    op.drop_table('convites')
