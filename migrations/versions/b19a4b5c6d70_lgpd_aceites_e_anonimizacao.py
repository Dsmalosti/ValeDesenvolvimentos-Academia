"""LGPD: aceite dos termos, vontade do aluno sobre o WhatsApp e marca de dados apagados

[back-19-lgpd] Quatro colunas novas, todas aceitando vazio. Nenhum dado existente muda.

  instrutores   termos_versao, termos_aceitos_em   qual versão dos termos a pessoa aceitou ao criar a conta, e quando.
                                                   Vazio para quem criou a conta antes desta branch.
  alunos        aceita_whatsapp                    sim, não, ou vazio (ainda não foi perguntado)
  alunos        anonimizado_em                     quando os dados pessoais do aluno foram apagados a pedido (LGPD).
                                                   Com esta data preenchida o aluno some das telas.

Downgrade: remove as quatro colunas. (Os dados que já foram apagados não voltam; só se perde o registro de
que foram apagados, e esses alunos voltariam a aparecer nas listas como "Aluno removido".)

Revision ID: b19a4b5c6d70
Revises: b17f3a4b5c60
Create Date: 2026-10-13
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b19a4b5c6d70'
down_revision = 'b17f3a4b5c60'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('instrutores') as lote:
        lote.add_column(sa.Column('termos_versao', sa.String(length=30), nullable=True))
        lote.add_column(sa.Column('termos_aceitos_em', sa.DateTime(), nullable=True))
    with op.batch_alter_table('alunos') as lote:
        lote.add_column(sa.Column('aceita_whatsapp', sa.Boolean(), nullable=True))
        lote.add_column(sa.Column('anonimizado_em', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('alunos') as lote:
        lote.drop_column('anonimizado_em')
        lote.drop_column('aceita_whatsapp')
    with op.batch_alter_table('instrutores') as lote:
        lote.drop_column('termos_aceitos_em')
        lote.drop_column('termos_versao')
