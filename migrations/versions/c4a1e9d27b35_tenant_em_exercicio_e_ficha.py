"""isolamento por academia em exercicio e ficha, inicio do plano e unicidade por academia

Revision ID: c4a1e9d27b35
Revises: 13fcfff3915e
Create Date: 2026-09-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4a1e9d27b35'
down_revision = '13fcfff3915e'
branch_labels = None
depends_on = None


def _unique_por_coluna(bind, tabela, coluna):
    """Nome real da constraint única de uma coluna (varia entre bancos já criados)."""
    for constraint in sa.inspect(bind).get_unique_constraints(tabela):
        if constraint["column_names"] == [coluna]:
            return constraint["name"]
    return None


def upgrade():
    bind = op.get_bind()

    with op.batch_alter_table('exercicio', schema=None) as batch_op:
        batch_op.add_column(sa.Column('instrutor_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_exercicio_instrutor_id_instrutores'), 'instrutores', ['instrutor_id'], ['id'])

    with op.batch_alter_table('ficha', schema=None) as batch_op:
        batch_op.add_column(sa.Column('instrutor_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_ficha_instrutor_id_instrutores'), 'instrutores', ['instrutor_id'], ['id'])

    with op.batch_alter_table('alunos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data_inicio_plano', sa.Date(), nullable=True))

    # ===== Preenche registros antigos =====
    # Registros sem dono ficam com o primeiro instrutor (base anterior ao multi-tenant)
    primeiro_instrutor = bind.execute(sa.text("SELECT MIN(id) FROM instrutores")).scalar()
    if primeiro_instrutor is not None:
        for tabela in ('alunos', 'planos', 'exercicio'):
            bind.execute(
                sa.text(f"UPDATE {tabela} SET instrutor_id = :instrutor WHERE instrutor_id IS NULL"),
                {"instrutor": primeiro_instrutor},
            )

    bind.execute(sa.text(
        "UPDATE ficha SET instrutor_id = "
        "(SELECT alunos.instrutor_id FROM alunos WHERE alunos.id = ficha.aluno_id) "
        "WHERE instrutor_id IS NULL"
    ))

    data_cadastro = "DATE(data_cadastro)" if bind.dialect.name == "sqlite" else "CAST(data_cadastro AS DATE)"
    bind.execute(sa.text(
        f"UPDATE alunos SET data_inicio_plano = {data_cadastro} "
        "WHERE data_inicio_plano IS NULL AND data_cadastro IS NOT NULL"
    ))

    # ===== E-mail e CPF passam a ser únicos por academia =====
    uq_email = _unique_por_coluna(bind, 'alunos', 'email')
    uq_cpf = _unique_por_coluna(bind, 'alunos', 'cpf')
    with op.batch_alter_table('alunos', schema=None) as batch_op:
        if uq_email:
            batch_op.drop_constraint(uq_email, type_='unique')
        if uq_cpf:
            batch_op.drop_constraint(uq_cpf, type_='unique')
        batch_op.create_unique_constraint('uq_alunos_instrutor_id_email', ['instrutor_id', 'email'])
        batch_op.create_unique_constraint('uq_alunos_instrutor_id_cpf', ['instrutor_id', 'cpf'])

    for tabela in ('alunos', 'planos', 'exercicio', 'ficha'):
        op.create_index(f'ix_{tabela}_instrutor_id', tabela, ['instrutor_id'], unique=False)


def downgrade():
    for tabela in ('ficha', 'exercicio', 'planos', 'alunos'):
        op.drop_index(f'ix_{tabela}_instrutor_id', table_name=tabela)

    with op.batch_alter_table('alunos', schema=None) as batch_op:
        batch_op.drop_constraint('uq_alunos_instrutor_id_cpf', type_='unique')
        batch_op.drop_constraint('uq_alunos_instrutor_id_email', type_='unique')
        batch_op.create_unique_constraint('uq_alunos_email', ['email'])
        batch_op.create_unique_constraint('uq_alunos_cpf', ['cpf'])
        batch_op.drop_column('data_inicio_plano')

    with op.batch_alter_table('ficha', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_ficha_instrutor_id_instrutores'), type_='foreignkey')
        batch_op.drop_column('instrutor_id')

    with op.batch_alter_table('exercicio', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_exercicio_instrutor_id_instrutores'), type_='foreignkey')
        batch_op.drop_column('instrutor_id')
