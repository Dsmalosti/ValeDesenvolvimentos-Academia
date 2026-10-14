"""
Testes da branch back-24-assinatura: teste grátis de 2 meses, aviso de vencimento, bloqueio 7 dias depois,
o "PIX copia e cola" da mensalidade e a confirmação do pagamento.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.extensions.database import db
from app.helpers.datas import somar_meses
from app.helpers.pix import copia_e_cola, crc16
from app.models import Conta, Mensalidade
from app.services import assinatura_service
from tests.conftest import conta_de, contar, criar_personal, criar_usuario, logar
from tests import conftest

HOJE = date.today()
DIA = timedelta(days=1)


@pytest.fixture()
def academia(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    return {"dono": dono, "conta": conta, "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao")}


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


# ------------------------------------------------------------------ peças
def test_somar_meses_cai_no_ultimo_dia_quando_o_mes_e_mais_curto():
    assert somar_meses(date(2026, 10, 14), 2) == date(2026, 12, 14)
    assert somar_meses(date(2027, 1, 31), 1) == date(2027, 2, 28)
    assert somar_meses(date(2028, 1, 31), 1) == date(2028, 2, 29)                  # ano bissexto
    assert somar_meses(date(2026, 11, 30), 3) == date(2027, 2, 28)                 # passa a virada do ano


def test_codigo_pix_segue_o_padrao_do_banco_central():
    # exemplo do Manual de Padrões para Iniciação do Pix (Banco Central): o código termina com o CRC 1D3D
    exemplo = "00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-4266554400005204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***6304"
    assert crc16(exemplo) == "1D3D"

    codigo = copia_e_cola("60499733000144", "Vale Téc", "Tremembé", valor=Decimal("49.99"), identificador="VALETEC 7!")
    assert codigo.startswith("000201") and "0014br.gov.bcb.pix011460499733000144" in codigo
    assert "540549.99" in codigo and "5802BR" in codigo and "5908VALE TEC" in codigo and "6008TREMEMBE" in codigo
    assert "62120508VALETEC7" in codigo                                            # só letras e números no identificador
    assert codigo[-8:-4] == "6304" and codigo[-4:] == crc16(codigo[:-4])          # o CRC confere o código inteiro


# ------------------------------------------------------------------ teste grátis
def test_conta_nova_nasce_com_dois_meses_de_teste(app, academia):
    assert da_conta(academia["conta"], "teste_ate") == somar_meses(HOJE, 2) and da_conta(academia["conta"], "pago_ate") is None
    dono = como(app, academia["dono"])
    html = dono.get("/assinatura").get_data(as_text=True)
    assert "Teste grátis até" in html and somar_meses(HOJE, 2).strftime("%d/%m/%Y") in html and "R$ 49,99 por mês" in html
    assert "Seu teste grátis termina" not in dono.get("/").get_data(as_text=True)           # longe do fim: sem aviso no topo


def test_aviso_nos_ultimos_dias_do_teste_so_para_o_dono(app, academia):
    mudar(academia["conta"], teste_ate=HOJE + 3 * DIA)
    painel = como(app, academia["dono"]).get("/").get_data(as_text=True)
    assert "Seu teste grátis termina em 3 dias" in painel and 'href="/assinatura">Ver como pagar' in painel
    assert "teste grátis" not in como(app, academia["recepcao"]).get("/").get_data(as_text=True).lower()
    mudar(academia["conta"], teste_ate=HOJE)
    assert "Seu teste grátis termina hoje" in como(app, academia["dono"]).get("/").get_data(as_text=True)


def test_vencida_avisa_em_vermelho_e_tudo_continua_funcionando(app, academia):
    mudar(academia["conta"], teste_ate=HOJE - 7 * DIA)                            # último dia de tolerância
    dono, recepcao = como(app, academia["dono"]), como(app, academia["recepcao"])
    painel = dono.get("/").get_data(as_text=True)
    assert "note--red" in painel and "vencida desde" in painel and (HOJE + DIA).strftime("%d/%m/%Y") in painel     # bloqueia amanhã
    assert "Avise o responsável pela conta" in recepcao.get("/").get_data(as_text=True)
    assert dono.get("/alunos").status_code == 200
    assert dono.post("/configuracoes/funcionalidade", data={"chave": "lembretes", "ligado": "0"}).status_code == 302


# ------------------------------------------------------------------ bloqueio
def test_bloqueada_so_abre_a_tela_de_pagamento(app, academia):
    mudar(academia["conta"], teste_ate=HOJE - 8 * DIA)                            # 8 dias depois do vencimento
    dono = como(app, academia["dono"])
    for url in ("/", "/alunos", "/frequencia", "/configuracoes", "/mensagens"):
        assert dono.get(url).headers.get("Location") == "/assinatura", url
    tela = dono.get("/assinatura").get_data(as_text=True)
    assert "Sua conta está bloqueada" in tela and "guardados até" in tela and (HOJE + 30 * DIA).strftime("%d/%m/%Y") in tela
    assert 'action="/sair"' in tela and "vale.informatica02@gmail.com" in tela
    assert dono.post("/configuracoes/funcionalidade", data={"chave": "lembretes", "ligado": "0"}).status_code == 403
    assert da_conta(academia["conta"], "lembretes_ligados") is True                # o envio recusado não gravou nada
    for url in ("/termos", "/privacidade", "/saude"):
        assert dono.get(url).status_code == 200, url
    assert dono.post("/sair").status_code == 302

    recepcao = como(app, academia["recepcao"]).get("/assinatura").get_data(as_text=True)
    assert "Quem paga é o responsável pela conta" in recepcao and "Diana Teste" in recepcao and "pix-codigo" not in recepcao


def test_outra_conta_nao_e_afetada_pelo_bloqueio(app, academia):
    mudar(academia["conta"], teste_ate=HOJE - 30 * DIA)
    outro = criar_usuario("outro@teste.local", nome="Otto")
    assert como(app, outro).get("/alunos").status_code == 200


# ------------------------------------------------------------------ o código PIX na tela
def test_codigo_pix_aparece_com_a_chave_configurada(app, academia):
    dono = como(app, academia["dono"])
    assert "O código PIX ainda não está disponível aqui" in dono.get("/assinatura").get_data(as_text=True)

    app.config["VALE_TEC_PIX_CHAVE"] = "60499733000144"
    html = dono.get("/assinatura").get_data(as_text=True)
    assert 'id="pix-codigo"' in html and "011460499733000144" in html and "540549.99" in html and "data-copiar=" in html
    assert "pix-codigo" not in como(app, academia["recepcao"]).get("/assinatura").get_data(as_text=True)        # quem paga é o dono

    personal = criar_personal()
    tela = como(app, personal).get("/assinatura").get_data(as_text=True)
    assert "Personal Trainer" in tela and "R$ 24,99 por mês" in tela and "540524.99" in tela


# ------------------------------------------------------------------ pagamento
def test_pagar_em_dia_continua_do_vencimento(app, academia):
    fim = HOJE + 10 * DIA
    mudar(academia["conta"], teste_ate=fim)
    with conftest._APP.app_context():
        conta = db.session.get(Conta, academia["conta"])
        registro = assinatura_service.registrar_pagamento(conta)
        assert (registro.periodo_inicio, registro.periodo_fim, registro.valor) == (fim + DIA, somar_meses(fim, 1), Decimal("49.99"))
        assert conta.pago_ate == somar_meses(fim, 1) and assinatura_service.situacao(conta)["estado"] == "em_dia"
        with pytest.raises(ValueError):
            assinatura_service.registrar_pagamento(conta, meses=0)
    html = como(app, academia["dono"]).get("/assinatura").get_data(as_text=True)
    assert "Pago até" in html and "Pagamentos confirmados" in html and "R$ 49,99" in html


def test_pagar_depois_do_bloqueio_comeca_no_dia_do_pagamento_e_libera(app, academia):
    mudar(academia["conta"], teste_ate=HOJE - 20 * DIA)
    dono = como(app, academia["dono"])
    assert dono.get("/alunos").headers.get("Location") == "/assinatura"
    with conftest._APP.app_context():
        assinatura_service.registrar_pagamento(db.session.get(Conta, academia["conta"]), meses=2)
    assert da_conta(academia["conta"], "pago_ate") == somar_meses(HOJE, 2)
    assert dono.get("/alunos").status_code == 200 and contar(Mensalidade) == 1


def test_isolamento_a_tela_mostra_so_a_propria_conta(app, academia):
    with conftest._APP.app_context():
        assinatura_service.registrar_pagamento(db.session.get(Conta, academia["conta"]), valor="777.00")
    outro = criar_usuario("outro@teste.local", nome="Otto")
    html = como(app, outro).get("/assinatura").get_data(as_text=True)
    assert "777" not in html and "Pagamentos confirmados" not in html


def test_sem_login_a_tela_pede_login_e_o_aviso_nao_aparece(app, academia):
    assert app.test_client().get("/assinatura").headers["Location"].startswith("/login")
    assert "note--red" not in app.test_client().get("/login").get_data(as_text=True)


# ------------------------------------------------------------------ linha de comando
def test_comandos_de_linha_de_comando(app, academia):
    runner = app.test_cli_runner()
    lista = runner.invoke(args=["assinaturas"])
    assert lista.exit_code == 0 and "Academia de Diana" in lista.output and "Teste grátis" in lista.output

    ate = HOJE + 90 * DIA
    teste = runner.invoke(args=["assinatura-teste", "--conta", str(academia["conta"]), "--ate", ate.isoformat()])
    assert teste.exit_code == 0 and da_conta(academia["conta"], "teste_ate") == ate

    paga = runner.invoke(args=["assinatura-paga", "--conta", str(academia["conta"])])
    assert paga.exit_code == 0 and da_conta(academia["conta"], "pago_ate") == somar_meses(ate, 1)
    assert runner.invoke(args=["assinatura-paga", "--conta", "9999"]).exit_code != 0
