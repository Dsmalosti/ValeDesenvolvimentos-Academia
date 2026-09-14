"""Garante que uma academia nunca enxerga nem altera dados de outra."""
from decimal import Decimal

import pytest

from app.exceptions import BusinessError
from app.extensions.database import db
from app.models import Aluno, Ficha, Plano
from app.services.aluno_service import AlunoService
from app.services.exercicio_service import ExercicioService
from app.services.ficha_service import FichaService
from app.services.plano_service import PlanoService


def _montar_academia(instrutor_id, sufixo):
    plano = PlanoService.criar_plano(instrutor_id, {"nome": f"Mensal {sufixo}", "valor": Decimal("100"), "duracao_dias": 30})
    aluno = AlunoService.criar_aluno(instrutor_id, {"nome": f"Aluno Secreto {sufixo}", "email": f"secreto@{sufixo}.com", "plano_id": plano.id})
    exercicio = ExercicioService.criar_exercicio(instrutor_id, {"nome": f"Supino {sufixo}", "grupo_muscular": "peito"})
    ficha = FichaService.criar_ficha(instrutor_id, {"nome": f"Ficha {sufixo}", "aluno_id": aluno.id})
    treino = FichaService.adicionar_treino(ficha, "segunda")
    item = FichaService.adicionar_exercicio(treino, {"exercicio_id": exercicio.id, "series": 3, "repeticoes": "12"})
    return {
        "plano_id": plano.id, "aluno_id": aluno.id, "exercicio_id": exercicio.id,
        "ficha_id": ficha.id, "treino_id": treino.id, "item_id": item.id,
    }


@pytest.fixture
def academia_a(app, criar_instrutor):
    instrutor_id = criar_instrutor(email="ana@academia.com", nome="Ana")
    with app.app_context():
        dados = _montar_academia(instrutor_id, "A")
    dados["instrutor_id"] = instrutor_id
    return dados


@pytest.fixture
def cliente_b(client, criar_instrutor, logar):
    criar_instrutor(email="bruno@outra.com", nome="Bruno")
    logar("bruno@outra.com")
    return client


@pytest.mark.parametrize("metodo,url", [
    ("get", "/alunos/editar/{aluno_id}"),
    ("post", "/alunos/excluir/{aluno_id}"),
    ("post", "/alunos/{aluno_id}/renovar"),
    ("get", "/planos/editar/{plano_id}/"),
    ("post", "/planos/excluir/{plano_id}"),
    ("get", "/exercicios/editar/{exercicio_id}"),
    ("post", "/exercicios/excluir/{exercicio_id}"),
    ("get", "/fichas/?aluno_id={aluno_id}"),
    ("get", "/fichas/detalhes/{ficha_id}"),
    ("get", "/fichas/editar/{ficha_id}"),
    ("post", "/fichas/excluir/{ficha_id}"),
    ("get", "/fichas/{ficha_id}/treino/novo"),
    ("get", "/fichas/treino/{treino_id}/editar"),
    ("post", "/fichas/treino/{treino_id}/excluir"),
    ("get", "/fichas/treino/{treino_id}/exercicio/adicionar"),
    ("post", "/fichas/treino/exercicio/{item_id}/remover"),
])
def test_outra_academia_recebe_404(academia_a, cliente_b, metodo, url):
    resposta = getattr(cliente_b, metodo)(url.format(**academia_a))
    assert resposta.status_code == 404


@pytest.mark.parametrize("url", ["/", "/alunos/", "/alunos/?q=Secreto", "/planos/", "/exercicios/", "/fichas/"])
def test_listagens_nao_mostram_dados_de_outra_academia(academia_a, cliente_b, url):
    html = cliente_b.get(url).get_data(as_text=True)
    for nome in ("Aluno Secreto A", "Mensal A", "Supino A", "Ficha A"):
        assert nome not in html


def test_exclusao_em_massa_ignora_alunos_de_outra_academia(app, academia_a, cliente_b):
    resposta = cliente_b.post("/alunos/excluir-varios/", data={"selecionados": [str(academia_a["aluno_id"])]})
    assert resposta.status_code == 302
    with app.app_context():
        assert db.session.get(Aluno, academia_a["aluno_id"]) is not None


def test_nao_cadastra_aluno_com_plano_de_outra_academia(app, academia_a, cliente_b):
    cliente_b.post("/alunos/cadastro/", data={
        "nome": "Invasor", "email": "invasor@b.com", "plano_id": academia_a["plano_id"],
        "data_inicio_plano": "2026-09-01", "ativo": "y",
    })
    with app.app_context():
        assert Aluno.query.filter_by(nome="Invasor").first() is None


def test_nao_cria_ficha_para_aluno_de_outra_academia(app, academia_a, cliente_b):
    cliente_b.post("/fichas/novo/", data={"nome": "Ficha invasora", "aluno_id": academia_a["aluno_id"], "ativo": "y"})
    with app.app_context():
        assert Ficha.query.filter_by(nome="Ficha invasora").first() is None


def test_servicos_recusam_referencias_de_outra_academia(app, academia_a, criar_instrutor):
    instrutor_b = criar_instrutor(email="bruno@outra.com", nome="Bruno")
    with app.app_context():
        dados_b = _montar_academia(instrutor_b, "B")
        treino_b = db.session.get(Ficha, dados_b["ficha_id"]).treinos[0]

        with pytest.raises(BusinessError):
            FichaService.adicionar_exercicio(treino_b, {"exercicio_id": academia_a["exercicio_id"], "series": 3, "repeticoes": "10"})
        with pytest.raises(BusinessError):
            FichaService.criar_ficha(instrutor_b, {"nome": "X", "aluno_id": academia_a["aluno_id"]})
        with pytest.raises(BusinessError):
            AlunoService.criar_aluno(instrutor_b, {"nome": "X", "email": "x@b.com", "plano_id": academia_a["plano_id"]})

        assert AlunoService.excluir_varios(instrutor_b, [academia_a["aluno_id"]]) == 0


def test_mesmo_email_de_aluno_permitido_em_academias_diferentes(app, academia_a, criar_instrutor):
    instrutor_b = criar_instrutor(email="bruno@outra.com", nome="Bruno")
    with app.app_context():
        plano = PlanoService.criar_plano(instrutor_b, {"nome": "Mensal", "valor": Decimal("90"), "duracao_dias": 30})
        aluno = AlunoService.criar_aluno(instrutor_b, {"nome": "Mesmo Email", "email": "secreto@a.com", "plano_id": plano.id})
        assert aluno.id is not None

        with pytest.raises(BusinessError, match="e-mail"):
            AlunoService.criar_aluno(instrutor_b, {"nome": "Duplicado", "email": "SECRETO@a.com", "plano_id": plano.id})

        assert Plano.query.count() == 2
