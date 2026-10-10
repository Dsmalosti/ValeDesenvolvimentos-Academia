"""Testes do login novo (blueprint auth, branch back-01-auth-login). Aqui o CSRF fica LIGADO."""
import re

import pytest

from tests.conftest import SENHA_TESTE, criar_usuario


@pytest.fixture()
def cliente_csrf(app):
    """Cliente com a proteção CSRF ligada, como em produção."""
    app.config["WTF_CSRF_ENABLED"] = True
    criar_usuario("ana@teste.local", nome="Ana")
    criar_usuario("inativo@teste.local", nome="Bruno", ativo=False)
    return app.test_client()


def token(html):
    """Pega o csrf_token do formulário, como o navegador faria."""
    campo = re.search(r'<input[^>]*name="csrf_token"[^>]*>', html)
    valor = campo and re.search(r'value="([^"]+)"', campo.group(0))
    return valor.group(1) if valor else ""


def entrar(cliente, email="ana@teste.local", senha=SENHA_TESTE, url_tela="/login", lembrar=True):
    """Abre a tela (GET) e envia o formulário para /login, sem ?next=, igual ao template."""
    dados = {"csrf_token": token(cliente.get(url_tela).get_data(as_text=True)),
             "identificador": email, "senha": senha, "perfil": "recepcao"}
    if lembrar:
        dados["lembrar"] = "1"
    return cliente.post("/login", data=dados)


def test_post_sem_csrf_e_recusado(cliente_csrf):
    resposta = cliente_csrf.post("/login", data={"identificador": "ana@teste.local", "senha": SENHA_TESTE})
    assert resposta.status_code == 400


def test_login_certo_vai_para_o_painel(cliente_csrf):
    resposta = entrar(cliente_csrf)
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/"
    assert cliente_csrf.get("/login").status_code == 302  # já logado não vê a tela de novo


def test_senha_errada_e_email_inexistente_dao_a_mesma_mensagem(cliente_csrf):
    errada = entrar(cliente_csrf, senha="errada").get_data(as_text=True)
    inexistente = entrar(cliente_csrf, email="ninguem@teste.local").get_data(as_text=True)
    assert "Usuário ou senha inválidos" in errada
    assert "Usuário ou senha inválidos" in inexistente
    assert 'value="ana@teste.local"' in errada      # repovoa o e-mail
    assert "data-abrir-auto" not in errada          # o popup de perfil não reabre


def test_usuario_inativo_nao_entra(cliente_csrf):
    assert "Usuário desativado" in entrar(cliente_csrf, email="inativo@teste.local").get_data(as_text=True)


def test_email_com_maiuscula_e_espacos_entra(cliente_csrf):
    assert entrar(cliente_csrf, email="  Ana@Teste.Local ").status_code == 302


def test_lembrar_de_mim(cliente_csrf, app):
    com = entrar(cliente_csrf, lembrar=True).headers.getlist("Set-Cookie")
    sem = entrar(app.test_client(), lembrar=False).headers.getlist("Set-Cookie")
    assert any("remember_token" in c for c in com)
    assert not any("remember_token" in c for c in sem)


def test_volta_para_a_pagina_pedida(cliente_csrf):
    """O formulário posta em /login sem o ?next=; o destino fica guardado na sessão."""
    resposta = entrar(cliente_csrf, url_tela="/login?next=/planos/listar/")
    assert resposta.headers["Location"] == "/planos/listar/"


@pytest.mark.parametrize("destino", ["https://site-falso.com", "//site-falso.com", "javascript:alert(1)"])
def test_next_de_outro_site_e_ignorado(cliente_csrf, destino):
    resposta = entrar(cliente_csrf, url_tela="/login?next=" + destino)
    assert resposta.headers["Location"] == "/"


def test_sair_so_por_post_e_com_csrf(cliente_csrf):
    entrar(cliente_csrf)
    assert cliente_csrf.get("/sair").status_code == 405
    assert cliente_csrf.post("/sair").status_code == 400
    # qualquer página logada com formulário serve para pegar um csrf_token válido
    tk = token(cliente_csrf.get("/planos/criar/").get_data(as_text=True))
    assert tk
    resposta = cliente_csrf.post("/sair", data={"csrf_token": tk})
    assert resposta.status_code == 302 and resposta.headers["Location"] == "/login"
    assert cliente_csrf.get("/").status_code == 302  # o "lembrar de mim" não loga de volta
