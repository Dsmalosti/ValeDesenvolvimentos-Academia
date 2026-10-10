from app.models import Aluno
from app.helpers.conta import da_conta
from app.helpers.date_helper import is_aniversariante

def obter_dados_dashboard():
    # [back-03-isolamento] antes: Aluno.query.all(). O painel contava os alunos e os
    # aniversariantes de TODAS as academias.
    alunos = da_conta(Aluno).all()

    # [back-02-limpeza] antes: a.ativo == 'ativo'. A coluna é True/False, nunca o texto 'ativo',
    # então a contagem de alunos ativos do painel dava sempre zero.
    ativos = sum(1 for a in alunos if a.ativo)
    aniversariantes = sum(1 for a in alunos if is_aniversariante(a.data_nascimento))

    return {
        "ativos": ativos,
        "aniversariantes": aniversariantes
    }
