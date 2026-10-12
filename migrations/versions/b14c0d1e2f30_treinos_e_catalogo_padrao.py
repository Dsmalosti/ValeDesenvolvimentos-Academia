"""treinos: colunas novas em exercicio, ficha, treino e treino_exercicio; catálogo padrão de exercícios

[back-14-treinos] As quatro tabelas já existiam. Esta migration só ACRESCENTA colunas, todas
aceitando vazio (ou com valor padrão), e grava o catálogo padrão de exercícios.

  exercicio          equipamento
  ficha              objetivo, rascunho (padrão não), modelo, valida_ate, atualizada_em, atualizada_por_id
  treino             letra (A a E), nome
  treino_exercicio   descanso, ordem (padrão 0)

Dados:
  - os treinos que já existem ganham a letra pela ordem em que foram criados dentro da ficha
    (o 1º vira A, o 2º vira B...). Do 6º em diante ficam sem letra e não aparecem na tela nova;
    continuam no banco e na tela antiga.
  - as linhas de treino que já existem ganham `ordem` pela ordem em que foram criadas.
  - o catálogo padrão (exercícios sem dono, que toda academia vê) recebe os exercícios do front
    que ainda não existirem com o mesmo nome. Os que já existem não são alterados, a não ser para
    receber o equipamento quando estava vazio.

Downgrade: remove as colunas. Os exercícios acrescentados ao catálogo NÃO são apagados (fichas já
podem estar usando).

Revision ID: b14c0d1e2f30
Revises: b13b9c0d1e20
Create Date: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b14c0d1e2f30'
down_revision = 'b13b9c0d1e20'
branch_labels = None
depends_on = None

LETRAS = 'ABCDE'


def upgrade():
    conexao = op.get_bind()

    with op.batch_alter_table('exercicio') as lote:
        lote.add_column(sa.Column('equipamento', sa.String(length=60), nullable=True))
    with op.batch_alter_table('ficha') as lote:
        lote.add_column(sa.Column('objetivo', sa.String(length=200), nullable=True))
        lote.add_column(sa.Column('rascunho', sa.Boolean(), nullable=False, server_default=sa.false()))
        lote.add_column(sa.Column('modelo', sa.String(length=40), nullable=True))
        lote.add_column(sa.Column('valida_ate', sa.Date(), nullable=True))
        lote.add_column(sa.Column('atualizada_em', sa.DateTime(), nullable=True))
        lote.add_column(sa.Column('atualizada_por_id', sa.Integer(), nullable=True))
        lote.create_foreign_key(op.f('fk_ficha_atualizada_por_id_instrutores'), 'instrutores', ['atualizada_por_id'], ['id'])
    with op.batch_alter_table('treino') as lote:
        lote.add_column(sa.Column('letra', sa.String(length=1), nullable=True))
        lote.add_column(sa.Column('nome', sa.String(length=100), nullable=True))
    with op.batch_alter_table('treino_exercicio') as lote:
        lote.add_column(sa.Column('descanso', sa.String(length=20), nullable=True))
        lote.add_column(sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'))

    # letra dos treinos que já existem: pela ordem de criação dentro de cada ficha
    posicao = {}
    for treino_id, ficha_id in conexao.execute(sa.text("SELECT id, ficha_id FROM treino ORDER BY ficha_id, id")).fetchall():
        n = posicao.get(ficha_id, 0)
        posicao[ficha_id] = n + 1
        if n < len(LETRAS):
            conexao.execute(sa.text("UPDATE treino SET letra = :letra WHERE id = :id"), {'letra': LETRAS[n], 'id': treino_id})

    # ordem das linhas que já existem: pela ordem de criação dentro de cada treino
    posicao = {}
    for linha_id, treino_id in conexao.execute(sa.text("SELECT id, treino_id FROM treino_exercicio ORDER BY treino_id, id")).fetchall():
        n = posicao.get(treino_id, 0)
        posicao[treino_id] = n + 1
        if n:
            conexao.execute(sa.text("UPDATE treino_exercicio SET ordem = :ordem WHERE id = :id"), {'ordem': n, 'id': linha_id})

    # catálogo padrão: só dado (nomes), importado do arquivo que o sistema também usa
    from app.dados_padrao import EXERCICIOS_PADRAO
    existentes = {nome.strip().lower(): (id, equipamento) for id, nome, equipamento in
                  conexao.execute(sa.text("SELECT id, nome, equipamento FROM exercicio WHERE conta_id IS NULL")).fetchall() if nome}
    for nome, grupo, equipamento in EXERCICIOS_PADRAO:
        atual = existentes.get(nome.lower())
        if atual is None:
            conexao.execute(sa.text("INSERT INTO exercicio (nome, grupo_muscular, equipamento, ativo, conta_id) VALUES (:nome, :grupo, :equipamento, true, NULL)"),
                            {'nome': nome, 'grupo': grupo, 'equipamento': equipamento})
        elif not atual[1]:
            conexao.execute(sa.text("UPDATE exercicio SET equipamento = :equipamento WHERE id = :id"), {'equipamento': equipamento, 'id': atual[0]})


def downgrade():
    with op.batch_alter_table('treino_exercicio') as lote:
        lote.drop_column('ordem')
        lote.drop_column('descanso')
    with op.batch_alter_table('treino') as lote:
        lote.drop_column('nome')
        lote.drop_column('letra')
    with op.batch_alter_table('ficha') as lote:
        lote.drop_constraint(op.f('fk_ficha_atualizada_por_id_instrutores'), type_='foreignkey')
        lote.drop_column('atualizada_por_id')
        lote.drop_column('atualizada_em')
        lote.drop_column('valida_ate')
        lote.drop_column('modelo')
        lote.drop_column('rascunho')
        lote.drop_column('objetivo')
    with op.batch_alter_table('exercicio') as lote:
        lote.drop_column('equipamento')
