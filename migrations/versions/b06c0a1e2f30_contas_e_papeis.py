"""contas e papeis: tabela contas, conta_id nas tabelas de negocio, papel do usuario

[back-06-contas-e-papeis] Escrita à mão (não é autogerada), porque além de mudar a estrutura
ela MOVE DADOS: cada usuário que já existe vira dono de uma conta nova, e os alunos, planos e
pagamentos dele passam a apontar para essa conta.

O que faz, na ordem:
  0. Confere que não há aluno nem plano sem dono. Se houver, PARA antes de mexer em qualquer
     coisa e diz quantos são: sem dono, não há como saber de qual academia eles são.
  1. Cria a tabela `contas`.
  2. Cria as colunas novas ainda aceitando vazio (`conta_id` em instrutores, alunos, planos,
     pagamentos e exercicio; `papel` em instrutores).
  3. Para cada usuário existente, cria uma conta e liga os dados dele a ela. Todo usuário
     existente vira `proprietario`. Os exercícios existentes ficam sem conta: viram o
     catálogo padrão, que todas as academias usam e nenhuma edita.
  4. Torna `conta_id` obrigatório (menos em exercicio), cria as chaves estrangeiras e os
     índices, e troca "e-mail e CPF únicos no banco inteiro" por "únicos dentro da conta".

O downgrade desfaz tudo e apaga a tabela `contas`. O que foi configurado na conta (nome da
academia etc.) se perde; alunos, planos e pagamentos continuam, porque `instrutor_id` nunca
foi mexido.

Revision ID: b06c0a1e2f30
Revises: 74c21aa0a5d7
Create Date: 2026-10-10
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b06c0a1e2f30'
down_revision = '74c21aa0a5d7'
branch_labels = None
depends_on = None

# Mesma convenção de nomes de app/extensions/database.py. No SQLite, restrição antiga sem nome
# só pode ser removida se o Alembic souber que nome ela "deveria" ter.
CONVENCAO = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
COM_CONTA_OBRIGATORIA = ('instrutores', 'alunos', 'planos', 'pagamentos')


def _unicos_de_uma_coluna(inspetor, tabela, coluna):
    """Nomes das restrições e dos índices únicos que cobrem SÓ essa coluna (ex.: e-mail único no banco inteiro)."""
    restricoes = [u.get('name') for u in inspetor.get_unique_constraints(tabela) if u['column_names'] == [coluna]]
    indices = [i['name'] for i in inspetor.get_indexes(tabela) if i.get('unique') and i['column_names'] == [coluna]]
    # no Postgres uma restrição única também aparece como índice: não remover duas vezes
    return restricoes, [i for i in indices if i not in restricoes]


def upgrade():
    conexao = op.get_bind()

    # 0) conferência, antes de qualquer mudança
    sem_dono = {t: conexao.execute(sa.text(f"SELECT count(*) FROM {t} WHERE instrutor_id IS NULL")).scalar()
                for t in ('alunos', 'planos')}
    if any(sem_dono.values()):
        raise RuntimeError(
            f"Migration interrompida, nada foi alterado: existem registros sem dono ({sem_dono}). "
            "Atribua um instrutor_id a eles (ou apague-os) e rode de novo.")

    # 1) a tabela de contas
    contas = op.create_table(
        'contas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('razao', sa.String(length=160), nullable=True),
        sa.Column('cnpj', sa.String(length=18), nullable=True),
        sa.Column('telefone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('cidade', sa.String(length=80), nullable=True),
        sa.Column('endereco', sa.String(length=200), nullable=True),
        sa.Column('modelo', sa.String(length=20), server_default='academia', nullable=False),
        sa.Column('checkin_ativo', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('pix_ligado', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_contas')),
    )

    # 2) colunas novas, por enquanto aceitando vazio
    op.add_column('instrutores', sa.Column('papel', sa.String(length=20), server_default='proprietario', nullable=False))
    for tabela in COM_CONTA_OBRIGATORIA + ('exercicio',):
        op.add_column(tabela, sa.Column('conta_id', sa.Integer(), nullable=True))

    # 3) dados: uma conta para cada usuário que já existe
    usuarios = conexao.execute(sa.text("SELECT id, nome, sobrenome, email FROM instrutores ORDER BY id")).fetchall()
    for usuario in usuarios:
        nome_pessoa = ' '.join(p for p in (usuario.nome, usuario.sobrenome) if p).strip() or (usuario.email or f'usuário {usuario.id}')
        nova = conexao.execute(contas.insert().values(nome=f'Academia de {nome_pessoa}'[:120], modelo='academia',
                                                      checkin_ativo=False, pix_ligado=False, criado_em=datetime.utcnow()))
        conexao.execute(sa.text("UPDATE instrutores SET conta_id = :conta WHERE id = :usuario"),
                        {'conta': nova.inserted_primary_key[0], 'usuario': usuario.id})
    for tabela in ('alunos', 'planos', 'pagamentos'):
        conexao.execute(sa.text(
            f"UPDATE {tabela} SET conta_id = (SELECT conta_id FROM instrutores WHERE instrutores.id = {tabela}.instrutor_id)"))
    # exercicio.conta_id fica vazio de propósito: os exercícios existentes viram o catálogo padrão

    # 4) trava a estrutura
    inspetor = sa.inspect(conexao)
    for tabela in COM_CONTA_OBRIGATORIA:
        with op.batch_alter_table(tabela, naming_convention=CONVENCAO) as lote:
            lote.alter_column('conta_id', existing_type=sa.Integer(), nullable=False)
            lote.create_foreign_key(f'fk_{tabela}_conta_id_contas', 'contas', ['conta_id'], ['id'])
            if tabela == 'alunos':
                for coluna in ('email', 'cpf'):
                    restricoes, indices = _unicos_de_uma_coluna(inspetor, 'alunos', coluna)
                    for nome in restricoes:
                        lote.drop_constraint(nome or f'uq_alunos_{coluna}', type_='unique')
                    for nome in indices:
                        lote.drop_index(nome)
                lote.create_unique_constraint('uq_alunos_conta_id_email', ['conta_id', 'email'])
                lote.create_unique_constraint('uq_alunos_conta_id_cpf', ['conta_id', 'cpf'])
    with op.batch_alter_table('exercicio', naming_convention=CONVENCAO) as lote:
        lote.create_foreign_key('fk_exercicio_conta_id_contas', 'contas', ['conta_id'], ['id'])
    for tabela in ('alunos', 'planos', 'pagamentos', 'exercicio'):
        op.create_index(f'ix_{tabela}_conta_id', tabela, ['conta_id'], unique=False)


def downgrade():
    for tabela in ('alunos', 'planos', 'pagamentos', 'exercicio'):
        op.drop_index(f'ix_{tabela}_conta_id', table_name=tabela)
    with op.batch_alter_table('alunos', naming_convention=CONVENCAO) as lote:
        lote.drop_constraint('uq_alunos_conta_id_cpf', type_='unique')
        lote.drop_constraint('uq_alunos_conta_id_email', type_='unique')
        # volta ao que era: e-mail e CPF únicos no banco inteiro. Se, depois do upgrade, duas
        # academias tiverem cadastrado o mesmo e-mail ou CPF, esta linha falha: é preciso
        # resolver as repetições antes de voltar.
        lote.create_unique_constraint('uq_alunos_email', ['email'])
        lote.create_unique_constraint('uq_alunos_cpf', ['cpf'])
    for tabela in COM_CONTA_OBRIGATORIA + ('exercicio',):
        with op.batch_alter_table(tabela, naming_convention=CONVENCAO) as lote:
            lote.drop_constraint(f'fk_{tabela}_conta_id_contas', type_='foreignkey')
            lote.drop_column('conta_id')
    with op.batch_alter_table('instrutores', naming_convention=CONVENCAO) as lote:
        lote.drop_column('papel')
    op.drop_table('contas')
