"""Testes da branch back-18-seguranca: limite de tentativas, cabeçalhos, prazo da sessão, sessão que cai e mensagem única do login."""
import os
from datetime import timedelta

import pytest

from app.extensions.database import db
from app.extensions.protecao import limiter
from app.extensions.security import bcrypt
from app.models import User
from tests.conftest import SENHA_TESTE, conta_de, criar_aluno, criar_plano, criar_usuario, logar


@pytest.fixture()
def dono(app):
    return criar_usuario("dono@teste.local", nome="Diana")


@pytest.fixture()
def com_limite(app):
    """Liga o limite de tentativas (nos testes ele fica desligado) e zera os contadores antes e depois."""
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.reset()
    limiter.enabled = False


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def tentar(cliente, email="dono@teste.local", senha="errada", ip="10.0.0.1", url="/login"):
    return cliente.post(url, data={"identificador": email, "senha": senha, "email": email}, environ_overrides={"REMOTE_ADDR": ip})


# ------------------------------------------------------------------ limite de tentativas
def test_login_bloqueia_depois_de_10_tentativas_por_minuto(app, dono, com_limite):
    cliente = app.test_client()
    for i in range(10):
        assert tentar(cliente, email=f"alvo{i}@teste.local").status_code == 200, i        # e-mails diferentes: o que conta aqui é o IP
    barrado = tentar(cliente, email="outro@teste.local")
    assert barrado.status_code == 429 and "Muitas tentativas" in barrado.get_data(as_text=True)
    assert tentar(cliente, senha=SENHA_TESTE).status_code == 429                         # nem com a senha certa, enquanto durar o bloqueio
    assert cliente.get("/login", environ_overrides={"REMOTE_ADDR": "10.0.0.1"}).status_code == 200      # abrir a tela não conta
    assert tentar(app.test_client(), email="mais@teste.local", ip="10.0.0.2").status_code == 200        # outro endereço não é afetado


def test_login_bloqueia_o_mesmo_email_vindo_de_enderecos_diferentes(app, dono, com_limite):
    for i in range(10):
        assert tentar(app.test_client(), ip=f"10.1.0.{i}").status_code == 200
    assert tentar(app.test_client(), ip="10.1.0.99").status_code == 429                  # 11ª tentativa na mesma conta, de outro IP
    assert tentar(app.test_client(), email="DONO@teste.local ", ip="10.1.0.98").status_code == 429      # maiúscula e espaço não driblam
    assert tentar(app.test_client(), email="vizinho@teste.local", ip="10.1.0.97").status_code == 200    # outra conta segue livre


def test_criar_conta_e_pedido_de_senha_tem_limite_por_hora(app, com_limite):
    cliente = app.test_client()
    for i in range(5):
        r = cliente.post("/criar-conta", data={"tipo": "academia", "nome": f"Pessoa {i}", "email": f"p{i}@teste.local", "senha": SENHA_TESTE},
                         environ_overrides={"REMOTE_ADDR": "10.2.0.1"})
        assert r.status_code == 302, i
        cliente.post("/sair")
    assert cliente.post("/criar-conta", data={"tipo": "academia", "nome": "Sexta", "email": "p6@teste.local", "senha": SENHA_TESTE},
                        environ_overrides={"REMOTE_ADDR": "10.2.0.1"}).status_code == 429
    with app.app_context():
        assert User.query.count() == 5                                                   # a sexta conta não foi criada

    for i in range(5):
        assert tentar(cliente, url="/esqueci-senha", ip="10.2.0.2").status_code == 200
    assert tentar(cliente, url="/esqueci-senha", ip="10.2.0.2").status_code == 429


def test_links_de_convite_e_de_senha_e_a_tela_antiga_de_login_tem_limite(app, com_limite):
    cliente = app.test_client()
    for url in ("/convite/codigo-inventado", "/nova-senha/codigo-inventado"):
        for _ in range(20):
            assert cliente.get(url, environ_overrides={"REMOTE_ADDR": "10.3.0.1"}).status_code == 404
        assert cliente.get(url, environ_overrides={"REMOTE_ADDR": "10.3.0.1"}).status_code == 429       # 21 códigos chutados em uma hora
    for _ in range(10):
        cliente.post("/instrutores/login/", data={"email": "x@teste.local", "senha": "errada"}, environ_overrides={"REMOTE_ADDR": "10.3.0.2"})
    assert cliente.post("/instrutores/login/", data={"email": "x@teste.local", "senha": "errada"},
                        environ_overrides={"REMOTE_ADDR": "10.3.0.2"}).status_code == 429


def test_sem_o_limite_ligado_nada_e_barrado(app, dono):
    cliente = app.test_client()
    assert all(tentar(cliente).status_code == 200 for _ in range(15))                    # é assim que os outros testes rodam


# ------------------------------------------------------------------ login: uma mensagem só
def test_login_responde_igual_para_email_inexistente_senha_errada_e_conta_desativada(app, dono):
    criar_usuario("parado@teste.local", nome="Paulo", ativo=False)
    cliente = app.test_client()
    respostas = [tentar(cliente, email=email, senha=senha).get_data(as_text=True)
                 for email, senha in (("ninguem@teste.local", "qualquer"), ("dono@teste.local", "errada"), ("parado@teste.local", SENHA_TESTE))]
    for html in respostas:
        assert "Usuário ou senha inválidos" in html and "desativ" not in html
    assert tentar(cliente, senha=SENHA_TESTE).status_code == 302                         # e quem acerta, entra


def test_tela_de_login_sem_popup_de_perfil_e_sem_botao_de_digital(app):
    html = app.test_client().get("/login").get_data(as_text=True)
    assert "dlg-perfil" not in html and "Como você vai entrar?" not in html and "data-abrir-auto" not in html
    assert "Entrar com digital" not in html and 'name="identificador"' in html and 'name="senha"' in html
    errada = tentar(app.test_client()).get_data(as_text=True)
    assert "dlg-perfil" not in errada and "Entrando como" not in errada.split("<form")[0]


# ------------------------------------------------------------------ sessão
def test_sessao_tem_prazo_e_o_cookie_e_protegido(app, dono):
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(hours=12) and app.config["REMEMBER_COOKIE_DURATION"] == timedelta(days=30)
    resposta = tentar(app.test_client(), senha=SENHA_TESTE)
    cookie = next(c for c in resposta.headers.getlist("Set-Cookie") if c.startswith("session="))
    assert "Expires=" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie    # com prazo; JavaScript não lê; outro site não usa


def test_trocar_a_senha_derruba_as_outras_sessoes(app, dono):
    celular, computador = como(app, dono), como(app, dono)
    assert celular.get("/alunos").status_code == 200 and computador.get("/alunos").status_code == 200
    with app.app_context():
        db.session.get(User, dono).senha = bcrypt.generate_password_hash("Outra-senha-456").decode("utf-8")
        db.session.commit()
    for cliente in (celular, computador):
        resposta = cliente.get("/alunos")
        assert resposta.status_code == 302 and "/login" in resposta.headers["Location"]
    assert tentar(app.test_client(), senha="Outra-senha-456").status_code == 302         # com a senha nova, entra


def test_troca_de_senha_pelo_link_derruba_quem_estava_logado(app, dono):
    from app.services import acesso_service
    logado = como(app, dono)
    with app.test_request_context():
        link = acesso_service.pedir_troca_de_senha("dono@teste.local", enviar=False)
    token = link.rsplit("/", 1)[-1]
    assert app.test_client().post(f"/nova-senha/{token}", data={"senha": "Senha-nova-789"}).status_code == 302
    assert "/login" in logado.get("/").headers["Location"]


def test_quem_foi_removido_da_equipe_perde_a_sessao_na_hora(app, dono):
    rita = criar_usuario("rita@teste.local", nome="Rita", conta=conta_de(dono), papel="recepcao")
    sessao_da_rita = como(app, rita)
    assert sessao_da_rita.get("/alunos").status_code == 200
    como(app, dono).post("/configuracoes/equipe", data={"acao": "remover", "id": rita})
    resposta = sessao_da_rita.get("/alunos")
    assert resposta.status_code == 302 and "/login" in resposta.headers["Location"]


@pytest.mark.parametrize("valor", ["ID", "ID|marca-errada", "ID|", "abc", "", "999999|0000000000000000", "1 OR 1=1"])
def test_sessao_com_identificacao_antiga_ou_forjada_nao_vale(app, dono, valor):
    cliente = app.test_client()
    with cliente.session_transaction() as sessao:
        sessao["_user_id"] = valor.replace("ID", str(dono))
        sessao["_fresh"] = True
    resposta = cliente.get("/alunos")
    assert resposta.status_code == 302 and "/login" in resposta.headers["Location"]


# ------------------------------------------------------------------ cabeçalhos
def test_toda_resposta_leva_os_cabecalhos_de_seguranca(app, dono):
    for resposta in (app.test_client().get("/login"), como(app, dono).get("/"), como(app, dono).get("/endereco-que-nao-existe")):
        csp = resposta.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp and "object-src 'none'" in csp and "form-action 'self'" in csp
        scripts = csp.split("script-src")[1].split(";")[0]
        assert "'self'" in scripts and "'unsafe-inline'" not in scripts and "'unsafe-eval'" not in scripts and "*" not in scripts
        assert resposta.headers["X-Frame-Options"] == "DENY" and resposta.headers["X-Content-Type-Options"] == "nosniff"
        assert resposta.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Strict-Transport-Security" not in resposta.headers                       # só em produção (aqui o endereço é http)


def test_as_telas_novas_nao_tem_script_nem_evento_embutido(app, dono):
    """A regra de CSP (script só de /static) só funciona se nenhum template tiver <script> com código ou onclick=."""
    import re
    raiz = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "templates")
    problemas = []
    for pasta, _, arquivos in os.walk(raiz):
        for nome in arquivos:
            if nome.endswith(".html"):
                texto = open(os.path.join(pasta, nome), encoding="utf-8").read()
                for achado in re.finditer(r"<script(?![^>]*\bsrc=)(?![^>]*application/json)[^>]*>|\son[a-z]+=\"", texto):
                    problemas.append(f"{nome}: {achado.group(0)[:40]}")
    assert problemas == []


def test_em_producao_https_obrigatorio_e_cookie_seguro(app):
    """Sobe o app com a configuração de produção (banco descartável) e confere o que só liga lá."""
    from app import create_app
    antes = os.environ.get("FLASK_CONFIG")
    os.environ["FLASK_CONFIG"] = "production"
    try:
        producao = create_app()
    finally:
        os.environ["FLASK_CONFIG"] = antes or "testing"
    assert "vt-testes-" in producao.config["SQLALCHEMY_DATABASE_URI"]
    assert producao.config["SESSION_COOKIE_SECURE"] and producao.config["REMEMBER_COOKIE_SECURE"] and not producao.config["DEBUG"]
    cliente = producao.test_client()
    sem_https = cliente.get("/login")
    assert sem_https.status_code == 302 and sem_https.headers["Location"].startswith("https://")
    com_https = cliente.get("/login", base_url="https://localhost")
    assert com_https.status_code == 200 and "max-age=" in com_https.headers["Strict-Transport-Security"]
    por_tras_do_proxy = cliente.get("/login", headers={"X-Forwarded-Proto": "https"})     # a hospedagem termina o HTTPS antes do app
    assert por_tras_do_proxy.status_code == 200
    limiter.enabled = False                                                              # o app de produção religou o limite: desliga para os próximos testes
    limiter.reset()


# ------------------------------------------------------------------ tamanho do envio
def test_envio_maior_que_5_mb_e_recusado(app, dono):
    assert app.config["MAX_CONTENT_LENGTH"] == 5 * 1024 * 1024
    plano = criar_plano(dono)
    aluno = criar_aluno(dono, plano, "Ana Souza", "ana@exemplo.com", "111.222.333-96")
    resposta = como(app, dono).post(f"/alunos/{aluno}/avaliacoes/nova", data={"peso_kg": "70", "altura_cm": "170", "anotacao": "x" * (6 * 1024 * 1024)})
    assert resposta.status_code == 413 and "Arquivo grande demais" in resposta.get_data(as_text=True)
