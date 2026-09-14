from datetime import timedelta
from decimal import Decimal

import pytest

from app.exceptions import BusinessError
from app.extensions.database import db
from app.helpers.date_helper import hoje
from app.models import Aluno, Exercicio, Ficha, Plano, Treino, TreinoExercicio, User
from app.services.aluno_service import AlunoService
from app.services.dashboard_service import obter_dados_dashboard
from app.services.exercicio_service import EXERCICIOS_PADRAO
from app.services.plano_service import PlanoService


@pytest.fixture
def cliente(client, criar_instrutor, logar):
    criar_instrutor()
    logar("ana@academia.com")
    return client


def texto(resposta):
    return resposta.get_data(as_text=True)


def test_fluxo_completo_plano_aluno_exercicio_ficha(app, cliente):
    # 1. plano com valor no formato brasileiro
    resposta = cliente.post("/planos/criar/", data={"nome": "Mensal", "valor": "1.129,90", "duracao_dias": "30", "ativo": "y"})
    assert resposta.status_code == 302
    with app.app_context():
        plano = Plano.query.one()
        assert plano.valor == Decimal("1129.90")
        plano_id = plano.id

    # 2. aluno com CPF e telefone normalizados
    resposta = cliente.post("/alunos/cadastro/", data={
        "nome": "Maria Silva", "email": "Maria@Email.com", "telefone": "11912345678",
        "cpf": "52998224725", "data_nascimento": "1995-05-10", "plano_id": plano_id,
        "data_inicio_plano": hoje().isoformat(), "ativo": "y",
    })
    assert resposta.status_code == 302
    with app.app_context():
        aluno = Aluno.query.one()
        assert (aluno.email, aluno.cpf, aluno.telefone) == ("maria@email.com", "529.982.247-25", "(11) 91234-5678")
        assert aluno.situacao == "em_dia"
        aluno_id = aluno.id
    assert "Maria Silva" in texto(cliente.get("/alunos/"))

    # 3. biblioteca padrão (idempotente)
    cliente.post("/exercicios/importar-padrao/")
    cliente.post("/exercicios/importar-padrao/")
    with app.app_context():
        assert Exercicio.query.count() == len(EXERCICIOS_PADRAO)
        exercicio_id = Exercicio.query.filter_by(nome="Agachamento livre").one().id

    # 4. ficha -> treino -> exercício
    resposta = cliente.post("/fichas/novo/", data={"nome": "Hipertrofia A", "aluno_id": aluno_id, "observacoes": "Foco em pernas", "ativo": "y"})
    assert resposta.status_code == 302
    with app.app_context():
        ficha_id = Ficha.query.one().id

    resposta = cliente.post(f"/fichas/{ficha_id}/treino/novo", data={"dia_semana": "segunda"})
    with app.app_context():
        treino_id = Treino.query.one().id
    assert resposta.headers["Location"].endswith(f"/fichas/treino/{treino_id}/exercicio/adicionar")

    duplicado = cliente.post(f"/fichas/{ficha_id}/treino/novo", data={"dia_semana": "segunda"})
    assert "Esta ficha já tem um treino nesse dia." in texto(duplicado)

    resposta = cliente.post(f"/fichas/treino/{treino_id}/exercicio/adicionar", data={
        "exercicio_id": exercicio_id, "series": "4", "repeticoes": "8-12", "carga": "40 kg", "observacoes": "Descer devagar",
    })
    assert resposta.status_code == 302

    detalhes = texto(cliente.get(f"/fichas/detalhes/{ficha_id}"))
    for trecho in ("Agachamento livre", "8-12", "40 kg", "Descer devagar", "Foco em pernas"):
        assert trecho in detalhes

    # 5. regras de proteção
    cliente.post(f"/planos/excluir/{plano_id}")
    cliente.post(f"/exercicios/excluir/{exercicio_id}")
    with app.app_context():
        assert db.session.get(Plano, plano_id) is not None
        assert db.session.get(Exercicio, exercicio_id) is not None

    # 6. excluir o aluno leva junto fichas, treinos e itens
    cliente.post(f"/alunos/excluir/{aluno_id}")
    with app.app_context():
        assert Aluno.query.count() == 0
        assert Ficha.query.count() == 0
        assert Treino.query.count() == 0
        assert TreinoExercicio.query.count() == 0


def test_formulario_invalido_mostra_erros_acessiveis(cliente):
    resposta = cliente.post("/alunos/cadastro/", data={"nome": "", "email": "invalido", "cpf": "111.111.111-11"})
    html = texto(resposta)
    assert resposta.status_code == 200
    assert 'aria-invalid="true"' in html
    assert "CPF inválido." in html
    assert "E-mail inválido." in html


def test_todas_as_telas_renderizam(app, cliente):
    with app.app_context():
        instrutor_id = User.query.one().id
        plano = PlanoService.criar_plano(instrutor_id, {"nome": "Mensal", "valor": Decimal("99.9"), "duracao_dias": 30})
        aluno = AlunoService.criar_aluno(instrutor_id, {"nome": "João", "email": "joao@x.com", "plano_id": plano.id})
        plano_id, aluno_id = plano.id, aluno.id

    urls = [
        "/", "/alunos/", "/alunos/?situacao=vencido", "/alunos/cadastro/", f"/alunos/editar/{aluno_id}",
        "/planos/", "/planos/criar/", f"/planos/editar/{plano_id}/",
        "/exercicios/", "/exercicios/criar/", "/fichas/", "/fichas/novo/", "/instrutores/conta/",
    ]
    for url in urls:
        assert cliente.get(url).status_code == 200, url

    assert cliente.get("/alunos/editar/999999").status_code == 404


def test_dashboard_calcula_vencimentos_e_receita(app, cliente):
    with app.app_context():
        instrutor_id = User.query.one().id
        referencia = hoje()
        plano = PlanoService.criar_plano(instrutor_id, {"nome": "Mensal", "valor": Decimal("150"), "duracao_dias": 30})

        def criar(nome, dias_atras, ativo=True):
            AlunoService.criar_aluno(instrutor_id, {
                "nome": nome, "email": f"{nome.split()[0].lower()}@x.com", "plano_id": plano.id,
                "data_inicio_plano": referencia - timedelta(days=dias_atras), "ativo": ativo,
            })

        criar("Em Dia", 0)
        criar("Quase Vencendo", 27)
        criar("Ja Venceu", 40)
        criar("Inativo Total", 0, ativo=False)

        dados = obter_dados_dashboard(instrutor_id)
        assert dados["ativos"] == 3
        assert [a.nome for a in dados["a_vencer"]] == ["Quase Vencendo"]
        assert [a.nome for a in dados["vencidos"]] == ["Ja Venceu"]
        assert dados["receita_mensal"] == Decimal("300.00")

    html = texto(cliente.get("/"))
    assert "R$ 300,00" in html
    assert "Quase Vencendo" in html


def test_renovacao_antecipada_nao_perde_dias(app, criar_instrutor):
    instrutor_id = criar_instrutor()
    with app.app_context():
        referencia = hoje()
        plano = PlanoService.criar_plano(instrutor_id, {"nome": "Mensal", "valor": Decimal("100"), "duracao_dias": 30})

        antecipado = AlunoService.criar_aluno(instrutor_id, {"nome": "A", "email": "a@x.com", "plano_id": plano.id, "data_inicio_plano": referencia - timedelta(days=27)})
        AlunoService.renovar_plano(antecipado)
        assert antecipado.data_vencimento == referencia + timedelta(days=33)

        vencido = AlunoService.criar_aluno(instrutor_id, {"nome": "B", "email": "b@x.com", "plano_id": plano.id, "data_inicio_plano": referencia - timedelta(days=40)})
        AlunoService.renovar_plano(vencido)
        assert vencido.data_vencimento == referencia + timedelta(days=30)


def test_nao_aceita_nascimento_no_futuro(app, criar_instrutor):
    instrutor_id = criar_instrutor()
    with app.app_context():
        plano = PlanoService.criar_plano(instrutor_id, {"nome": "Mensal", "valor": Decimal("100"), "duracao_dias": 30})
        with pytest.raises(BusinessError):
            AlunoService.criar_aluno(instrutor_id, {
                "nome": "Futuro", "email": "f@x.com", "plano_id": plano.id,
                "data_nascimento": hoje() + timedelta(days=1),
            })
