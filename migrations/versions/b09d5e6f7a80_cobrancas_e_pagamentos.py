"""cobrança: tabela nova `cobrancas` e a `pagamentos` em outro formato

[back-09-cobranca] Esquema aprovado pelo Diogo (PR #22, as 6 perguntas). Escrita à mão.

O que era: uma tabela só, `pagamentos`, com aluno_id, instrutor_id, valor, data_pagamento (só a
data), data_vencimento, forma_pagamento e observacao. Cada linha era "o aluno pagou tanto e por
isso está em dia até tal data".

O que fica:
  - `cobrancas` (nova): o que se deve. Aluno, plano da época, tipo, valor congelado, período
    (data_inicio a data_vencimento) e status.
  - `pagamentos`: o que entrou. Aponta para a cobrança e guarda forma, valor_pago, dia e hora,
    origem da confirmação e quem confirmou.

Upgrade, passo a passo:
  1. cria `cobrancas`;
  2. acrescenta as colunas novas em `pagamentos`, ainda aceitando vazio;
  3. para CADA pagamento antigo cria uma cobrança `paga` (mesmo aluno, conta, valor e vencimento;
     plano = o plano atual do aluno; tipo = matrícula no primeiro pagamento do aluno e renovação
     nos seguintes) e liga o pagamento a ela;
  4. troca data_pagamento de data para data e hora (os antigos ficam com 00:00);
  5. torna obrigatórias as colunas novas e remove as antigas.

Downgrade: devolve as colunas antigas a partir da cobrança e apaga `cobrancas`.
ATENÇÃO, perde dado: cobranças em aberto deixam de existir, e pagamento de diária avulsa (sem
aluno) é apagado, porque o formato antigo exigia aluno.

Revision ID: b09d5e6f7a80
Revises: b08c3d4e5f60
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b09d5e6f7a80'
down_revision = 'b08c3d4e5f60'
branch_labels = None
depends_on = None


def upgrade():
    conexao = op.get_bind()

    # 1. a tabela de cobranças
    op.create_table(
        'cobrancas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conta_id', sa.Integer(), nullable=False),
        sa.Column('aluno_id', sa.Integer(), nullable=True),
        sa.Column('plano_id', sa.Integer(), nullable=True),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('nome_visitante', sa.String(length=100), nullable=True),
        sa.Column('valor', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('data_inicio', sa.Date(), nullable=False),
        sa.Column('data_vencimento', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('data_geracao', sa.DateTime(), nullable=False),
        sa.Column('instrutor_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['conta_id'], ['contas.id'], name=op.f('fk_cobrancas_conta_id_contas')),
        sa.ForeignKeyConstraint(['aluno_id'], ['alunos.id'], name=op.f('fk_cobrancas_aluno_id_alunos')),
        sa.ForeignKeyConstraint(['plano_id'], ['planos.id'], name=op.f('fk_cobrancas_plano_id_planos')),
        sa.ForeignKeyConstraint(['instrutor_id'], ['instrutores.id'], name=op.f('fk_cobrancas_instrutor_id_instrutores')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_cobrancas')),
    )
    op.create_index('ix_cobrancas_conta_status_vencimento', 'cobrancas', ['conta_id', 'status', 'data_vencimento'])

    # 2. colunas novas do pagamento, por enquanto aceitando vazio
    with op.batch_alter_table('pagamentos') as lote:
        lote.add_column(sa.Column('cobranca_id', sa.Integer(), nullable=True))
        lote.add_column(sa.Column('forma', sa.String(length=20), nullable=True))
        lote.add_column(sa.Column('valor_pago', sa.Numeric(precision=10, scale=2), nullable=True))
        lote.add_column(sa.Column('origem_confirmacao', sa.String(length=20), nullable=True))
        lote.add_column(sa.Column('confirmado_por_instrutor_id', sa.Integer(), nullable=True))
        lote.add_column(sa.Column('referencia_externa', sa.String(length=100), nullable=True))

    # 3. uma cobrança paga para cada pagamento antigo
    antigos = conexao.execute(sa.text(
        "SELECT p.id, p.aluno_id, p.instrutor_id, p.conta_id, p.valor, p.data_pagamento, p.data_vencimento, a.plano_id "
        "FROM pagamentos p JOIN alunos a ON a.id = p.aluno_id ORDER BY p.aluno_id, p.data_pagamento, p.id")).fetchall()
    ja_pagou = set()
    for linha in antigos:
        tipo = 'renovacao' if linha.aluno_id in ja_pagou else 'matricula'
        ja_pagou.add(linha.aluno_id)
        cobranca_id = conexao.execute(sa.text(
            "INSERT INTO cobrancas (conta_id, aluno_id, plano_id, tipo, valor, data_inicio, data_vencimento, status, data_geracao, instrutor_id) "
            "VALUES (:conta, :aluno, :plano, :tipo, :valor, :inicio, :vencimento, 'paga', :gerada, :instrutor) RETURNING id"),
            {'conta': linha.conta_id, 'aluno': linha.aluno_id, 'plano': linha.plano_id, 'tipo': tipo, 'valor': linha.valor,
             'inicio': linha.data_pagamento, 'vencimento': linha.data_vencimento, 'gerada': linha.data_pagamento,
             'instrutor': linha.instrutor_id}).scalar()
        conexao.execute(sa.text("UPDATE pagamentos SET cobranca_id = :cobranca WHERE id = :id"), {'cobranca': cobranca_id, 'id': linha.id})
    # a forma antiga ('dinheiro', 'pix', 'cartao') é mantida como estava; vazia vira 'nao_informada'
    conexao.execute(sa.text(
        "UPDATE pagamentos SET forma = COALESCE(NULLIF(forma_pagamento, ''), 'nao_informada'), valor_pago = valor, "
        "origem_confirmacao = 'manual', confirmado_por_instrutor_id = instrutor_id"))

    # 4 e 5. data com hora, colunas novas obrigatórias, colunas antigas fora
    with op.batch_alter_table('pagamentos') as lote:
        lote.alter_column('data_pagamento', existing_type=sa.Date(), type_=sa.DateTime(), existing_nullable=False,
                          postgresql_using='data_pagamento::timestamp')
        lote.alter_column('cobranca_id', existing_type=sa.Integer(), nullable=False)
        lote.alter_column('forma', existing_type=sa.String(length=20), nullable=False)
        lote.alter_column('valor_pago', existing_type=sa.Numeric(precision=10, scale=2), nullable=False)
        lote.alter_column('origem_confirmacao', existing_type=sa.String(length=20), nullable=False)
        lote.create_foreign_key(op.f('fk_pagamentos_cobranca_id_cobrancas'), 'cobrancas', ['cobranca_id'], ['id'])
        lote.create_foreign_key(op.f('fk_pagamentos_confirmado_por_instrutor_id_instrutores'), 'instrutores',
                                ['confirmado_por_instrutor_id'], ['id'])
        lote.create_index(op.f('ix_pagamentos_cobranca_id'), ['cobranca_id'])
        # as chaves estrangeiras de aluno_id e instrutor_id saem junto com as colunas
        lote.drop_column('aluno_id')
        lote.drop_column('instrutor_id')
        lote.drop_column('valor')
        lote.drop_column('data_vencimento')
        lote.drop_column('forma_pagamento')


def downgrade():
    conexao = op.get_bind()

    with op.batch_alter_table('pagamentos') as lote:
        lote.add_column(sa.Column('aluno_id', sa.Integer(), nullable=True))
        lote.add_column(sa.Column('instrutor_id', sa.Integer(), nullable=True))
        lote.add_column(sa.Column('valor', sa.Numeric(precision=10, scale=2), nullable=True))
        lote.add_column(sa.Column('data_vencimento', sa.Date(), nullable=True))
        lote.add_column(sa.Column('forma_pagamento', sa.String(length=20), nullable=True))

    conexao.execute(sa.text(
        "UPDATE pagamentos SET aluno_id = c.aluno_id, instrutor_id = COALESCE(pagamentos.confirmado_por_instrutor_id, c.instrutor_id), "
        "valor = pagamentos.valor_pago, data_vencimento = COALESCE(c.data_vencimento, c.data_inicio), "
        "forma_pagamento = NULLIF(pagamentos.forma, 'nao_informada') "
        "FROM cobrancas c WHERE c.id = pagamentos.cobranca_id"))
    # o formato antigo exige aluno e quem registrou: o que não tiver (diária avulsa) não tem como voltar
    conexao.execute(sa.text("DELETE FROM pagamentos WHERE aluno_id IS NULL OR instrutor_id IS NULL"))

    with op.batch_alter_table('pagamentos') as lote:
        lote.alter_column('data_pagamento', existing_type=sa.DateTime(), type_=sa.Date(), existing_nullable=False,
                          postgresql_using='data_pagamento::date')
        lote.alter_column('aluno_id', existing_type=sa.Integer(), nullable=False)
        lote.alter_column('instrutor_id', existing_type=sa.Integer(), nullable=False)
        lote.alter_column('valor', existing_type=sa.Numeric(precision=10, scale=2), nullable=False)
        lote.alter_column('data_vencimento', existing_type=sa.Date(), nullable=False)
        lote.create_foreign_key(op.f('fk_pagamentos_aluno_id_alunos'), 'alunos', ['aluno_id'], ['id'])
        lote.create_foreign_key(op.f('fk_pagamentos_instrutor_id_instrutores'), 'instrutores', ['instrutor_id'], ['id'])
        lote.drop_index(op.f('ix_pagamentos_cobranca_id'))
        lote.drop_constraint(op.f('fk_pagamentos_cobranca_id_cobrancas'), type_='foreignkey')
        lote.drop_constraint(op.f('fk_pagamentos_confirmado_por_instrutor_id_instrutores'), type_='foreignkey')
        lote.drop_column('cobranca_id')
        lote.drop_column('forma')
        lote.drop_column('valor_pago')
        lote.drop_column('origem_confirmacao')
        lote.drop_column('confirmado_por_instrutor_id')
        lote.drop_column('referencia_externa')

    op.drop_index('ix_cobrancas_conta_status_vencimento', table_name='cobrancas')
    op.drop_table('cobrancas')
