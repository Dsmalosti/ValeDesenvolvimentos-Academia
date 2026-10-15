"""Testes da branch back-11-relatorios: painel administrativo (formas, ponto de equilíbrio, custos, retenção, churn, risco e lançamentos)."""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from werkzeug.datastructures import MultiDict

from app.models import Aluno, Custo
from app.services import painel_service, relatorio_service
from tests.conftest import (campo, conta_de, contar, criar_aluno, criar_cobranca_em_aberto, criar_custo, criar_entrada,
                            criar_pagamento, criar_plano, criar_usuario, ligar_checkin, logar)

HOJE = date.today()
DIA = timedelta(days=1)
MESES = relatorio_service.MESES


@pytest.fixture()
def academia(app):
    """Dona, recepção e instrutor; plano Mensal (R$ 100); alunos Ana, Bruno e Carla, todos ativos."""
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    plano = criar_plano(dono, nome="Mensal")
    return {"dono": dono, "conta": conta, "plano": plano,
            "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
            "instrutor": criar_usuario("igor@teste.local", nome="Igor", conta=conta, papel="instrutor"),
            "ana": criar_aluno(dono, plano, "Ana Souza", "ana@exemplo.com", "111.222.333-96"),
            "bruno": criar_aluno(dono, plano, "Bruno Dias", "bruno@exemplo.com", "555.666.777-20"),
            "carla": criar_aluno(dono, plano, "Carla Lima", "carla@exemplo.com", "123.456.789-09")}


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def logado(app, usuario_id, funcao, *args, **kwargs):
    """Chama uma função de serviço como se `usuario_id` estivesse logado."""
    with app.test_request_context():
        from flask_login import login_user
        from app.extensions.database import db
        from app.models import User
        login_user(db.session.get(User, usuario_id))
        return funcao(*args, **kwargs)


def contexto(app, academia, hoje=None, **argumentos):
    return logado(app, academia["dono"], relatorio_service.contexto_do_painel, MultiDict(argumentos), hoje)


def mexer(app, aluno_id, **campos):
    """Altera colunas de um aluno direto no banco (para montar histórico: data de cadastro, de inativação...)."""
    with app.app_context():
        from app.extensions.database import db
        aluno = db.session.get(Aluno, aluno_id)
        for nome, valor in campos.items():
            setattr(aluno, nome, valor)
        db.session.commit()


def ha(dias):
    return datetime.now() - dias * DIA


# ------------------------------------------------------------------ tela vazia
def test_painel_administrativo_de_academia_nova_nao_inventa_numero(app, academia):
    html = como(app, academia["dono"]).get("/relatorios/painel").get_data(as_text=True)

    assert 'class="rail"' in html and "Painel administrativo" in html
    assert "Cadastre os custos fixos do mês" in html                   # sem custos não há ponto de equilíbrio
    assert html.count("Sem dado ainda") == 2                           # retenção e comparação com o mês anterior
    assert "Ninguém com nota abaixo de 50 agora." in html and "Nenhum lançamento com esse filtro." in html
    assert f"recebidos em {MESES[HOJE.month - 1]}" in html and f"Lançamentos de {MESES[HOJE.month - 1]}" in html
    assert ">None<" not in html and "None" not in html.replace("NoneType", "") and "setembro" not in html.lower().replace(MESES[HOJE.month - 1], "")
    assert "Último fechamento" not in html


# ------------------------------------------------------------------ faturamento
def test_faturamento_por_forma_junta_debito_e_credito_em_cartao(app, academia):
    for aluno, valor, forma in [("ana", 100, "pix"), ("bruno", 50, "debito"), ("carla", 50, "credito"), ("ana", 50, "dinheiro")]:
        criar_pagamento(academia["dono"], academia[aluno], valor, HOJE, HOJE + 30 * DIA, forma=forma)

    c = contexto(app, academia)

    assert c["recebido"] == 250.0
    assert [(f["nome"], f["pct"], f["texto"], f["cor"]) for f in c["formas"]] == [
        ("PIX", 40, "R$ 100", "blue"), ("Cartão", 40, "R$ 100", "yellow-chart"), ("Dinheiro", 20, "R$ 50", "teal")]
    assert c["grafico"]["valores"][-1] == 250 and len(c["grafico"]["labels"]) == 12 and c["grafico"]["destaque"] == 11
    assert c["ticket"] == painel_ticket(app, academia)                 # o mesmo número do card do painel


def painel_ticket(app, academia):
    return logado(app, academia["dono"], painel_service.montar_painel)["k"]["ticket"]


def test_periodo_muda_o_que_entra_na_conta(app, academia):
    hoje = date(2026, 10, 12)
    criar_pagamento(academia["dono"], academia["ana"], 100, date(2026, 10, 5), date(2026, 11, 4))      # este mês (segunda, 05/10)
    criar_pagamento(academia["dono"], academia["bruno"], 70, date(2026, 9, 8), date(2026, 10, 8))      # mês passado, até o dia 12
    criar_pagamento(academia["dono"], academia["carla"], 30, date(2026, 9, 25), date(2026, 10, 25))    # mês passado, depois do dia 12
    criar_pagamento(academia["dono"], academia["ana"], 400, date(2026, 3, 10), date(2026, 4, 9))       # há 7 meses

    mes = contexto(app, academia, hoje)
    assert (mes["recebido"], mes["periodo_txt"], mes["mes_txt"]) == (100.0, "em outubro", "Outubro de 2026")
    assert mes["variacao"] == "+43% vs setembro"                        # 100 contra os 70 de setembro ATÉ o dia 12
    assert contexto(app, academia, hoje, periodo="semana")["recebido"] == 0.0
    tres = contexto(app, academia, hoje, periodo="3m")
    assert (tres["recebido"], tres["periodo_txt"], tres["periodo_de"]) == (200.0, "nos últimos 3 meses", "dos últimos 3 meses")
    assert contexto(app, academia, hoje, periodo="ano")["recebido"] == 600.0
    assert contexto(app, academia, hoje, periodo="invalido")["periodo"] == "mes"


# ------------------------------------------------------------------ custos e ponto de equilíbrio
def test_custos_criar_editar_e_remover(app, academia):
    recepcao = como(app, academia["recepcao"])
    resposta = recepcao.post("/relatorios/custos", data={"descricao": "  Aluguel  ", "valor": "6.800,00"})
    assert resposta.headers["Location"] == "/relatorios/painel#custos"
    with app.app_context():
        custo = Custo.query.one()
        assert (custo.descricao, custo.valor, custo.conta_id) == ("Aluguel", Decimal("6800.00"), academia["conta"])
        cid = custo.id

    recepcao.post("/relatorios/custos", data={"id": str(cid), "descricao": "Aluguel do galpão", "valor": "7.000,00"})
    assert campo(Custo, cid, "descricao") == "Aluguel do galpão" and campo(Custo, cid, "valor") == Decimal("7000.00") and contar(Custo) == 1

    html = recepcao.get("/relatorios/painel").get_data(as_text=True)
    assert "Aluguel do galpão" in html and "R$ 7.000" in html and "1 lançados" in html

    recepcao.post(f"/relatorios/custos/{cid}/excluir")
    assert contar(Custo) == 0


@pytest.mark.parametrize("dados", [{"descricao": "", "valor": "100,00"}, {"descricao": "Luz", "valor": "0,00"}, {"descricao": "Luz", "valor": "abc"},
                                   {"descricao": "Luz", "valor": "100.00"}, {"descricao": "x" * 101, "valor": "100,00"},
                                   {"id": "999", "descricao": "Luz", "valor": "100,00"}])
def test_custo_invalido_nao_grava(app, academia, dados):
    como(app, academia["dono"]).post("/relatorios/custos", data=dados)
    assert contar(Custo) == 0


def test_ponto_de_equilibrio_acima_abaixo_e_na_proporcao_do_periodo(app, academia):
    criar_custo(academia["dono"], "Aluguel", 300)
    dono = como(app, academia["dono"])
    abaixo = dono.get("/relatorios/painel").get_data(as_text=True)
    assert "R$ 300 abaixo do mínimo" in abaixo and ">Faltou<" in abaixo and "Cadastre os custos" not in abaixo

    criar_pagamento(academia["dono"], academia["ana"], 500, HOJE, HOJE + 30 * DIA)
    acima = dono.get("/relatorios/painel").get_data(as_text=True)
    assert "R$ 200 acima do mínimo" in acima and ">Sobrou<" in acima

    tres = contexto(app, academia, periodo="3m")
    assert (tres["custos_total"], tres["minimo"], tres["sobra"]) == (300.0, 900.0, -400.0)       # 3 meses de custo
    assert tres["gauge_max"] >= tres["minimo"] / 0.55 and tres["gauge_max"] % 1000 == 0


# ------------------------------------------------------------------ lançamentos
def test_lancamentos_filtro_e_csv(app, academia):
    criar_pagamento(academia["recepcao"], academia["ana"], 100, HOJE, HOJE + 30 * DIA, forma="pix")
    criar_pagamento(academia["recepcao"], academia["bruno"], 80, HOJE, HOJE + 30 * DIA, forma="credito")
    criar_cobranca_em_aberto(academia["dono"], academia["carla"], 100, HOJE - 3 * DIA, HOJE + 27 * DIA)     # já começou: em atraso
    outro = criar_usuario("outro@teste.local", nome="Otto")
    vizinho = criar_aluno(outro, criar_plano(outro, nome="Plano-B"), "Vizinho Alheio", "v@exemplo.com", "987.654.321-00")
    criar_pagamento(outro, vizinho, 999, HOJE, HOJE + 30 * DIA)

    todos = contexto(app, academia)["lancamentos"]
    assert sorted((x["aluno"]["nome"], x["forma"], x["valor"], x["situacao"], x["origem"]) for x in todos) == [
        ("Ana Souza", "PIX", 100.0, "pago", "manual"), ("Bruno Dias", "Cartão", 80.0, "pago", "manual"),
        ("Carla Lima", "—", 100.0, "atrasado", None)]
    assert [x["aluno"]["nome"] for x in contexto(app, academia, forma="Cartão")["lancamentos"]] == ["Bruno Dias"]
    assert [x["aluno"]["nome"] for x in contexto(app, academia, situacao="atrasado")["lancamentos"]] == ["Carla Lima"]
    assert contexto(app, academia, forma="cheque")["filtro"] == {"forma": "", "situacao": ""}

    dono = como(app, academia["dono"])
    html = dono.get("/relatorios/painel?forma=PIX").get_data(as_text=True)
    assert "Ana Souza" in html and "Bruno Dias" not in html and "Vizinho" not in html
    resposta = dono.get("/relatorios/exportar?formato=csv&situacao=pago")
    texto = resposta.get_data(as_text=True)
    assert resposta.headers["Content-Type"].startswith("text/csv") and "lancamentos-" in resposta.headers["Content-Disposition"]
    assert texto.startswith("﻿Aluno;Data;Plano;Forma;Valor;Situação;Confirmação")
    assert f"Ana Souza;{HOJE.strftime('%d/%m/%Y')};Mensal;PIX;100,00;pago;recepção" in texto and "Carla" not in texto and "Vizinho" not in texto


def test_excel_e_pdf_ainda_nao_existem_e_relatorios_leva_ao_painel(app, academia):
    dono = como(app, academia["dono"])
    for formato in ("xlsx", "pdf"):
        assert dono.get(f"/relatorios/exportar?formato={formato}").headers["Location"] == "/relatorios/painel"
    assert dono.get("/relatorios?periodo=3m&forma=PIX&outro=x").headers["Location"] == "/relatorios/painel?periodo=3m&forma=PIX"


# ------------------------------------------------------------------ quem pode e isolamento
def test_instrutor_nao_ve_nada_do_administrativo(app, academia):
    custo = criar_custo(academia["dono"], "Aluguel", 300)
    instrutor = como(app, academia["instrutor"])
    for metodo, url in [("GET", "/relatorios"), ("GET", "/relatorios/painel"), ("GET", "/relatorios/exportar"),
                        ("POST", "/relatorios/custos"), ("POST", f"/relatorios/custos/{custo}/excluir")]:
        assert instrutor.open(url, method=metodo, data={"descricao": "Luz", "valor": "10,00"}).status_code == 403, f"{metodo} {url}"
    assert contar(Custo) == 1


def test_custo_de_outra_academia_nao_aparece_nem_pode_ser_mexido(app, academia):
    custo = criar_custo(academia["dono"], "Folha da Diana", 300)        # ("Aluguel" não serve: é o exemplo escrito no campo)
    outro = como(app, criar_usuario("outro@teste.local", nome="Otto"))

    assert "Folha da Diana" not in outro.get("/relatorios/painel").get_data(as_text=True)
    outro.post("/relatorios/custos", data={"id": str(custo), "descricao": "Invadido", "valor": "1,00"})
    outro.post(f"/relatorios/custos/{custo}/excluir")
    assert campo(Custo, custo, "descricao") == "Folha da Diana" and contar(Custo) == 1


# ------------------------------------------------------------------ data de inativação
def test_data_de_inativacao_e_guardada_e_apagada_sozinha(app, academia):
    dono = como(app, academia["dono"])
    assert campo(Aluno, academia["ana"], "data_inativacao") is None

    dono.post(f"/alunos/{academia['ana']}/inativar")
    quando = campo(Aluno, academia["ana"], "data_inativacao")
    assert quando is not None and abs((datetime.now() - quando).total_seconds()) < 60

    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    dono.post(f"/cobrancas/{cobranca}/confirmar", data={"forma": "pix"})          # pagar reativa
    assert campo(Aluno, academia["ana"], "ativo") is True and campo(Aluno, academia["ana"], "data_inativacao") is None

    dono.post(f"/alunos/status/{academia['bruno']}")                              # o botão de status da tela antiga também conta
    assert campo(Aluno, academia["bruno"], "ativo") is False and campo(Aluno, academia["bruno"], "data_inativacao") is not None


def test_grafico_de_ativos_do_painel_conta_quem_saiu_depois(app, academia):
    for aluno in ("ana", "bruno", "carla"):
        mexer(app, academia[aluno], data_cadastro=ha(100))
    mexer(app, academia["carla"], ativo=False)                                     # saiu hoje: nos meses passados ela era ativa
    serie = logado(app, academia["dono"], painel_service.montar_painel)["serie"]
    assert serie["valores"][-1] == 2 and serie["valores"][-2] == 3


# ------------------------------------------------------------------ retenção e comparação
def test_retencao_so_usa_quem_tem_historico(app, academia):
    mexer(app, academia["ana"], data_cadastro=ha(100))                             # ficou os 100 dias
    mexer(app, academia["bruno"], data_cadastro=ha(100))
    mexer(app, academia["bruno"], ativo=False)
    mexer(app, academia["bruno"], data_inativacao=ha(60))                          # saiu com 40 dias de casa
    mexer(app, academia["carla"], data_cadastro=ha(10))                            # nova: só entra no marco zero
    antigo = criar_aluno(academia["dono"], academia["plano"], "Inativo Antigo", "ia@exemplo.com", "987.654.320-29", ativo=False)
    mexer(app, antigo, data_cadastro=ha(200))                                      # inativo sem data: não se sabe quanto ficou

    retencao = contexto(app, academia)["retencao"]

    assert retencao["labels"] == ["0", "30", "60", "90"] and retencao["valores"] == [100, 100, 50, 50]


def test_comparativo_churn_e_ausentes(app, academia):
    ligar_checkin(academia["conta"])
    hoje = date(2026, 10, 12)
    for aluno in ("ana", "bruno", "carla"):
        mexer(app, academia[aluno], data_cadastro=datetime(2026, 6, 1))
    extra = criar_aluno(academia["dono"], academia["plano"], "Davi Saiu", "davi@exemplo.com", "987.654.320-29")
    mexer(app, extra, data_cadastro=datetime(2026, 6, 1), ativo=False)
    mexer(app, extra, data_inativacao=datetime(2026, 9, 20))                       # saiu em setembro
    mexer(app, academia["carla"], ativo=False)
    mexer(app, academia["carla"], data_inativacao=datetime(2026, 10, 5))           # saiu em outubro
    criar_entrada(academia["dono"], academia["ana"], datetime(2026, 9, 1, 18))     # sumida há mais de 15 dias nos dois momentos
    criar_entrada(academia["dono"], academia["bruno"], datetime(2026, 10, 10, 18))

    linhas = {x["nome"]: x for x in contexto(app, academia, hoje)["comparativo"]}

    assert round(linhas["Churn"]["ant"], 1) == 25.0 and round(linhas["Churn"]["atu"], 1) == 33.3      # 1 de 4, depois 1 de 3
    assert (linhas["Ausentes +15d"]["ant"], linhas["Ausentes +15d"]["atu"]) == (1, 1)
    assert all(0 <= x["p_ant"] <= 100 and 0 <= x["p_atu"] <= 100 for x in linhas.values())
    assert "Inadimplência" not in linhas                                           # sem nenhum pagamento não há o que comparar


# ------------------------------------------------------------------ risco e mapa
def test_risco_lista_quem_tem_nota_abaixo_de_50(app, academia):
    ligar_checkin(academia["conta"])
    for aluno in ("ana", "bruno", "carla"):
        mexer(app, academia[aluno], data_cadastro=ha(200))
    criar_pagamento(academia["dono"], academia["ana"], 100, HOJE - 50 * DIA, HOJE - 20 * DIA)        # 20 dias de atraso: 100 - 60 = 40
    criar_pagamento(academia["dono"], academia["bruno"], 100, HOJE - 12 * DIA, HOJE + 18 * DIA)      # em dia...
    criar_entrada(academia["dono"], academia["bruno"], ha(40))                                       # ...mas sumiu há 40 dias: 100 - 50 = 50
    criar_pagamento(academia["dono"], academia["carla"], 100, HOJE - 40 * DIA, HOJE - 10 * DIA)      # 10 dias de atraso (30)...
    criar_entrada(academia["dono"], academia["carla"], ha(30))                                       # ...e 30 dias sem vir (46): 100 - 76 = 24

    c = contexto(app, academia)

    assert [(r["aluno"]["nome"], r["score"], r["motivo"]) for r in c["risco"]] == [
        ("Carla Lima", 24, "30 dias sem vir"), ("Ana Souza", 40, "20 dias sem pagar")]
    assert c["risco_total"] == 2
    html = como(app, academia["dono"]).get("/relatorios/painel").get_data(as_text=True)
    assert "Carla Lima" in html and "Ver os 2" in html and "wa.me/55" in html


def test_mapa_de_movimento_mostra_o_pico(app, academia):
    ligar_checkin(academia["conta"])
    hoje = date(2026, 10, 12)                                                      # segunda-feira
    for dias in (4, 11, 18):                                                       # três quintas-feiras, às 18h
        criar_entrada(academia["dono"], academia["ana"], datetime(2026, 10, 12, 18, 30) - dias * DIA)
    criar_entrada(academia["dono"], academia["bruno"], datetime(2026, 10, 10, 7, 0))               # um sábado de manhã
    criar_entrada(academia["dono"], academia["bruno"], datetime(2026, 8, 1, 7, 0))                 # fora dos 28 dias

    mapa = contexto(app, academia, hoje)["mapa"]

    assert mapa["pico"] == "quinta 18h" and mapa["horas"] == ["06h", "09h", "12h", "15h", "18h", "21h"]
    assert mapa["niveis"][4][3] == 4 and mapa["niveis"][0][5] == 2 and sum(map(sum, mapa["niveis"])) == 6
    html = como(app, academia["dono"]).get("/relatorios/painel").get_data(as_text=True)
    assert "Movimento por dia e horário" in html

    ligar_checkin(academia["conta"], False)
    assert "Movimento por dia e horário" not in como(app, academia["dono"]).get("/relatorios/painel").get_data(as_text=True)
