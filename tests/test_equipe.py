"""Testes da branch back-13-equipe: criar conta, convite da equipe, trocar papel, remover e troca de senha."""
import re
from datetime import datetime, timedelta

import pytest

from app.extensions.security import bcrypt
from app.models import Conta, Convite, RedefinicaoSenha, User
from app.services import acesso_service
from tests.conftest import SENHA_TESTE, campo, conta_de, contar, criar_usuario, logar

SENHA_NOVA = "uma frase bem comprida 2026"


@pytest.fixture()
def academia(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    return {"dono": dono, "conta": conta,
            "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
            "instrutor": criar_usuario("igor@teste.local", nome="Igor", conta=conta, papel="instrutor")}


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def convidar(cliente, email="nova@exemplo.com", papel="recepcao"):
    """O dono convida pela tela. Devolve o link do convite (que fica na sessão dele para o botão de copiar)."""
    cliente.post("/configuracoes/equipe", data={"acao": "convidar", "email": email, "papel": papel})
    with cliente.session_transaction() as sessao:
        links = sessao.get("links_de_convite", {})
    return list(links.values())[-1] if links else None


def caminho(link):
    return "/" + link.split("/", 3)[3]


def entra(app, email, senha):
    """Tenta entrar pela tela de login. Devolve True se entrou."""
    resposta = app.test_client().post("/login", data={"identificador": email, "senha": senha})
    return resposta.status_code == 302 and resposta.headers["Location"] == "/"


def mexer(app, modelo, id, **campos):
    with app.app_context():
        from app.extensions.database import db
        registro = db.session.get(modelo, id)
        for nome, valor in campos.items():
            setattr(registro, nome, valor)
        db.session.commit()


# ------------------------------------------------------------------ criar conta
def test_dono_cria_a_propria_conta_e_ja_entra(app):
    cliente = app.test_client()
    assert "Criar sua conta" in cliente.get("/criar-conta").get_data(as_text=True)

    resposta = cliente.post("/criar-conta", data={"tipo": "academia", "nome": "Marina Albuquerque", "email": " Marina@Exemplo.com ", "senha": SENHA_NOVA})

    assert resposta.status_code == 302 and resposta.headers["Location"] == "/"
    with app.app_context():
        usuario = User.query.filter_by(email="marina@exemplo.com").one()
        conta = usuario.conta
        assert (usuario.nome, usuario.sobrenome, usuario.papel, usuario.ativo) == ("Marina", "Albuquerque", "proprietario", True)
        assert (conta.nome, conta.modelo, conta.checkin_ativo) == ("Academia de Marina", "academia", True)
        assert usuario.senha != SENHA_NOVA and bcrypt.check_password_hash(usuario.senha, SENHA_NOVA)      # senha guardada com bcrypt
    assert cliente.get("/").status_code == 200                              # já está logada, no painel
    assert entra(app, "marina@exemplo.com", SENHA_NOVA)


def test_personal_cria_conta_do_modelo_personal(app):
    app.test_client().post("/criar-conta", data={"tipo": "personal", "nome": "Adauto Netto", "email": "adauto@exemplo.com", "senha": SENHA_NOVA})
    with app.app_context():
        conta = User.query.filter_by(email="adauto@exemplo.com").one().conta
        assert (conta.nome, conta.modelo, conta.checkin_ativo) == ("Adauto Netto", "personal", False)


@pytest.mark.parametrize("trocas, aviso", [
    ({"nome": "  "}, "Diga seu nome."),
    ({"email": "sem-arroba"}, "Confira o e-mail"),
    ({"senha": "1234567"}, "pelo menos 8 caracteres"),
    ({"senha": "x" * 73}, "no máximo 72 caracteres"),
    ({"email": "DONO@teste.local"}, "Esse e-mail já tem conta."),            # já existe (em maiúsculas dá no mesmo)
])
def test_conta_invalida_avisa_e_nao_cria(app, academia, trocas, aviso):
    dados = {"tipo": "academia", "nome": "Marina", "email": "marina@exemplo.com", "senha": SENHA_NOVA}
    dados.update(trocas)
    antes = (contar(User), contar(Conta))
    resposta = app.test_client().post("/criar-conta", data=dados)
    assert resposta.status_code == 400 and aviso in resposta.get_data(as_text=True)
    assert (contar(User), contar(Conta)) == antes


def test_quem_ja_esta_logado_nao_cria_outra_conta(app, academia):
    assert como(app, academia["dono"]).get("/criar-conta").headers["Location"] == "/"


# ------------------------------------------------------------------ convidar
def test_dono_convida_e_o_banco_guarda_so_o_hash_do_link(app, academia):
    dono = como(app, academia["dono"])
    link = convidar(dono, "Nova@Exemplo.com", "instrutor")

    token = link.rsplit("/", 1)[1]
    with app.app_context():
        convite = Convite.query.one()
        assert (convite.email, convite.papel, convite.conta_id, convite.criado_por_id) == ("nova@exemplo.com", "instrutor", academia["conta"], academia["dono"])
        assert re.fullmatch(r"[0-9a-f]{64}", convite.token_hash) and token not in convite.token_hash and len(token) >= 40
        assert timedelta(days=6, hours=23) < convite.expira_em - datetime.now() <= timedelta(days=7) and convite.usado_em is None

    html = dono.get("/configuracoes?aba=equipe").get_data(as_text=True)
    assert "Convite enviado · esperando criar a senha" in html and f'data-copiar="{link}"' in html
    # em outro navegador (outra sessão) o convite aparece, mas sem o link: ele não está guardado em lugar nenhum
    outro_navegador = como(app, academia["dono"]).get("/configuracoes?aba=equipe").get_data(as_text=True)
    assert "esperando criar a senha" in outro_navegador and "data-copiar" not in outro_navegador


def test_convidar_de_novo_o_mesmo_email_troca_o_convite(app, academia):
    dono = como(app, academia["dono"])
    primeiro = convidar(dono, "nova@exemplo.com")
    segundo = convidar(dono, "nova@exemplo.com", "instrutor")
    assert contar(Convite) == 1 and primeiro != segundo
    assert app.test_client().get(caminho(primeiro)).status_code == 404      # o link antigo deixou de valer
    assert app.test_client().get(caminho(segundo)).status_code == 200


@pytest.mark.parametrize("email, papel", [("sem-arroba", "recepcao"), ("", "recepcao"), ("nova@exemplo.com", "proprietario"),
                                          ("nova@exemplo.com", ""), ("rita@teste.local", "recepcao"), ("de-fora@teste.local", "recepcao")])
def test_convite_invalido_nao_e_criado(app, academia, email, papel):
    criar_usuario("de-fora@teste.local", nome="Fabio")                       # tem conta em outra academia
    assert convidar(como(app, academia["dono"]), email, papel) is None and contar(Convite) == 0


def test_so_o_dono_convida_e_gerencia(app, academia):
    for papel in ("recepcao", "instrutor"):
        resposta = como(app, academia[papel]).post("/configuracoes/equipe", data={"acao": "convidar", "email": "x@exemplo.com", "papel": "recepcao"})
        assert resposta.status_code == 403
    assert contar(Convite) == 0


# ------------------------------------------------------------------ aceitar o convite
def test_convidado_cria_a_senha_e_entra_na_equipe_certa(app, academia):
    link = convidar(como(app, academia["dono"]), "nova@exemplo.com", "instrutor")
    visitante = app.test_client()

    tela = visitante.get(caminho(link)).get_data(as_text=True)
    assert "Criar seu acesso" in tela and "nova@exemplo.com" in tela and "Academia de Diana" in tela and "Instrutor" in tela and "Diana te convidou" in tela

    resposta = visitante.post(caminho(link), data={"nome": "Paulo Reis", "senha": SENHA_NOVA})

    assert resposta.status_code == 302 and resposta.headers["Location"] == "/"
    with app.app_context():
        novo = User.query.filter_by(email="nova@exemplo.com").one()
        assert (novo.nome, novo.sobrenome, novo.papel, novo.conta_id, novo.ativo) == ("Paulo", "Reis", "instrutor", academia["conta"], True)
        assert bcrypt.check_password_hash(novo.senha, SENHA_NOVA) and Convite.query.one().usado_em is not None
    assert visitante.get("/alunos").status_code == 200                       # já entrou, na academia certa
    assert visitante.get("/relatorios/painel").status_code == 403            # e com o papel certo (instrutor não vê dinheiro)
    assert "Paulo Reis" in como(app, academia["dono"]).get("/configuracoes?aba=equipe").get_data(as_text=True)


def test_link_de_convite_so_vale_uma_vez_e_por_7_dias(app, academia):
    dono = como(app, academia["dono"])
    usado = convidar(dono, "um@exemplo.com")
    app.test_client().post(caminho(usado), data={"nome": "Um Dois", "senha": SENHA_NOVA})
    vencido = convidar(dono, "dois@exemplo.com")
    with app.app_context():
        convite = Convite.query.filter_by(email="dois@exemplo.com").one()
        mexer(app, Convite, convite.id, expira_em=datetime.now() - timedelta(minutes=1))

    for link in (usado, vencido, "http://localhost/convite/codigo-inventado"):
        for metodo in ("GET", "POST"):
            resposta = app.test_client().open(caminho(link), method=metodo, data={"nome": "Invasor", "senha": SENHA_NOVA})
            assert resposta.status_code == 404 and "Este convite não vale mais" in resposta.get_data(as_text=True), f"{metodo} {link}"
    assert contar(User, nome="Invasor") == 0


@pytest.mark.parametrize("dados, aviso", [({"nome": "", "senha": SENHA_NOVA}, "Diga seu nome."), ({"nome": "Paulo", "senha": "curta"}, "pelo menos 8 caracteres")])
def test_convite_com_dado_invalido_nao_cria_e_continua_valendo(app, academia, dados, aviso):
    link = convidar(como(app, academia["dono"]), "nova@exemplo.com")
    resposta = app.test_client().post(caminho(link), data=dados)
    assert resposta.status_code == 400 and aviso in resposta.get_data(as_text=True)
    assert contar(User, email="nova@exemplo.com") == 0 and app.test_client().get(caminho(link)).status_code == 200


# ------------------------------------------------------------------ papel, remover, cancelar
def test_trocar_o_papel(app, academia):
    dono = como(app, academia["dono"])
    dono.post("/configuracoes/equipe", data={"acao": "papel", "id": academia["instrutor"], "papel": "recepcao"})
    assert campo(User, academia["instrutor"], "papel") == "recepcao"

    for alvo, papel in [(academia["instrutor"], "proprietario"), (academia["dono"], "instrutor")]:     # ninguém vira dono, e o dono não é rebaixado
        dono.post("/configuracoes/equipe", data={"acao": "papel", "id": alvo, "papel": papel})
    assert campo(User, academia["instrutor"], "papel") == "recepcao" and campo(User, academia["dono"], "papel") == "proprietario"


def test_remover_tira_o_acesso_sem_apagar_o_cadastro(app, academia):
    dono = como(app, academia["dono"])
    assert entra(app, "rita@teste.local", SENHA_TESTE)

    dono.post("/configuracoes/equipe", data={"acao": "remover", "id": academia["recepcao"]})

    assert contar(User, id=academia["recepcao"]) == 1 and campo(User, academia["recepcao"], "ativo") is False
    assert not entra(app, "rita@teste.local", SENHA_TESTE)
    assert "Rita Teste" not in dono.get("/configuracoes?aba=equipe").get_data(as_text=True)

    # o dono não se remove, e ninguém mexe na equipe de outra academia
    de_fora = criar_usuario("dono-b@teste.local", nome="Bento")
    colega_de_fora = criar_usuario("colega-b@teste.local", nome="Carla", conta=conta_de(de_fora), papel="recepcao")
    for alvo in (academia["dono"], colega_de_fora, 99999):
        dono.post("/configuracoes/equipe", data={"acao": "remover", "id": alvo})
    assert campo(User, academia["dono"], "ativo") is True and campo(User, colega_de_fora, "ativo") is True


def test_quem_foi_removido_pode_ser_convidado_de_novo_e_volta_com_o_mesmo_cadastro(app, academia):
    dono = como(app, academia["dono"])
    dono.post("/configuracoes/equipe", data={"acao": "remover", "id": academia["recepcao"]})
    link = convidar(dono, "rita@teste.local", "instrutor")
    app.test_client().post(caminho(link), data={"nome": "Rita Volta", "senha": SENHA_NOVA})

    assert contar(User, email="rita@teste.local") == 1
    assert (campo(User, academia["recepcao"], "ativo"), campo(User, academia["recepcao"], "papel")) == (True, "instrutor")
    assert entra(app, "rita@teste.local", SENHA_NOVA) and not entra(app, "rita@teste.local", SENHA_TESTE)


def test_cancelar_convite_e_convite_de_outra_academia(app, academia):
    dono = como(app, academia["dono"])
    link = convidar(dono, "nova@exemplo.com")
    with app.app_context():
        numero = Convite.query.one().id
    outro = como(app, criar_usuario("dono-b@teste.local", nome="Bento"))
    outro.post("/configuracoes/equipe", data={"acao": "remover", "id": -numero})          # de outra academia: nada acontece
    assert contar(Convite) == 1 and "nova@exemplo.com" not in outro.get("/configuracoes?aba=equipe").get_data(as_text=True)

    dono.post("/configuracoes/equipe", data={"acao": "remover", "id": -numero})
    assert contar(Convite) == 0 and app.test_client().get(caminho(link)).status_code == 404


# ------------------------------------------------------------------ esqueci a senha
def test_esqueci_a_senha_responde_igual_exista_a_conta_ou_nao(app, academia):
    visitante = app.test_client()
    assert "Recuperar acesso" in visitante.get("/esqueci-senha").get_data(as_text=True)

    existe = visitante.post("/esqueci-senha", data={"email": "rita@teste.local"})
    nao_existe = visitante.post("/esqueci-senha", data={"email": "ninguem@teste.local"})

    assert existe.status_code == nao_existe.status_code == 200
    assert existe.get_data(as_text=True).replace("rita@teste.local", "X") == nao_existe.get_data(as_text=True).replace("ninguem@teste.local", "X")
    assert "Pedido registrado" in existe.get_data(as_text=True)              # nos testes o e-mail não está configurado: a tela não diz "enviado"
    with app.app_context():
        pedido = RedefinicaoSenha.query.one()                                # só existe pedido para quem tem conta
        assert pedido.usuario_id == academia["recepcao"] and re.fullmatch(r"[0-9a-f]{64}", pedido.token_hash)
        assert timedelta(minutes=59) < pedido.expira_em - datetime.now() <= timedelta(hours=1)


def link_de_senha(app, email):
    with app.test_request_context():
        return acesso_service.pedir_troca_de_senha(email, enviar=False)


def test_trocar_a_senha_pelo_link(app, academia):
    link = link_de_senha(app, "rita@teste.local")
    visitante = app.test_client()
    assert "Criar senha nova" in visitante.get(caminho(link)).get_data(as_text=True)
    curta = visitante.post(caminho(link), data={"senha": "curta"})
    assert curta.status_code == 400 and "pelo menos 8 caracteres" in curta.get_data(as_text=True)

    resposta = visitante.post(caminho(link), data={"senha": SENHA_NOVA})

    assert resposta.status_code == 302 and resposta.headers["Location"] == "/login"      # não entra sozinho: faz o login com a senha nova
    assert entra(app, "rita@teste.local", SENHA_NOVA) and not entra(app, "rita@teste.local", SENHA_TESTE)
    assert visitante.get(caminho(link)).status_code == 404                               # uso único
    assert visitante.post(caminho(link), data={"senha": "outra senha qualquer"}).status_code == 404
    assert entra(app, "rita@teste.local", SENHA_NOVA)


def test_link_de_senha_vence_em_1_hora_e_o_pedido_novo_cancela_o_antigo(app, academia):
    antigo = link_de_senha(app, "rita@teste.local")
    novo = link_de_senha(app, "rita@teste.local")
    assert contar(RedefinicaoSenha) == 1 and app.test_client().get(caminho(antigo)).status_code == 404
    with app.app_context():
        mexer(app, RedefinicaoSenha, RedefinicaoSenha.query.one().id, expira_em=datetime.now() - timedelta(seconds=1))
    resposta = app.test_client().post(caminho(novo), data={"senha": SENHA_NOVA})
    assert resposta.status_code == 404 and "Este link não vale mais" in resposta.get_data(as_text=True)
    assert entra(app, "rita@teste.local", SENHA_TESTE)


def test_conta_desativada_nao_recebe_link_de_senha(app, academia):
    mexer(app, User, academia["recepcao"], ativo=False)
    assert link_de_senha(app, "rita@teste.local") is None and link_de_senha(app, "sem-arroba") is None and contar(RedefinicaoSenha) == 0


def test_comando_do_suporte_gera_o_link(app, academia):
    saida = app.test_cli_runner().invoke(args=["link-de-senha", "--email", "rita@teste.local"]).output
    assert "/nova-senha/" in saida
    assert "Não há conta ativa" in app.test_cli_runner().invoke(args=["link-de-senha", "--email", "ninguem@teste.local"]).output


# ------------------------------------------------------------------ e-mail
def test_email_vai_com_criptografia_e_falha_do_provedor_nao_derruba_a_tela(app, monkeypatch):
    from app.helpers import email as modulo
    enviados = []

    class ServidorFalso:
        def __init__(self, host, porta, timeout):
            self.host, self.porta, self.passos = host, porta, []

        def __enter__(self):
            return self

        def __exit__(self, *erro):
            return False

        def starttls(self):
            self.passos.append("tls")

        def login(self, usuario, senha):
            self.passos.append("login")

        def send_message(self, mensagem):
            enviados.append((self.host, self.porta, self.passos + ["envio"], mensagem["To"], mensagem["Subject"], mensagem.get_content()))

    for chave, valor in {"SMTP_HOST": "smtp.exemplo.com", "SMTP_USUARIO": "u", "SMTP_SENHA": "s", "EMAIL_REMETENTE": "nao-responda@exemplo.com"}.items():
        monkeypatch.setenv(chave, valor)
    monkeypatch.setattr(modulo.smtplib, "SMTP", ServidorFalso)
    with app.app_context():
        assert modulo.email_configurado() is False                           # nos testes nunca envia
        app.config["TESTING"] = False
        try:
            assert modulo.enviar_email("ana@exemplo.com", "Assunto", "Texto com o link") is True
            assert enviados == [("smtp.exemplo.com", 587, ["tls", "login", "envio"], "ana@exemplo.com", "Assunto", "Texto com o link\n")]

            def quebrado(*args, **kwargs):
                raise OSError("sem rede")
            monkeypatch.setattr(modulo.smtplib, "SMTP", quebrado)
            assert modulo.enviar_email("ana@exemplo.com", "Assunto", "Texto") is False      # não levanta erro
        finally:
            app.config["TESTING"] = True
