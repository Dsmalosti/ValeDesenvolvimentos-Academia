"""
Testes da branch back-06-contas-e-papeis: conta (academia) separada de usuário, papéis,
exercício com dono, e-mail e CPF únicos por conta, cadastro aberto fechado e `flask criar-conta`.

[back-27-telas-antigas] Estes testes usavam as TELAS ANTIGAS (/alunos/listar/, /instrutores/..., /fichas/..., /exercicios/criar/...),
que saíram. Os de papéis e de isolamento passaram para as telas novas; os da gestão da equipe antiga e do exercício
antigo saíram, porque as telas novas já têm os seus (tests/test_equipe.py, tests/test_treinos.py,
tests/test_alunos.py: e-mail e CPF por academia, catálogo e exercício de outra academia, convite, papel e remoção).
"""
from datetime import date
import pytest

from app.cli import criar_conta_com_dono
from app.extensions.database import db
from app.models import Aluno, Conta, Exercicio, User
from tests.conftest import (campo, conta_de, contar, criar_aluno, criar_exercicio, criar_pagamento,
                            criar_plano, criar_usuario, logar)


@pytest.fixture()
def equipe(app):
    """Uma academia com dono, recepção e instrutor, um plano e um aluno. Devolve os ids."""
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    recepcao = criar_usuario("recepcao@teste.local", nome="Rita", conta=conta, papel="recepcao")
    instrutor = criar_usuario("instrutor@teste.local", nome="Igor", conta=conta, papel="instrutor")
    plano = criar_plano(dono)
    aluno = criar_aluno(dono, plano, "Ana Souza", "ana@exemplo.com", "111")
    return {"conta": conta, "dono": dono, "recepcao": recepcao, "instrutor": instrutor, "plano": plano, "aluno": aluno}


def entrar_como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


# ------------------------------------------------------------------ a equipe vê os mesmos dados
@pytest.mark.parametrize("quem", ["dono", "recepcao", "instrutor"])
def test_toda_a_equipe_ve_os_alunos_da_academia(app, equipe, quem):
    pagina = entrar_como(app, equipe[quem]).get("/alunos")
    assert pagina.status_code == 200 and "Ana Souza" in pagina.get_data(as_text=True)


def test_outra_academia_continua_sem_ver_nada(app, equipe):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    html = entrar_como(app, outro).get("/alunos").get_data(as_text=True)
    assert "Ana Souza" not in html
    assert entrar_como(app, outro).get(f"/alunos/{equipe['aluno']}/editar").status_code == 404


# ------------------------------------------------------------------ papéis
# [back-27-telas-antigas] antes: as rotas das telas antigas. Agora as equivalentes das telas novas.
INSTRUTOR_NAO_PODE = [
    ("GET", "/alunos/novo"), ("POST", "/alunos/novo"), ("GET", "/alunos/1/editar"),
    ("POST", "/alunos/1/excluir"), ("POST", "/alunos/1/inativar"),
    ("GET", "/planos/novo"), ("GET", "/planos/1/editar"), ("POST", "/planos/1/alternar"),
    ("GET", "/relatorios"), ("GET", "/relatorios/painel"), ("POST", "/cobrancas/diaria"),
]


@pytest.mark.parametrize("metodo, url", INSTRUTOR_NAO_PODE)
def test_instrutor_recebe_403_no_que_nao_e_dele(app, equipe, metodo, url):
    resposta = entrar_como(app, equipe["instrutor"]).open(url, method=metodo)
    assert resposta.status_code == 403, f"{metodo} {url} respondeu {resposta.status_code}"


@pytest.mark.parametrize("url", ["/alunos", "/planos", "/treinos", "/exercicios", "/exercicios/novo", "/configuracoes"])   # [back-27-telas-antigas] antes: as telas antigas
def test_instrutor_entra_no_que_e_dele(app, equipe, url):
    assert entrar_como(app, equipe["instrutor"]).get(url).status_code == 200


@pytest.mark.parametrize("metodo, url", [m for m in INSTRUTOR_NAO_PODE if "excluir" not in m[1]])
def test_recepcao_pode_o_que_o_instrutor_nao_pode(app, equipe, metodo, url):
    resposta = entrar_como(app, equipe["recepcao"]).open(url, method=metodo)
    assert resposta.status_code != 403, f"{metodo} {url} barrou a recepção"


def test_so_o_dono_exclui_aluno(app, equipe):
    assert entrar_como(app, equipe["recepcao"]).post(f"/alunos/{equipe['aluno']}/excluir").status_code == 403
    assert contar(Aluno, id=equipe["aluno"]) == 1
    assert entrar_como(app, equipe["dono"]).post(f"/alunos/{equipe['aluno']}/excluir").status_code == 302
    assert contar(Aluno, id=equipe["aluno"]) == 0


def test_instrutor_nao_ve_os_numeros_do_painel(app, equipe):
    criar_pagamento(equipe["dono"], equipe["aluno"], 432, __import__("datetime").date.today(), __import__("datetime").date.today())

    do_instrutor = entrar_como(app, equipe["instrutor"]).get("/").get_data(as_text=True)
    do_dono = entrar_como(app, equipe["dono"]).get("/").get_data(as_text=True)

    assert "Painel do instrutor" in do_instrutor and "432" not in do_instrutor and "Faturamento" not in do_instrutor
    assert "432" in do_dono


# ------------------------------------------------------------------ cadastro aberto fechado
def test_cadastro_aberto_pela_internet_esta_fechado(cliente):     # [back-27-telas-antigas] a rota saiu de vez; continua respondendo 404
    dados = {"nome": "Invasor", "sobrenome": "X", "email": "invasor@exemplo.com", "senha": "abc12345", "confirmacao_senha": "abc12345"}
    assert cliente.get("/instrutores/cadastro/").status_code == 404
    assert cliente.post("/instrutores/cadastro/", data=dados).status_code == 404
    assert contar(User) == 0 and contar(Conta) == 0


# ------------------------------------------------------------------ nome da academia e papel na tela
def test_painel_mostra_o_nome_da_academia_e_o_papel(app, equipe):
    html = entrar_como(app, equipe["dono"]).get("/").get_data(as_text=True)
    assert "Academia de Diana" in html and "Minha academia" not in html
    assert "Diana Teste · proprietário" in html
    assert "Rita Teste · recepção" in entrar_como(app, equipe["recepcao"]).get("/").get_data(as_text=True)


# ------------------------------------------------------------------ flask criar-conta
def test_criar_conta_com_dono(app):
    with app.app_context():
        usuario = criar_conta_com_dono("Studio Forte", "Lia", "Prado", "  Lia@Exemplo.com ", "senha-de-teste")
        assert usuario.papel == "proprietario" and usuario.email == "lia@exemplo.com"
        assert db.session.get(Conta, usuario.conta_id).nome == "Studio Forte"
        with pytest.raises(ValueError, match="Já existe"):
            criar_conta_com_dono("Outra", "Lia", "Prado", "lia@exemplo.com", "senha-de-teste")
    assert contar(Conta) == 1


def test_comando_flask_criar_conta_e_login(app):
    resultado = app.test_cli_runner().invoke(args=["criar-conta"], input="Studio Forte\nLia\nPrado\nlia@exemplo.com\nsenha-de-teste\nsenha-de-teste\n")
    assert resultado.exit_code == 0 and "Conta \"Studio Forte\" criada" in resultado.output
    assert "senha-de-teste" not in resultado.output               # a senha não é mostrada

    cliente = app.test_client()
    resposta = cliente.post("/login", data={"identificador": "lia@exemplo.com", "senha": "senha-de-teste"})
    assert resposta.status_code == 302 and resposta.headers["Location"] == "/"
    assert "Studio Forte" in cliente.get("/").get_data(as_text=True)
