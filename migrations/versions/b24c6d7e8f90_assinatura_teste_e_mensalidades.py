"""Assinatura do Vale Tec: fim do teste grátis, período pago e os pagamentos da mensalidade

[back-24-assinatura] Antes não existia cobrança do próprio Vale Tec: toda conta usava o sistema para sempre.

  contas         teste_ate   último dia do teste grátis. As contas que já existem recebem a data de criação + 2 meses
                             (sem data de criação, hoje + 2 meses). Ninguém fica bloqueado por causa desta migration.
  contas         pago_ate    último dia do período pago. Vazio para todas (ninguém pagou ainda).
  mensalidades   (nova)      cada pagamento confirmado: conta, valor, meses, período, quando, quem confirmou.

Downgrade: apaga a tabela mensalidades e as duas colunas (os pagamentos registrados se perdem).

Revision ID: b24c6d7e8f90
Revises: b22b5c6d7e80
Create Date: 2026-10-14
"""
import calendar
from datetime import date, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b24c6d7e8f90'
down_revision = 'b22b5c6d7e80'
branch_labels = None
depends_on = None


def _mais_dois_meses(dia):
    """Cópia de app/helpers/datas.somar_meses(dia, 2): a migration não importa código do app, que pode mudar depois."""
    total = dia.month - 1 + 2
    ano, mes = dia.year + total // 12, total % 12 + 1
    return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


def _como_data(valor):
    if valor is None:
        return date.today()
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return datetime.fromisoformat(str(valor)[:19]).date()       # SQLite devolve texto


def upgrade():
    with op.batch_alter_table('contas') as lote:
        lote.add_column(sa.Column('teste_ate', sa.Date(), nullable=True))
        lote.add_column(sa.Column('pago_ate', sa.Date(), nullable=True))
    op.create_table(
        'mensalidades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=False),
        sa.Column('valor', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('meses', sa.Integer(), nullable=False),
        sa.Column('periodo_inicio', sa.Date(), nullable=False),
        sa.Column('periodo_fim', sa.Date(), nullable=False),
        sa.Column('pago_em', sa.DateTime(), nullable=False),
        sa.Column('forma', sa.String(length=20), nullable=False),
        sa.Column('registrado_por_id', sa.Integer(), nullable=True),
        sa.Column('observacao', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], name='fk_mensalidades_conta_id_contas'),
        sa.ForeignKeyConstraint(['registrado_por_id'], ['instrutores.id'], name='fk_mensalidades_registrado_por_id_instrutores'),
        sa.PrimaryKeyConstraint('id', name='pk_mensalidades'),
    )
    op.create_index('ix_mensalidades_conta_id', 'mensalidades', ['conta_id'])

    # as contas que já existem começam o teste a partir da data em que foram criadas
    conexao = op.get_bind()
    for conta_id, criado_em in conexao.execute(sa.text('SELECT id, criado_em FROM contas')).fetchall():
        conexao.execute(sa.text('UPDATE contas SET teste_ate = :ate WHERE id = :id'), {'ate': _mais_dois_meses(_como_data(criado_em)), 'id': conta_id})


def downgrade():
    op.drop_index('ix_mensalidades_conta_id', table_name='mensalidades')
    op.drop_table('mensalidades')
    with op.batch_alter_table('contas') as lote:
        lote.drop_column('pago_ate')
        lote.drop_column('teste_ate')
