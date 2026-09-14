import pytest

from conftest import SENHA


def texto(resposta):
    return resposta.get_data(as_text=True)


def test_cadastro_cria_conta_loga_e_mostra_primeiros_passos(client):
    resposta = client.post("/instrutores/cadastro/", data={
        "nome": "Carla", "sobrenome": "Souza", "email": "Carla@Academia.com", "senha": "senha-forte-1",
    })
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/"

    painel = client.get("/")
    assert painel.status_code == 200
    assert "Primeiros passos" in texto(painel)


def test_cadastro_recusa_email_duplicado_ignorando_maiusculas(client, criar_instrutor):
    criar_instrutor(email="ana@academia.com")
    resposta = client.post("/instrutores/cadastro/", data={
        "nome": "Outra", "email": "ANA@academia.com", "senha": "senha-forte-1",
    })
    assert resposta.status_code == 200
    assert "Já existe uma conta com este e-mail." in texto(resposta)


def test_cadastro_exige_senha_com_8_caracteres(client):
    resposta = client.post("/instrutores/cadastro/", data={
        "nome": "Carla", "email": "carla@academia.com", "senha": "curta",
    })
    assert resposta.status_code == 200
    assert "Use pelo menos 8 caracteres." in texto(resposta)


def test_login_com_senha_errada_nao_revela_se_email_existe(client, criar_instrutor, logar):
    criar_instrutor()
    senha_errada = logar("ana@academia.com", "senha-errada-1")
    email_inexistente = logar("ninguem@academia.com", "senha-errada-1")
    assert "E-mail ou senha inválidos." in texto(senha_errada)
    assert "E-mail ou senha inválidos." in texto(email_inexistente)


def test_login_ignora_next_externo(client, criar_instrutor):
    criar_instrutor()
    resposta = client.post("/instrutores/login/?next=https://site-malicioso.com", data={
        "email": "ana@academia.com", "senha": SENHA,
    })
    assert resposta.headers["Location"] == "/"


def test_login_respeita_next_interno(client, criar_instrutor):
    criar_instrutor()
    resposta = client.post("/instrutores/login/?next=/planos/", data={
        "email": "ana@academia.com", "senha": SENHA,
    })
    assert resposta.headers["Location"] == "/planos/"


def test_conta_desativada_nao_entra(client, criar_instrutor, logar):
    criar_instrutor(ativo=False)
    resposta = logar("ana@academia.com")
    assert resposta.status_code == 200
    assert "Esta conta está desativada" in texto(resposta)


@pytest.mark.parametrize("url", ["/", "/alunos/", "/planos/", "/exercicios/", "/fichas/", "/instrutores/conta/"])
def test_rotas_exigem_login(client, url):
    resposta = client.get(url)
    assert resposta.status_code == 302
    assert "/instrutores/login/" in resposta.headers["Location"]


def test_logout_so_por_post(client, criar_instrutor, logar):
    criar_instrutor()
    logar("ana@academia.com")

    assert client.get("/instrutores/sair/").status_code == 405
    assert client.post("/instrutores/sair/").status_code == 302
    assert client.get("/").status_code == 302


def test_trocar_senha_exige_senha_atual(client, criar_instrutor, logar):
    criar_instrutor()
    logar("ana@academia.com")

    dados = {"nome": "Ana", "email": "ana@academia.com", "nova_senha": "nova-senha-123"}
    errada = client.post("/instrutores/conta/", data={**dados, "senha_atual": "senha-errada-0"})
    assert "Senha atual incorreta." in texto(errada)

    certa = client.post("/instrutores/conta/", data={**dados, "senha_atual": SENHA})
    assert certa.status_code == 302

    client.post("/instrutores/sair/")
    assert logar("ana@academia.com", "nova-senha-123").status_code == 302


def test_cabecalhos_de_seguranca(client):
    resposta = client.get("/instrutores/login/")
    assert "Content-Security-Policy" in resposta.headers
    assert resposta.headers["X-Frame-Options"] == "DENY"
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"


def test_healthcheck(client):
    resposta = client.get("/saude")
    assert resposta.status_code == 200
    assert resposta.get_json() == {"status": "ok"}
