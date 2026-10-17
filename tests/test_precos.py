"""
Testes da branch back-28-precos-e-promocao: o preço final do Vale Tec (R$ 59,99 academia e R$ 29,99 personal, igual para
todas as contas) e como ele aparece: "preço de lançamento, 50% de desconto", com o preço de tabela riscado.
"""
from datetime import date, timedelta
from decimal import Decimal

from app.extensions.database import db
from app.models import Conta
from app.services import assinatura_service
from tests import conftest
from tests.conftest import conta_de, criar_personal, criar_usuario, logar

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


# ------------------------------------------------------------------ preço
def test_preco_cobrado_e_preco_de_tabela():
    assert assinatura_service.preco(Conta(modelo="academia")) == Decimal("59.99")
    assert assinatura_service.preco(Conta(modelo="personal")) == Decimal("29.99")
    assert assinatura_service.preco_de_tabela(Conta(modelo="academia")) == Decimal("119.98")
    assert assinatura_service.preco_de_tabela(Conta(modelo="personal")) == Decimal("59.98")
    # o desconto anunciado bate com a conta: a tabela é o dobro do preço cobrado
    for modelo in ("academia", "personal"):
        conta = Conta(modelo=modelo)
        cobrado, tabela = assinatura_service.preco(conta), assinatura_service.preco_de_tabela(conta)
        assert cobrado == (tabela * (100 - assinatura_service.DESCONTO_DE_LANCAMENTO) / 100).quantize(Decimal("0.01"))


def test_toda_conta_nova_paga_o_mesmo_preco_nao_importa_a_ordem(app):
    """Antes (primeira versão desta branch) só as 10 primeiras contas tinham desconto. Agora é igual para todas."""
    for i in range(12):
        resposta = app.test_client().post("/criar-conta", data={"tipo": "academia", "nome": f"Pessoa {i} Silva",
                                                                "email": f"p{i}@exemplo.com", "senha": SENHA})
        assert resposta.status_code == 302
    with conftest._APP.app_context():
        assert {assinatura_service.preco(c) for c in Conta.query.all()} == {Decimal("59.99")}


# ------------------------------------------------------------------ telas
def test_tela_de_criar_conta_mostra_o_preco_de_lancamento(app):
    html = app.test_client().get("/criar-conta").get_data(as_text=True)
    assert "Preço de lançamento: 50% de desconto" in html
    assert "R$\u00a059,99 por mês para academia (de <s>R$\u00a0119,98</s>)" in html and "R$\u00a029,99 para personal (de <s>R$\u00a059,98</s>)" in html
    assert "restam" not in html and "primeiras" not in html


def test_tela_de_assinatura_e_pix_com_o_preco_final(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    app.config["VALE_TEC_PIX_CHAVE"] = "60499733000144"
    html = como(app, dono).get("/assinatura").get_data(as_text=True)
    assert "R$ 59,99 por mês" in html and '<s class="faint">R$ 119,98</s>' in html
    assert "Preço de lançamento: 50% de desconto" in html and "540559.99" in html     # o PIX cobra o preço final


def test_aviso_do_topo_lembra_o_desconto(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    mudar(conta_de(dono), teste_ate=HOJE + timedelta(days=3))
    painel = como(app, dono).get("/").get_data(as_text=True)
    assert "custa R$ 59,99 por mês" in painel and "Preço de lançamento, com 50% de desconto." in painel


def test_personal_ve_o_preco_dele(app):
    personal = criar_personal("pedro@teste.local", nome="Pedro")
    html = como(app, personal).get("/assinatura").get_data(as_text=True)
    assert "R$ 29,99 por mês" in html and "R$ 59,98" in html


def test_sem_desconto_as_telas_deixam_de_mostrar_o_preco_riscado(app, monkeypatch):
    """Se um dia o desconto acabar (DESCONTO_DE_LANCAMENTO = 0), nenhuma tela mostra o preço riscado."""
    monkeypatch.setattr(assinatura_service, "DESCONTO_DE_LANCAMENTO", 0)
    dono = criar_usuario("dono@teste.local", nome="Diana")
    assinatura = como(app, dono).get("/assinatura").get_data(as_text=True)
    criar = app.test_client().get("/criar-conta").get_data(as_text=True)
    assert "R$ 59,99 por mês" in assinatura and "R$ 119,98" not in assinatura and "Preço de lançamento" not in assinatura
    assert "Preço de lançamento" not in criar
