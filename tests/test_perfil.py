"""
Testes da branch back-30-meu-perfil: cada pessoa edita o próprio nome e e-mail e troca a própria senha em /perfil.
"""
import pytest

from app.extensions.database import db
from app.extensions.security import bcrypt
from app.models import User
from app.services.admin_service import CHAVE_DA_SESSAO
from tests import conftest
from tests.conftest import SENHA_TESTE, conta_de, criar_personal, criar_usuario, logar

NOVA = "outra frase bem comprida"


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def usuario(usuario_id):
    with conftest._APP.app_context():
        u = db.session.get(User, usuario_id)
        db.session.expunge(u)
        return u


def senha_e(usuario_id, senha):
    with conftest._APP.app_context():
        return bcrypt.check_password_hash(db.session.get(User, usuario_id).senha, senha)


@pytest.fixture()
def equipe(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    return {"dono": dono, "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
            "instrutor": criar_usuario("ivo@teste.local", nome="Ivo", conta=conta, papel="instrutor")}


# ------------------------------------------------------------------ a tela
@pytest.mark.parametrize("papel", ["dono", "recepcao", "instrutor"])
def test_todos_os_papeis_abrem_o_proprio_perfil(app, equipe, papel):
    html = como(app, equipe[papel]).get("/perfil").get_data(as_text=True)
    u = usuario(equipe[papel])
    assert "Meu perfil" in html and f'value="{u.email}"' in html and f'value="{u.nome}"' in html
    assert 'action="/perfil/dados"' in html and 'action="/perfil/senha"' in html


def test_personal_tambem_tem_perfil_e_o_menu_mostra_o_link(app):
    personal = criar_personal("pedro@teste.local", nome="Pedro")
    html = como(app, personal).get("/perfil").get_data(as_text=True)
    assert 'value="pedro@teste.local"' in html and 'href="/perfil"' in html


def test_sem_login_pede_login(app):
    assert app.test_client().get("/perfil").headers["Location"].startswith("/login")
    assert app.test_client().post("/perfil/senha", data={}).headers["Location"].startswith("/login")


# ------------------------------------------------------------------ nome e e-mail
def test_troca_o_nome_sem_pedir_senha(app, equipe):
    cliente = como(app, equipe["recepcao"])
    resposta = cliente.post("/perfil/dados", data={"nome": "  Rita  de Cássia ", "sobrenome": "Moraes", "email": "rita@teste.local"})
    assert resposta.status_code == 302
    u = usuario(equipe["recepcao"])
    assert (u.nome, u.sobrenome, u.email) == ("Rita de Cássia", "Moraes", "rita@teste.local")


def test_trocar_o_email_pede_a_senha_atual(app, equipe):
    cliente = como(app, equipe["dono"])
    sem_senha = cliente.post("/perfil/dados", data={"nome": "Diana", "email": "diana.nova@teste.local"})
    assert sem_senha.status_code == 400 and "Para trocar o e-mail, digite a sua senha atual." in sem_senha.get_data(as_text=True)
    errada = cliente.post("/perfil/dados", data={"nome": "Diana", "email": "diana.nova@teste.local", "senha_atual": "chute errado"})
    assert errada.status_code == 400 and usuario(equipe["dono"]).email == "dono@teste.local"

    certa = cliente.post("/perfil/dados", data={"nome": "Diana", "email": " Diana.Nova@Teste.local ", "senha_atual": SENHA_TESTE})
    assert certa.status_code == 302 and usuario(equipe["dono"]).email == "diana.nova@teste.local"
    # o login passa a ser o e-mail novo
    entrar = app.test_client().post("/login", data={"identificador": "diana.nova@teste.local", "senha": SENHA_TESTE})
    assert entrar.status_code == 302 and entrar.headers["Location"] == "/"


def test_nao_aceita_email_de_outra_pessoa_nem_invalido_nem_nome_vazio(app, equipe):
    cliente = como(app, equipe["instrutor"])
    outro = cliente.post("/perfil/dados", data={"nome": "Ivo", "email": "DONO@teste.local", "senha_atual": SENHA_TESTE})
    assert outro.status_code == 400 and "Esse e-mail já é o login de outra pessoa." in outro.get_data(as_text=True)
    invalido = cliente.post("/perfil/dados", data={"nome": "Ivo", "email": "ivo@", "senha_atual": SENHA_TESTE})
    assert invalido.status_code == 400 and "Confira o e-mail" in invalido.get_data(as_text=True)
    vazio = cliente.post("/perfil/dados", data={"nome": "   ", "email": "ivo@teste.local"})
    assert vazio.status_code == 400 and "Informe o seu nome." in vazio.get_data(as_text=True)
    assert usuario(equipe["instrutor"]).email == "ivo@teste.local" and usuario(equipe["instrutor"]).nome == "Ivo"


def test_o_formulario_so_mexe_no_proprio_usuario(app, equipe):
    """Mesmo mandando um `id` forjado no formulário, só quem está logado muda."""
    cliente = como(app, equipe["instrutor"])
    cliente.post("/perfil/dados", data={"id": equipe["dono"], "nome": "Hacker", "email": "ivo@teste.local"})
    assert usuario(equipe["dono"]).nome == "Diana" and usuario(equipe["instrutor"]).nome == "Hacker"


# ------------------------------------------------------------------ senha
def test_troca_a_senha_continua_logado_e_derruba_os_outros_aparelhos(app, equipe):
    este, outro_aparelho = como(app, equipe["dono"]), como(app, equipe["dono"])
    resposta = este.post("/perfil/senha", data={"senha_atual": SENHA_TESTE, "senha_nova": NOVA})
    assert resposta.status_code == 302 and senha_e(equipe["dono"], NOVA)
    assert este.get("/perfil").status_code == 200                                         # este aparelho continua dentro
    assert outro_aparelho.get("/perfil").headers["Location"].startswith("/login")       # o outro saiu
    assert app.test_client().post("/login", data={"identificador": "dono@teste.local", "senha": NOVA}).headers["Location"] == "/"


def test_senha_atual_errada_ou_nova_curta_ou_igual_nao_troca(app, equipe):
    cliente = como(app, equipe["recepcao"])
    errada = cliente.post("/perfil/senha", data={"senha_atual": "não é essa", "senha_nova": NOVA})
    assert errada.status_code == 400 and "A senha atual não confere." in errada.get_data(as_text=True)
    curta = cliente.post("/perfil/senha", data={"senha_atual": SENHA_TESTE, "senha_nova": "curta"})
    assert curta.status_code == 400 and "pelo menos 8 caracteres" in curta.get_data(as_text=True)
    igual = cliente.post("/perfil/senha", data={"senha_atual": SENHA_TESTE, "senha_nova": SENHA_TESTE})
    assert igual.status_code == 400 and "A nova senha é igual à atual." in igual.get_data(as_text=True)
    assert senha_e(equipe["recepcao"], SENHA_TESTE)


# ------------------------------------------------------------------ admin dentro da conta do cliente
def test_admin_dentro_da_conta_nao_muda_o_perfil_do_dono(app, equipe):
    cliente = como(app, equipe["dono"])
    with cliente.session_transaction() as sessao:
        sessao[CHAVE_DA_SESSAO] = "1|qualquer"               # como fica a sessão quando um admin "entra" na conta
    html = cliente.get("/perfil").get_data(as_text=True)
    assert "Este perfil é do cliente" in html and "disabled" in html
    cliente.post("/perfil/senha", data={"senha_atual": SENHA_TESTE, "senha_nova": NOVA})
    cliente.post("/perfil/dados", data={"nome": "Outro", "email": "admin@teste.local", "senha_atual": SENHA_TESTE})
    u = usuario(equipe["dono"])
    assert senha_e(equipe["dono"], SENHA_TESTE) and u.nome == "Diana" and u.email == "dono@teste.local"
