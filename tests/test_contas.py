"""
Testes da branch back-06-contas-e-papeis: conta (academia) separada de usuário, papéis,
exercício com dono, e-mail e CPF únicos por conta, cadastro aberto fechado e `flask criar-conta`.
"""
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
    pagina = entrar_como(app, equipe[quem]).get("/alunos/listar/")
    assert pagina.status_code == 200 and "Ana Souza" in pagina.get_data(as_text=True)


def test_aluno_cadastrado_pela_recepcao_aparece_para_o_dono(app, equipe):
    entrar_como(app, equipe["recepcao"]).post("/alunos/cadastro/", data={
        "nome": "Bruno Lima", "email": "bruno@exemplo.com", "telefone": "11999990000",
        "data_nascimento": "1990-01-01", "cpf": "222", "ativo": "y", "plano_id": str(equipe["plano"])})

    assert contar(Aluno, email="bruno@exemplo.com", conta_id=equipe["conta"]) == 1
    assert campo(Aluno, 2, "instrutor_id") == equipe["recepcao"]      # guarda quem cadastrou
    assert "Bruno Lima" in entrar_como(app, equipe["dono"]).get("/alunos/listar/").get_data(as_text=True)


def test_outra_academia_continua_sem_ver_nada(app, equipe):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    html = entrar_como(app, outro).get("/alunos/listar/").get_data(as_text=True)
    assert "Ana Souza" not in html
    assert entrar_como(app, outro).get(f"/alunos/editar/{equipe['aluno']}").status_code == 404


# ------------------------------------------------------------------ papéis
INSTRUTOR_NAO_PODE = [
    ("GET", "/alunos/cadastro/"), ("POST", "/alunos/cadastro/"), ("GET", "/alunos/editar/1"),
    ("POST", "/alunos/excluir/1"), ("POST", "/alunos/status/1"),
    ("GET", "/planos/criar/"), ("GET", "/planos/editar/1/"), ("POST", "/planos/excluir/1"),
    ("GET", "/pagamentos/situacao/"), ("GET", "/pagamentos/registrar/1"), ("GET", "/pagamentos/listar/1"),
    ("GET", "/relatorios"), ("GET", "/relatorios/painel"), ("POST", "/cobrancas/diaria"),
    ("GET", "/instrutores/lista/"), ("POST", "/instrutores/excluir/1"),
]


@pytest.mark.parametrize("metodo, url", INSTRUTOR_NAO_PODE)
def test_instrutor_recebe_403_no_que_nao_e_dele(app, equipe, metodo, url):
    resposta = entrar_como(app, equipe["instrutor"]).open(url, method=metodo)
    assert resposta.status_code == 403, f"{metodo} {url} respondeu {resposta.status_code}"


@pytest.mark.parametrize("url", ["/alunos/listar/", "/planos/listar/", "/fichas/listar/", "/exercicios/listar/",
                                 "/fichas/novo/", "/exercicios/criar/", "/configuracoes"])
def test_instrutor_entra_no_que_e_dele(app, equipe, url):
    assert entrar_como(app, equipe["instrutor"]).get(url).status_code == 200


@pytest.mark.parametrize("metodo, url", [m for m in INSTRUTOR_NAO_PODE if "excluir" not in m[1]])
def test_recepcao_pode_o_que_o_instrutor_nao_pode(app, equipe, metodo, url):
    resposta = entrar_como(app, equipe["recepcao"]).open(url, method=metodo)
    assert resposta.status_code != 403, f"{metodo} {url} barrou a recepção"


def test_so_o_dono_exclui_aluno(app, equipe):
    assert entrar_como(app, equipe["recepcao"]).post(f"/alunos/excluir/{equipe['aluno']}").status_code == 403
    assert contar(Aluno, id=equipe["aluno"]) == 1
    assert entrar_como(app, equipe["dono"]).post(f"/alunos/excluir/{equipe['aluno']}").status_code == 302
    assert contar(Aluno, id=equipe["aluno"]) == 0


def test_instrutor_nao_ve_os_numeros_do_painel(app, equipe):
    criar_pagamento(equipe["dono"], equipe["aluno"], 432, __import__("datetime").date.today(), __import__("datetime").date.today())

    do_instrutor = entrar_como(app, equipe["instrutor"]).get("/").get_data(as_text=True)
    do_dono = entrar_como(app, equipe["dono"]).get("/").get_data(as_text=True)

    assert "Painel do instrutor" in do_instrutor and "432" not in do_instrutor and "Faturamento" not in do_instrutor
    assert "432" in do_dono


# ------------------------------------------------------------------ gestão da equipe
def test_lista_da_equipe_mostra_so_a_propria_academia(app, equipe):
    criar_usuario("outro@teste.local", nome="Otto")
    html = entrar_como(app, equipe["dono"]).get("/instrutores/lista/").get_data(as_text=True)
    assert "Diana" in html and "Rita" in html and "Igor" in html and "Otto" not in html


def test_dono_edita_colega_recepcao_nao(app, equipe):
    dados = {"nome": "Igor", "sobrenome": "Novo", "email": "igor@exemplo.com", "senha": "", "confirmacao_senha": ""}   # o navegador sempre manda os dois campos de senha, vazios
    assert entrar_como(app, equipe["recepcao"]).post(f"/instrutores/editar/{equipe['instrutor']}", data=dados).status_code == 403
    assert campo(User, equipe["instrutor"], "sobrenome") == "Teste"
    assert entrar_como(app, equipe["dono"]).post(f"/instrutores/editar/{equipe['instrutor']}", data=dados).status_code == 302
    assert campo(User, equipe["instrutor"], "sobrenome") == "Novo"


def test_cada_um_edita_a_si_mesmo(app, equipe):
    dados = {"nome": "Igor", "sobrenome": "Eu Mesmo", "email": "igor@exemplo.com", "senha": "", "confirmacao_senha": ""}   # o navegador sempre manda os dois campos de senha, vazios
    assert entrar_como(app, equipe["instrutor"]).post(f"/instrutores/editar/{equipe['instrutor']}", data=dados).status_code == 302
    assert campo(User, equipe["instrutor"], "sobrenome") == "Eu Mesmo"


def test_dono_tira_alguem_da_equipe_mas_nao_a_si_mesmo(app, equipe):
    dono = entrar_como(app, equipe["dono"])
    dono.post(f"/instrutores/excluir/{equipe['dono']}")
    assert contar(User, id=equipe["dono"]) == 1                       # continua lá
    dono.post(f"/instrutores/excluir/{equipe['instrutor']}")
    assert contar(User, id=equipe["instrutor"]) == 0


def test_usuario_de_outra_academia_nao_e_alcancado(app, equipe):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    dono = entrar_como(app, equipe["dono"])
    assert dono.get(f"/instrutores/editar/{outro}").status_code == 404
    assert dono.post(f"/instrutores/excluir/{outro}").status_code == 404
    assert contar(User, id=outro) == 1


# ------------------------------------------------------------------ cadastro aberto fechado
def test_cadastro_aberto_pela_internet_esta_fechado(cliente):
    dados = {"nome": "Invasor", "sobrenome": "X", "email": "invasor@exemplo.com", "senha": "abc12345", "confirmacao_senha": "abc12345"}
    assert cliente.get("/instrutores/cadastro/").status_code == 404
    assert cliente.post("/instrutores/cadastro/", data=dados).status_code == 404
    assert contar(User) == 0 and contar(Conta) == 0


# ------------------------------------------------------------------ exercício com dono
def test_exercicio_catalogo_e_proprio(app, equipe):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    do_catalogo = criar_exercicio("Agachamento padrao")
    da_casa = criar_exercicio("Supino da casa", dono_id=equipe["dono"])
    do_vizinho = criar_exercicio("Rosca do vizinho", dono_id=outro)
    dono = entrar_como(app, equipe["dono"])

    lista = dono.get("/exercicios/listar/").get_data(as_text=True)
    assert "Agachamento padrao" in lista and "Supino da casa" in lista and "Rosca do vizinho" not in lista

    novo = {"nome": "Alterado", "grupo_muscular": "peito", "ativo": "y"}
    assert dono.post(f"/exercicios/editar/{do_catalogo}", data=novo).status_code == 404   # catálogo: ninguém edita
    assert dono.post(f"/exercicios/editar/{do_vizinho}", data=novo).status_code == 404    # de outra academia
    assert dono.post(f"/exercicios/excluir/{do_vizinho}").status_code == 404
    assert dono.post(f"/exercicios/editar/{da_casa}", data=novo).status_code == 302       # o da própria academia
    assert campo(Exercicio, do_catalogo, "nome") == "Agachamento padrao"
    assert campo(Exercicio, do_vizinho, "nome") == "Rosca do vizinho"
    assert campo(Exercicio, da_casa, "nome") == "Alterado"


def test_exercicio_criado_nasce_da_academia(app, equipe):
    entrar_como(app, equipe["instrutor"]).post("/exercicios/criar/", data={"nome": "Remada nova", "grupo_muscular": "costas", "ativo": "y"})
    assert contar(Exercicio, nome="Remada nova", conta_id=equipe["conta"]) == 1


# ------------------------------------------------------------------ e-mail e CPF únicos por conta
def test_mesmo_email_e_cpf_em_academias_diferentes_pode(app, equipe):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    plano = criar_plano(outro, nome="Plano do Otto")
    entrar_como(app, outro).post("/alunos/cadastro/", data={
        "nome": "Ana Souza", "email": "ana@exemplo.com", "telefone": "11999990000",
        "data_nascimento": "1990-01-01", "cpf": "111", "ativo": "y", "plano_id": str(plano)})
    assert contar(Aluno, email="ana@exemplo.com") == 2


def test_mesmo_email_na_mesma_academia_nao_pode(app, equipe):
    entrar_como(app, equipe["dono"]).post("/alunos/cadastro/", data={
        "nome": "Outra Ana", "email": "ana@exemplo.com", "telefone": "11999990000",
        "data_nascimento": "1990-01-01", "cpf": "999", "ativo": "y", "plano_id": str(equipe["plano"])})
    assert contar(Aluno, email="ana@exemplo.com") == 1


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
