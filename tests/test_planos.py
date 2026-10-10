"""Testes da branch back-08-planos: telas de planos do front novo (lista, criar, editar, pausar e reativar)."""
from datetime import date
from decimal import Decimal

import pytest

from app.models import Plano
from app.services import painel_service
from tests.conftest import (campo, contar, criar_aluno, criar_pagamento, criar_plano, criar_usuario, conta_de, logar,
                            _salvar)

HOJE = date.today()


@pytest.fixture()
def academia(app):
    """Dono, recepção e instrutor de uma academia com dois planos ativos (Mensal e Anual) e um pausado."""
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    dados = {"dono": dono, "conta": conta,
             "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
             "instrutor": criar_usuario("igor@teste.local", nome="Igor", conta=conta, papel="instrutor"),
             "mensal": criar_plano(dono, nome="Mensal"),
             "anual": criar_plano(dono, nome="Anual"),
             "pausado": _salvar(Plano(nome="Plano Antigo", valor=80, duracao_dias=30, descricao="", ativo=False,
                                      instrutor_id=dono, conta_id=conta))}
    dados["ana"] = criar_aluno(dono, dados["mensal"], "Ana Souza", "ana@exemplo.com", "111.222.333-96")
    criar_aluno(dono, dados["mensal"], "Bia Lima", "bia@exemplo.com", "555.666.777-20")
    criar_aluno(dono, dados["anual"], "Caio Reis", "caio@exemplo.com", "123.456.789-09")
    return dados


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def formulario(**trocas):
    """Um plano válido, como o navegador envia. `trocas` muda campos; trocar por None tira o campo do envio."""
    dados = {"nome": "Trimestral", "valor": "1.234,56", "duracao_dias": "90", "descricao": "Três meses com desconto.",
             "ativo": "1", "avaliacoes_incluidas": "2"}
    dados.update(trocas)
    return {k: v for k, v in dados.items() if v is not None}


# ------------------------------------------------------------------ lista
def test_lista_mostra_os_planos_da_academia_com_os_numeros(app, academia):
    criar_pagamento(academia["dono"], academia["ana"], 300, HOJE, HOJE)       # Ana está no Mensal
    outro = criar_usuario("outro@teste.local", nome="Otto")
    criar_plano(outro, nome="Plano-da-Vizinha")

    html = como(app, academia["dono"]).get("/planos").get_data(as_text=True)

    assert 'class="rail"' in html                                             # layout novo
    assert "Mensal" in html and "Anual" in html and "Plano Antigo" in html
    assert "Plano-da-Vizinha" not in html
    assert "3 planos cadastrados" in html and "ticket médio de R$ 100,00 por aluno" in html   # 300 / 3 alunos ativos
    assert "100% do faturamento do mês" in html and "2 alunos" in html and "Inativo" in html
    assert html.index("Anual") < html.index("Mensal") < html.index("Plano Antigo")      # ativos por nome, pausado no fim
    assert ">None<" not in html


def test_numeros_da_tela_de_planos_batem_com_o_grafico_do_painel(app, academia):
    criar_pagamento(academia["dono"], academia["ana"], 300, HOJE, HOJE)
    with app.test_request_context():
        from flask_login import login_user
        from app.extensions.database import db
        from app.models import User
        login_user(db.session.get(User, academia["dono"]))
        do_painel = {x["plano_id"]: (x["alunos"], x["valor"], x["pct"]) for x in painel_service.montar_painel()["planos_fat"]}
        da_tela, _ = painel_service.planos_com_faturamento()

    for plano_id, numeros in do_painel.items():
        assert (da_tela[plano_id]["alunos"], da_tela[plano_id]["valor"], da_tela[plano_id]["pct"]) == numeros
    assert academia["pausado"] in da_tela and academia["pausado"] not in do_painel    # a tela mostra também o pausado


def test_lista_com_editar_preenche_o_painel_lateral(app, academia):
    html = como(app, academia["dono"]).get(f"/planos?editar={academia['mensal']}").get_data(as_text=True)
    assert f'action="/planos/{academia["mensal"]}/editar"' in html and 'value="100,00"' in html and "Cancelar edição" in html

    outro = criar_usuario("outro@teste.local", nome="Otto")
    de_fora = como(app, academia["dono"]).get(f"/planos?editar={criar_plano(outro, nome='Plano-B')}").get_data(as_text=True)
    assert "Plano-B" not in de_fora and "Cancelar edição" not in de_fora       # id de outra academia: como se não existisse


def test_instrutor_consulta_os_planos_mas_nao_ve_o_dinheiro(app, academia):
    criar_pagamento(academia["dono"], academia["ana"], 300, HOJE, HOJE)
    instrutor = como(app, academia["instrutor"])
    html = instrutor.get("/planos").get_data(as_text=True)

    assert "Mensal" in html and "R$ 100,00" in html                            # nome e preço, sim
    assert "100% do faturamento" not in html and "ticket médio de R$ 0,00" in html
    for metodo, url in [("GET", "/planos/novo"), ("POST", "/planos/novo"), ("GET", f"/planos/{academia['mensal']}/editar"),
                        ("POST", f"/planos/{academia['mensal']}/editar"), ("POST", f"/planos/{academia['mensal']}/alternar")]:
        assert instrutor.open(url, method=metodo, data=formulario()).status_code == 403, f"{metodo} {url}"
    assert campo(Plano, academia["mensal"], "ativo") is True and contar(Plano, nome="Trimestral") == 0


# ------------------------------------------------------------------ criar
def test_criar_plano(app, academia):
    recepcao = como(app, academia["recepcao"])
    assert "Criar plano" in recepcao.get("/planos/novo").get_data(as_text=True)

    resposta = recepcao.post("/planos/novo", data=formulario())

    assert resposta.status_code == 302 and resposta.headers["Location"] == "/planos"
    with app.app_context():
        plano = Plano.query.filter_by(nome="Trimestral").one()
        assert plano.valor == Decimal("1234.56") and plano.duracao_dias == 90 and plano.ativo is True
        assert plano.avaliacoes_incluidas == 2 and plano.descricao == "Três meses com desconto."
        assert plano.conta_id == academia["conta"] and plano.instrutor_id == academia["recepcao"]


def test_criar_pelo_painel_do_desktop_sem_o_campo_de_avaliacoes(app, academia):
    # o painel lateral não tem "Avaliação física inclusa", e o interruptor desligado não manda `ativo`
    como(app, academia["dono"]).post("/planos/novo", data=formulario(avaliacoes_incluidas=None, ativo=None, valor="89,9"))
    with app.app_context():
        plano = Plano.query.filter_by(nome="Trimestral").one()
        assert plano.avaliacoes_incluidas == 0 and plano.ativo is False and plano.valor == Decimal("89.90")


@pytest.mark.parametrize("trocas, mensagem", [
    ({"nome": "   "}, "Dê um nome ao plano."),
    ({"nome": "x" * 101}, "no máximo 100 letras"),
    ({"nome": "mensal"}, "Já existe um plano com este nome."),            # sem diferenciar maiúscula
    ({"valor": ""}, "Informe o valor em reais"),
    ({"valor": "0,00"}, "Informe um valor maior que zero."),
    ({"valor": "149.90"}, "Informe o valor em reais"),                    # ponto como centavo viraria R$ 14.990,00
    ({"valor": "-10,00"}, "Informe o valor em reais"),
    ({"valor": "abc"}, "Informe o valor em reais"),
    ({"valor": "999.999.999,00"}, "Valor alto demais."),
    ({"duracao_dias": "0"}, "A duração vai de 1 a 1095 dias."),
    ({"duracao_dias": "2000"}, "A duração vai de 1 a 1095 dias."),
    ({"duracao_dias": "trinta"}, "A duração vai de 1 a 1095 dias."),
])
def test_plano_invalido_avisa_e_nao_grava(app, academia, trocas, mensagem):
    antes = contar(Plano)
    resposta = como(app, academia["dono"]).post("/planos/novo", data=formulario(**trocas))
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 200 and mensagem in html
    assert contar(Plano) == antes
    assert "Três meses com desconto." in html                              # devolve o que foi digitado


def test_campos_sem_lugar_para_mensagem_avisam_no_topo(app, academia):
    dono = como(app, academia["dono"])
    # o aviso do topo vai dentro de um JSON (os acentos saem codificados): confere o trecho sem acento
    assert "500 letras." in dono.post("/planos/novo", data=formulario(descricao="x" * 501)).get_data(as_text=True)
    dono.post("/planos/novo", data=formulario(avaliacoes_incluidas="7"))
    assert contar(Plano, nome="Trimestral") == 0


def test_mesmo_nome_em_outra_academia_pode(app, academia):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    assert como(app, outro).post("/planos/novo", data=formulario(nome="Mensal")).status_code == 302
    assert contar(Plano, nome="Mensal") == 2


def test_nome_com_html_nao_vira_codigo_na_tela(app, academia):
    dono = como(app, academia["dono"])
    dono.post("/planos/novo", data=formulario(nome="<script>alert(1)</script>"))
    html = dono.get("/planos").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html


# ------------------------------------------------------------------ editar
def test_editar_plano(app, academia):
    dono = como(app, academia["dono"])
    tela = dono.get(f"/planos/{academia['mensal']}/editar").get_data(as_text=True)
    assert "Editar plano" in tela and 'value="Mensal"' in tela and 'value="100,00"' in tela
    assert "Quem está nesse plano" in tela and "Os 2 alunos atuais" in tela

    resposta = dono.post(f"/planos/{academia['mensal']}/editar", data=formulario(nome="Mensal", valor="159,90", duracao_dias="30"))

    assert resposta.status_code == 302 and resposta.headers["Location"] == "/planos"
    assert campo(Plano, academia["mensal"], "valor") == Decimal("159.90")      # o próprio nome não conta como repetido
    assert campo(Plano, academia["mensal"], "avaliacoes_incluidas") == 2


def test_editar_pelo_painel_do_desktop_nao_apaga_as_avaliacoes(app, academia):
    dono = como(app, academia["dono"])
    dono.post(f"/planos/{academia['mensal']}/editar", data=formulario(nome="Mensal", avaliacoes_incluidas="4"))
    dono.post(f"/planos/{academia['mensal']}/editar", data=formulario(nome="Mensal", avaliacoes_incluidas=None, valor="120,00"))

    assert campo(Plano, academia["mensal"], "valor") == Decimal("120.00")
    assert campo(Plano, academia["mensal"], "avaliacoes_incluidas") == 4       # o campo não veio: fica como estava


def test_editar_invalido_devolve_o_que_foi_digitado_e_os_numeros_do_plano(app, academia):
    resposta = como(app, academia["dono"]).post(f"/planos/{academia['mensal']}/editar",
                                                data=formulario(nome="Mensal Plus", duracao_dias="0"))
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 200 and "A duração vai de 1 a 1095 dias." in html
    assert 'value="Mensal Plus"' in html and 'value="1234,56"' in html and "Os 2 alunos atuais" in html
    assert campo(Plano, academia["mensal"], "nome") == "Mensal"


def test_plano_de_outra_academia_da_404(app, academia):
    outro = como(app, criar_usuario("outro@teste.local", nome="Otto"))
    for metodo, url in [("GET", "/planos/{}/editar"), ("POST", "/planos/{}/editar"), ("POST", "/planos/{}/alternar")]:
        assert outro.open(url.format(academia["mensal"]), method=metodo, data=formulario()).status_code == 404, f"{metodo} {url}"
    assert campo(Plano, academia["mensal"], "nome") == "Mensal" and campo(Plano, academia["mensal"], "ativo") is True


# ------------------------------------------------------------------ pausar e reativar
def test_alternar_pausa_e_reativa_sem_apagar(app, academia):
    dono = como(app, academia["dono"])
    assert dono.get(f"/planos/{academia['mensal']}/alternar").status_code == 405       # só por POST

    assert dono.post(f"/planos/{academia['mensal']}/alternar").headers["Location"] == "/planos"
    assert campo(Plano, academia["mensal"], "ativo") is False and contar(Plano, id=academia["mensal"]) == 1
    # pausado some do cadastro de aluno, mas a Ana continua nele
    cadastro = dono.get("/alunos/novo").get_data(as_text=True)
    assert "Mensal · R$" not in cadastro and "Anual · R$" in cadastro
    assert "Mensal" in dono.get(f"/alunos/{academia['ana']}").get_data(as_text=True)

    # o botão "Desativar plano" do celular manda o formulário inteiro para /alternar: os campos são ignorados
    dono.post(f"/planos/{academia['mensal']}/alternar", data=formulario(nome="Outro Nome"))
    assert campo(Plano, academia["mensal"], "ativo") is True and campo(Plano, academia["mensal"], "nome") == "Mensal"
