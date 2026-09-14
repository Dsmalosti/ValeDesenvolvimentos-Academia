from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import joinedload

from app.models import Aluno, Exercicio, Ficha, Plano
from app.helpers.date_helper import dias_ate_aniversario, hoje, is_aniversariante

JANELA_ANIVERSARIOS_DIAS = 30


def obter_dados_dashboard(instrutor_id):
    alunos = (
        Aluno.query.options(joinedload(Aluno.plano))
        .filter(Aluno.instrutor_id == instrutor_id)
        .all()
    )
    referencia = hoje()
    ativos = [a for a in alunos if a.ativo]

    vencidos = sorted(
        (a for a in ativos if a.situacao == "vencido"), key=lambda a: a.data_vencimento
    )
    a_vencer = sorted(
        (a for a in ativos if a.situacao == "a_vencer"), key=lambda a: a.data_vencimento
    )

    proximos_aniversarios = sorted(
        (
            (dias_ate_aniversario(a.data_nascimento, referencia), a)
            for a in ativos
            if a.data_nascimento
        ),
        key=lambda par: par[0],
    )
    proximos_aniversarios = [
        par for par in proximos_aniversarios if par[0] <= JANELA_ANIVERSARIOS_DIAS
    ][:5]

    # Receita recorrente: só conta quem está com o plano em dia
    receita_mensal = sum(
        (a.plano.valor_mensal for a in ativos if a.plano and a.situacao in ("em_dia", "a_vencer")),
        Decimal("0"),
    )

    recentes = sorted(
        alunos, key=lambda a: a.data_cadastro or datetime.min, reverse=True
    )[:5]

    onboarding = _checklist_onboarding(instrutor_id, total_alunos=len(alunos))

    return {
        "total_alunos": len(alunos),
        "ativos": len(ativos),
        "vencidos": vencidos,
        "a_vencer": a_vencer,
        "aniversariantes": sum(1 for a in ativos if is_aniversariante(a.data_nascimento, referencia)),
        "proximos_aniversarios": proximos_aniversarios,
        "receita_mensal": receita_mensal,
        "recentes": recentes,
        "onboarding": onboarding,
        "onboarding_concluidos": sum(1 for passo in onboarding if passo["feito"]),
    }


def _checklist_onboarding(instrutor_id, total_alunos):
    tem_plano = Plano.query.filter_by(instrutor_id=instrutor_id).first() is not None
    tem_exercicio = Exercicio.query.filter_by(instrutor_id=instrutor_id).first() is not None
    tem_ficha = Ficha.query.filter_by(instrutor_id=instrutor_id).first() is not None

    return [
        {
            "titulo": "Crie seu primeiro plano",
            "descricao": "Defina valor e duração das matrículas.",
            "feito": tem_plano,
            "endpoint": "planos.criarPlano",
            "acao": "Criar plano",
        },
        {
            "titulo": "Cadastre um aluno",
            "descricao": "Vincule o aluno a um plano para acompanhar o vencimento.",
            "feito": total_alunos > 0,
            "endpoint": "alunos.cadastroAluno",
            "acao": "Cadastrar aluno",
        },
        {
            "titulo": "Monte sua biblioteca de exercícios",
            "descricao": "Importe 26 exercícios prontos ou cadastre os seus.",
            "feito": tem_exercicio,
            "endpoint": "exercicios.listarExercicios",
            "acao": "Ver exercícios",
        },
        {
            "titulo": "Crie a primeira ficha de treino",
            "descricao": "Organize os treinos do aluno por dia da semana.",
            "feito": tem_ficha,
            "endpoint": "fichas.criarFicha",
            "acao": "Criar ficha",
        },
    ]
