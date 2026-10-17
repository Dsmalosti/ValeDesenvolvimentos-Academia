"""
Testes da branch back-28-precos-e-promocao: preços novos (R$ 59,99 academia e R$ 29,99 personal) e a promoção de
lançamento (50% para as 10 primeiras contas criadas), com o controle do admin.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.extensions.database import db
from app.models import AcaoAdmin, Conta, User
from app.services import assinatura_service
from tests import conftest
from tests.conftest import conta_de, contar, criar_personal, criar_usuario, logar

SENHA = "uma frase de teste longa"
HOJE = date.today()


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def mudar(conta_id, **campos):
    with conftest._APP.app_context():
        conta = db.session.get(Conta, conta_id)
        for nome, valor in campos.items():
            setattr(conta, nome, valor)
        db.session.commit()


def da_conta(conta_id, campo):
    with conftest._APP.app_context():
        return getattr(db.session.get(Conta, conta_id), campo)


def ocupar_vagas(quantas):
    """Cria `quantas` contas que já estão na promoção (para testar o fim das vagas)."""
    with conftest._APP.app_context():
        for i in range(quantas):
            db.session.add(Conta(nome=f"Ocupada {i}", desconto_promocional=50))
        db.session.commit()


def criar_pela_tela(app, email, tipo="academia"):
    cliente = app.test_client()
    resposta = cliente.post("/criar-conta", data={"tipo": tipo, "nome": "Marina Albuquerque", "email": email, "senha": SENHA})
    assert resposta.status_code == 302
    with conftest._APP.app_context():
        return User.query.filter_by(email=email).one().conta_id


# ------------------------------------------------------------------ preço
def test_precos_novos_e_metade_arredondada_para_baixo():
    assert assinatura_service.preco(Conta(modelo="academia")) == Decimal("59.99")
    assert assinatura_service.preco(Conta(modelo="personal")) == Decimal("29.99")
    # 59,99 / 2 = 29,995: o cliente paga 29,99 (nunca mais que a metade)
    assert assinatura_service.preco(Conta(modelo="academia", desconto_promocional=50)) == Decimal("29.99")
    assert assinatura_service.preco(Conta(modelo="personal", desconto_promocional=50)) == Decimal("14.99")
    assert assinatura_service.preco_cheio(Conta(modelo="academia", desconto_promocional=50)) == Decimal("59.99")


# ------------------------------------------------------------------ quem ganha a promoção
def test_conta_criada_pela_tela_ganha_a_promocao_enquanto_ha_vaga(app):
    conta = criar_pela_tela(app, "marina@exemplo.com")
    assert da_conta(conta, "desconto_promocional") == 50


def test_a_decima_primeira_conta_paga_o_preco_cheio(app):
    ocupar_vagas(10)
    with conftest._APP.app_context():
        assert assinatura_service.vagas_da_promocao() == 0
    conta = criar_pela_tela(app, "marina@exemplo.com")
    assert da_conta(conta, "desconto_promocional") == 0


def test_conta_apagada_devolve_a_vaga(app):
    ocupar_vagas(10)
    with conftest._APP.app_context():
        db.session.delete(Conta.query.filter_by(nome="Ocupada 0").one())
        db.session.commit()
        assert assinatura_service.vagas_da_promocao() == 1


def test_flask_criar_conta_tambem_entra_na_promocao(app):
    resultado = app.test_cli_runner().invoke(args=["criar-conta"], input="Studio Forte\nLia\nPrado\nlia@exemplo.com\nsenha-de-teste\nsenha-de-teste\n")
    assert resultado.exit_code == 0, resultado.output
    with conftest._APP.app_context():
        assert User.query.filter_by(email="lia@exemplo.com").one().conta.desconto_promocional == 50


# ------------------------------------------------------------------ telas
def test_tela_de_criar_conta_mostra_as_vagas_e_some_quando_acabam(app):
    html = app.test_client().get("/criar-conta").get_data(as_text=True)
    assert "Promoção de lançamento: 50% de desconto" in html and "restam 10" in html
    assert "R$ 29,99 por mês para academia" in html and "R$ 14,99 para personal" in html
    ocupar_vagas(9)
    assert "resta 1." in app.test_client().get("/criar-conta").get_data(as_text=True)
    ocupar_vagas(1)
    assert "Promoção de lançamento" not in app.test_client().get("/criar-conta").get_data(as_text=True)


def test_tela_de_assinatura_e_pix_com_o_preco_da_promocao(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    mudar(conta_de(dono), desconto_promocional=50)
    app.config["VALE_TEC_PIX_CHAVE"] = "60499733000144"
    html = como(app, dono).get("/assinatura").get_data(as_text=True)
    assert "R$ 29,99 por mês" in html and "<s class=\"faint\">R$ 59,99</s>" in html
    assert "Promoção de lançamento: 50% de desconto" in html and "540529.99" in html     # o PIX já vem com o valor da promoção


def test_conta_sem_promocao_nao_mostra_o_aviso(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    html = como(app, dono).get("/assinatura").get_data(as_text=True)
    assert "R$ 59,99 por mês" in html and "Promoção de lançamento" not in html


def test_aviso_do_topo_lembra_a_promocao(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    mudar(conta_de(dono), desconto_promocional=50, teste_ate=HOJE + timedelta(days=3))
    painel = como(app, dono).get("/").get_data(as_text=True)
    assert "custa R$ 29,99 por mês" in painel and "50% de desconto" in painel


def test_personal_na_promocao(app):
    personal = criar_personal("pedro@teste.local", nome="Pedro")
    mudar(conta_de(personal), desconto_promocional=50)
    assert "R$ 14,99 por mês" in como(app, personal).get("/assinatura").get_data(as_text=True)


# ------------------------------------------------------------------ admin
@pytest.fixture()
def admin(app):
    adm = criar_usuario("adauto@teste.local", nome="Adauto")
    with conftest._APP.app_context():
        db.session.get(User, adm).admin_sistema = True
        db.session.commit()
    return adm


def test_admin_tira_e_da_a_promocao_e_fica_registrado(app, admin):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    cliente = como(app, admin)
    assert "Dar a promoção (50%)" in cliente.get(f"/admin/contas/{conta}").get_data(as_text=True)

    assert cliente.post(f"/admin/contas/{conta}/promocao", data={"ligar": "1"}).status_code == 302
    assert da_conta(conta, "desconto_promocional") == 50
    tela = cliente.get(f"/admin/contas/{conta}").get_data(as_text=True)
    assert "Promoção 50%" in tela and "Tirar a promoção" in tela
    assert "1 de 10 vagas usadas" in cliente.get("/admin").get_data(as_text=True)

    cliente.post(f"/admin/contas/{conta}/promocao", data={"ligar": "0"})
    assert da_conta(conta, "desconto_promocional") == 0
    assert contar(AcaoAdmin, conta_id=conta, acao="promocao") == 2


def test_admin_nao_da_promocao_sem_vaga(app, admin):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    ocupar_vagas(10)
    cliente = como(app, admin)
    tela = cliente.post(f"/admin/contas/{conta}/promocao", data={"ligar": "1"}, follow_redirects=True).get_data(as_text=True)
    # o aviso vai para o JSON dos toasts (acentos viram ç...): confere o começo, sem acento
    assert "As 10 vagas da promo" in tela and da_conta(conta, "desconto_promocional") == 0


def test_quem_nao_e_admin_nao_mexe_na_promocao(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    outro = criar_usuario("outro@teste.local", nome="Otto")
    conta = conta_de(outro)
    assert como(app, dono).post(f"/admin/contas/{conta}/promocao", data={"ligar": "1"}).status_code == 404
    assert da_conta(conta, "desconto_promocional") == 0


def test_virar_admin_devolve_a_vaga_da_propria_conta(app):
    conta = criar_pela_tela(app, "adauto@exemplo.com")
    assert da_conta(conta, "desconto_promocional") == 50
    resultado = app.test_cli_runner().invoke(args=["admin-do-sistema", "--email", "adauto@exemplo.com"])
    assert resultado.exit_code == 0 and "a vaga foi liberada" in resultado.output
    assert da_conta(conta, "desconto_promocional") == 0
