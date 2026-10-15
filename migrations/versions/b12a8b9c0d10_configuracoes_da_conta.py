"""configurações: horário, metas e funcionalidades na conta; tabela `modelos_mensagem`

[back-12-config]

  1. acrescenta em `contas`:
       horario_semana, horario_sabado, horario_domingo        texto livre ("06h - 22h", "Fechado"), vazio = não informado
       meta_alunos_ativos, meta_faturamento, meta_retencao    as três metas; vazio = sem meta
       inatividade_ligada (padrão sim), inatividade_dias (padrão 60)
                                                              "o aluno vira Inativo sozinho depois de X dias sem renovar"
       inatividade_conferida_em                               último dia em que a regra acima rodou para a conta
       lembretes_ligados (padrão sim)
  2. cria `modelos_mensagem`: o texto de cada modelo de WhatsApp que a academia alterou
     (um por tipo e por conta). Quem nunca alterou usa o texto padrão do código.

Nenhuma conta existente muda de comportamento na migration em si. ATENÇÃO para o que vem depois:
com a inatividade ligada por padrão, na primeira vez que o painel de cada conta abrir os alunos
com vencimento passado há mais de 60 dias são desativados (nada é apagado).

Downgrade: remove as colunas e a tabela (as configurações gravadas se perdem).

Revision ID: b12a8b9c0d10
Revises: b11f7a8b9c00
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b12a8b9c0d10'
down_revision = 'b11f7a8b9c00'
branch_labels = None
depends_on = None

COLUNAS = ('horario_semana', 'horario_sabado', 'horario_domingo', 'meta_alunos_ativos', 'meta_faturamento', 'meta_retencao',
           'inatividade_ligada', 'inatividade_dias', 'inatividade_conferida_em', 'lembretes_ligados')


def upgrade():
    with op.batch_alter_table('contas') as lote:
        lote.add_column(sa.Column('horario_semana', sa.String(length=40), nullable=True))
        lote.add_column(sa.Column('horario_sabado', sa.String(length=40), nullable=True))
        lote.add_column(sa.Column('horario_domingo', sa.String(length=40), nullable=True))
        lote.add_column(sa.Column('meta_alunos_ativos', sa.Integer(), nullable=True))
        lote.add_column(sa.Column('meta_faturamento', sa.Numeric(precision=10, scale=2), nullable=True))
        lote.add_column(sa.Column('meta_retencao', sa.Integer(), nullable=True))
        # server_default preenche as contas que já existem; sem ele o NOT NULL falharia
        lote.add_column(sa.Column('inatividade_ligada', sa.Boolean(), nullable=False, server_default=sa.true()))
        lote.add_column(sa.Column('inatividade_dias', sa.Integer(), nullable=False, server_default='60'))
        lote.add_column(sa.Column('inatividade_conferida_em', sa.Date(), nullable=True))
        lote.add_column(sa.Column('lembretes_ligados', sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        'modelos_mensagem',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=30), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], name=op.f('fk_modelos_mensagem_conta_id_contas')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_modelos_mensagem')),
        sa.UniqueConstraint('conta_id', 'tipo', name='uq_modelos_mensagem_conta_id_tipo'),
    )


def downgrade():
    op.drop_table('modelos_mensagem')
    with op.batch_alter_table('contas') as lote:
        for coluna in reversed(COLUNAS):
            lote.drop_column(coluna)
