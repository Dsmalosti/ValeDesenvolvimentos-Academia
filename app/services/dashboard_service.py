from app.models import Aluno
from app.helpers.date_helper import is_aniversariante

def obter_dados_dashboard():
    alunos = Aluno.query.all()

    ativos = sum(1 for a in alunos if a.ativo)
    aniversariantes = sum(1 for a in alunos if is_aniversariante(a.data_nascimento))

    return {
        "ativos": ativos,
        "aniversariantes": aniversariantes
    }
