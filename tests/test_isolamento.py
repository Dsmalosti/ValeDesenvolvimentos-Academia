"""
Testes da branch back-03-isolamento: uma academia nunca vê, edita ou apaga dado de outra.

Cada teste monta duas contas, A e B, cada uma com plano, aluno, ficha e treino, loga como A e
tenta chegar no que é de B. Se algum destes testes falhar, NÃO faça o deploy: é o tipo de
defeito que faz uma academia enxergar os alunos da concorrente.
"""
import re

import pytest

from app.models import Aluno, Ficha, Plano, Treino, User
from tests.conftest import (campo, contar, criar_aluno, criar_ficha, criar_plano, criar_treino,
                            criar_usuario, logar)

# Páginas que existem para quem NÃO está logado. Qualquer outra rota tem que exigir login.
ROTAS_PUBLICAS = {"static", "auth.login", "auth.esqueci_senha", "auth.criar_conta",
                  "instrutores.login", "instrutores.cadastroInstrutor"}


@pytest.fixture()
def contas(app):
    """Duas academias completas. Devolve os ids num dicionário: contas['a']['aluno'] etc."""
    dados = {}
    for letra in ("a", "b"):
        dono = criar_usuario(f"dono-{letra}@teste.local", nome=f"Dono-{letra.upper()}")
        plano = criar_plano(dono, nome=f"Plano-{letra.upper()}")
        aluno = criar_aluno(dono, plano, f"Aluno-{letra.upper()}", f"aluno-{letra}@teste.local", f"cpf-{letra}")
        ficha = criar_ficha(aluno, nome=f"Ficha-{letra.upper()}")
        treino = criar_treino(ficha)
        dados[letra] = {"dono": dono, "plano": plano, "aluno": aluno, "ficha": ficha, "treino": treino}
    return dados


@pytest.fixture()
def logado_como_a(cliente, contas):
    logar(cliente, contas["a"]["dono"])
    return cliente


def test_pagina_com_id_de_outra_conta_da_404(logado_como_a, contas):
    b = contas["b"]
    tentativas = [
        ("GET", f"/alunos/editar/{b['aluno']}"),
        ("GET", f"/planos/editar/{b['plano']}/"),
        ("GET", f"/fichas/detalhes/{b['ficha']}"),
        ("GET", f"/fichas/editar/{b['ficha']}"),
        ("POST", f"/fichas/editar/{b['ficha']}"),
        ("POST", f"/fichas/excluir/{b['ficha']}"),
        ("GET", f"/fichas/{b['ficha']}/treino/novo"),
        ("POST", f"/fichas/{b['ficha']}/treino/novo"),
        ("GET", f"/fichas/treino/{b['treino']}/editar"),
        ("POST", f"/fichas/treino/{b['treino']}/editar"),
        ("POST", f"/fichas/treino/{b['treino']}/excluir"),
        ("GET", f"/fichas/treino/{b['treino']}/exercicio/adicionar"),
        ("POST", f"/fichas/treino/{b['treino']}/exercicio/adicionar"),
        ("GET", f"/pagamentos/registrar/{b['aluno']}"),
        ("POST", f"/pagamentos/registrar/{b['aluno']}"),
        ("GET", f"/pagamentos/listar/{b['aluno']}"),
        ("GET", f"/instrutores/editar/{b['dono']}"),
        ("POST", f"/instrutores/editar/{b['dono']}"),
        ("POST", f"/instrutores/excluir/{b['dono']}"),
    ]
    for metodo, url in tentativas:
        resposta = logado_como_a.open(url, method=metodo, data={"dia_semana": "terca", "nome": "invadido"})
        assert resposta.status_code == 404, f"{metodo} {url} respondeu {resposta.status_code}"


def test_acao_em_registro_de_outra_conta_nao_altera_nada(logado_como_a, contas):
    """Estas rotas respondem com um aviso de "não encontrado" em vez de 404; o que importa é não mudar nada."""
    b = contas["b"]
    logado_como_a.post(f"/alunos/excluir/{b['aluno']}")
    logado_como_a.post(f"/alunos/status/{b['aluno']}")
    logado_como_a.post(f"/alunos/editar/{b['aluno']}", data={"nome": "invadido"})
    logado_como_a.post(f"/planos/excluir/{b['plano']}")
    logado_como_a.post(f"/planos/editar/{b['plano']}/", data={"nome": "invadido"})

    assert campo(Aluno, b["aluno"], "nome") == "Aluno-B"
    assert campo(Aluno, b["aluno"], "ativo") is True
    assert campo(Plano, b["plano"], "nome") == "Plano-B"


def test_nada_da_outra_conta_foi_tocado_depois_das_tentativas(logado_como_a, contas):
    b = contas["b"]
    for metodo, url in [("POST", f"/fichas/excluir/{b['ficha']}"),
                        ("POST", f"/fichas/treino/{b['treino']}/excluir"),
                        ("POST", f"/fichas/editar/{b['ficha']}"),
                        ("POST", f"/instrutores/excluir/{b['dono']}"),
                        ("POST", f"/instrutores/editar/{b['dono']}")]:
        logado_como_a.open(url, method=metodo, data={"nome": "invadido", "sobrenome": "x",
                                                     "email": "tomei@teste.local", "senha": "nova-senha",
                                                     "confirmacao_senha": "nova-senha"})

    assert campo(Ficha, b["ficha"], "nome") == "Ficha-B"
    assert contar(Treino, id=b["treino"]) == 1
    assert campo(User, b["dono"], "email") == "dono-b@teste.local"


@pytest.mark.parametrize("url", ["/alunos/listar/", "/planos/listar/", "/fichas/listar/",
                                 "/instrutores/lista/", "/pagamentos/situacao/"])
def test_listas_so_mostram_a_propria_conta(logado_como_a, url):
    pagina = logado_como_a.get(url)
    html = pagina.get_data(as_text=True)

    assert pagina.status_code == 200
    assert not re.search(r"(Aluno|Plano|Ficha|Dono)-B|dono-b@|aluno-b@", html), f"{url} mostrou dado da conta B"


def test_listas_mostram_o_que_e_da_propria_conta(logado_como_a):
    """Garante que o teste acima não passa só porque a lista veio vazia."""
    assert "Aluno-A" in logado_como_a.get("/alunos/listar/").get_data(as_text=True)
    assert "Plano-A" in logado_como_a.get("/planos/listar/").get_data(as_text=True)
    assert "Ficha-A" in logado_como_a.get("/fichas/listar/").get_data(as_text=True)


def test_selects_so_oferecem_o_que_e_da_propria_conta(logado_como_a):
    cadastro_aluno = logado_como_a.get("/alunos/cadastro/").get_data(as_text=True)
    nova_ficha = logado_como_a.get("/fichas/novo/").get_data(as_text=True)

    assert "Plano-A" in cadastro_aluno and "Plano-B" not in cadastro_aluno
    assert "Aluno-A" in nova_ficha and "Aluno-B" not in nova_ficha


def test_envio_forjado_com_id_de_outra_conta_e_recusado(logado_como_a, contas):
    """Mesmo mandando o id direto no POST (sem passar pelo select), nada é criado."""
    b = contas["b"]
    logado_como_a.post("/alunos/cadastro/", data={
        "nome": "Forjado", "email": "forjado@exemplo.com", "telefone": "11999990000",
        "data_nascimento": "1990-01-01", "cpf": "cpf-forjado", "ativo": "y", "plano_id": str(b["plano"])})
    logado_como_a.post("/fichas/novo/", data={"nome": "Ficha forjada", "aluno_id": str(b["aluno"]), "ativo": "y"})

    assert contar(Aluno, email="forjado@exemplo.com") == 0
    assert contar(Ficha, nome="Ficha forjada") == 0


def test_o_mesmo_envio_com_id_da_propria_conta_funciona(logado_como_a, contas):
    """Par do teste acima: prova que o envio é recusado pelo id, e não por outro motivo."""
    a = contas["a"]
    logado_como_a.post("/alunos/cadastro/", data={
        "nome": "Legitimo", "email": "legitimo@exemplo.com", "telefone": "11999990000",
        "data_nascimento": "1990-01-01", "cpf": "cpf-legitimo", "ativo": "y", "plano_id": str(a["plano"])})
    logado_como_a.post("/fichas/novo/", data={"nome": "Ficha legitima", "aluno_id": str(a["aluno"]), "ativo": "y"})

    assert contar(Aluno, email="legitimo@exemplo.com") == 1
    assert contar(Ficha, nome="Ficha legitima") == 1


def test_painel_conta_so_os_alunos_da_propria_conta(cliente, contas):
    b = contas["b"]
    criar_aluno(b["dono"], b["plano"], "Outro-B", "outro-b@teste.local", "cpf-b2")
    logar(cliente, contas["a"]["dono"])

    html = cliente.get("/").get_data(as_text=True)

    ativos = re.search(r"Alunos\s+ativos.*?<[^>]+>\s*(\d+)\s*<", html, re.S | re.I)
    assert ativos and int(ativos.group(1)) == 1  # A tem 1 aluno ativo; B tem 2


def _rotas(app):
    """Todas as rotas do app com os parâmetros trocados por 1: (endpoint, url, métodos)."""
    for regra in app.url_map.iter_rules():
        yield regra.endpoint, re.sub(r"<[^>]+>", "1", regra.rule), regra.methods & {"GET", "POST"}


def test_sem_login_nenhuma_rota_abre(app):
    """Toda rota que não está em ROTAS_PUBLICAS manda quem não está logado para a tela de login."""
    abertas = []
    for endpoint, url, metodos in _rotas(app):
        if endpoint in ROTAS_PUBLICAS:
            continue
        for metodo in metodos:
            resposta = app.test_client().open(url, method=metodo)
            if not (resposta.status_code == 302 and resposta.headers["Location"].startswith("/login")):
                abertas.append(f"{metodo} {url} -> {resposta.status_code}")

    assert not abertas, "rotas que respondem sem login: " + ", ".join(abertas)


def test_nenhuma_rota_get_apaga_ou_altera_dados(app):
    """
    Rota que apaga, alterna ou desloga só pode aceitar POST. Com GET, um link, uma imagem em
    outro site ou o carregamento antecipado de links do front novo dispararia a ação sozinho.
    """
    # Pendência conhecida: o logout ANTIGO ainda é por GET. Sai junto com o cabeçalho antigo
    # (back-06-layout). O logout novo, /sair, já é só POST.
    pendencias_conhecidas = {"instrutores.logout"}

    perigosas = [f"{endpoint} {url}" for endpoint, url, metodos in _rotas(app)
                 if re.search(r"excluir|status|sair|inativar|alternar", url)
                 and "GET" in metodos and endpoint not in pendencias_conhecidas]

    assert not perigosas, "rotas que alteram dados por GET: " + ", ".join(perigosas)
