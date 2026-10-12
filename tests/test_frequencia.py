"""Testes da branch back-10-frequencia: registrar entrada, quem está na academia, ausentes, assiduidade e bloqueio de acesso."""
from datetime import date, datetime, timedelta

import pytest

from app.models import Aluno, Frequencia
from app.services import frequencia_service, painel_service
from tests.conftest import (campo, conta_de, contar, criar_aluno, criar_cobranca_em_aberto, criar_entrada, criar_plano,
                            criar_usuario, ligar_checkin, logar)

HOJE = date.today()
AGORA = datetime.now()
DIA = timedelta(days=1)


@pytest.fixture()
def academia(app):
    """Dona, recepção e instrutor de uma academia com o check-in LIGADO; alunos Ana e Bruno ativos e Caio inativo."""
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    ligar_checkin(conta)
    plano = criar_plano(dono, nome="Mensal")
    return {"dono": dono, "conta": conta, "plano": plano,
            "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
            "instrutor": criar_usuario("igor@teste.local", nome="Igor", conta=conta, papel="instrutor"),
            "ana": criar_aluno(dono, plano, "Ana Souza", "ana@exemplo.com", "111.222.333-96"),
            "bruno": criar_aluno(dono, plano, "Bruno Dias", "bruno@exemplo.com", "555.666.777-20"),
            "caio": criar_aluno(dono, plano, "Caio Inativo", "caio@exemplo.com", "123.456.789-09", ativo=False)}


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def do_painel(app, usuario_id):
    with app.test_request_context():
        from flask_login import login_user
        from app.extensions.database import db
        from app.models import User
        login_user(db.session.get(User, usuario_id))
        return painel_service.montar_painel()


def do_servico(app, usuario_id, funcao, *args, **kwargs):
    """Chama uma função do frequencia_service como se `usuario_id` estivesse logado."""
    with app.test_request_context():
        from flask_login import login_user
        from app.extensions.database import db
        from app.models import User
        login_user(db.session.get(User, usuario_id))
        return funcao(*args, **kwargs)


# ------------------------------------------------------------------ registrar entrada
def test_registrar_entrada_em_um_toque(app, academia):
    recepcao = como(app, academia["recepcao"])
    resposta = recepcao.post("/frequencia/checkin", data={"aluno_id": academia["ana"], "origem": "recepcao"})

    assert resposta.status_code == 302 and resposta.headers["Location"] == "/frequencia"
    with app.app_context():
        entrada = Frequencia.query.one()
        assert (entrada.aluno_id, entrada.conta_id, entrada.origem, entrada.instrutor_id) == (academia["ana"], academia["conta"], "recepcao", academia["recepcao"])
        assert abs((datetime.now() - entrada.data_hora_entrada).total_seconds()) < 60

    html = recepcao.get("/frequencia").get_data(as_text=True)
    assert 'class="rail"' in html and "Ana Souza" in html and "Recepção" in html and ">None<" not in html


def test_toque_repetido_nao_cria_outra_entrada(app, academia):
    recepcao = como(app, academia["recepcao"])
    for _ in range(3):
        recepcao.post("/frequencia/checkin", data={"aluno_id": academia["ana"]})
    assert contar(Frequencia, aluno_id=academia["ana"]) == 1

    criar_entrada(academia["dono"], academia["bruno"], AGORA - timedelta(minutes=61))     # mais de uma hora atrás: conta de novo
    recepcao.post("/frequencia/checkin", data={"aluno_id": academia["bruno"]})
    assert contar(Frequencia, aluno_id=academia["bruno"]) == 2


@pytest.mark.parametrize("caso", ["inativo", "bloqueado", "inexistente", "de_outra_academia", "sem_id"])
def test_entrada_recusada_nao_grava(app, academia, caso):
    if caso == "inativo":
        aluno_id = academia["caio"]
    elif caso == "bloqueado":
        aluno_id = academia["ana"]
        como(app, academia["dono"]).post(f"/alunos/{aluno_id}/acesso")
    elif caso == "de_outra_academia":
        outro = criar_usuario("outro@teste.local", nome="Otto")
        aluno_id = criar_aluno(outro, criar_plano(outro, nome="Plano-B"), "Vizinho", "v@exemplo.com", "987.654.321-00")
    else:
        aluno_id = 9999 if caso == "inexistente" else ""

    resposta = como(app, academia["recepcao"]).post("/frequencia/checkin", data={"aluno_id": aluno_id})

    assert resposta.status_code == 302 and contar(Frequencia) == 0


def test_mensalidade_atrasada_nao_barra_a_entrada(app, academia):
    criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE - 5 * DIA, HOJE + 25 * DIA)
    como(app, academia["recepcao"]).post("/frequencia/checkin", data={"aluno_id": academia["ana"]})
    assert contar(Frequencia, aluno_id=academia["ana"]) == 1      # entra, e a recepção é avisada da pendência


def test_instrutor_tambem_registra_entrada_mas_nao_exporta(app, academia):
    instrutor = como(app, academia["instrutor"])
    instrutor.post("/frequencia/checkin", data={"aluno_id": academia["ana"]})
    assert contar(Frequencia) == 1
    assert instrutor.get("/frequencia").status_code == 200 and instrutor.get("/frequencia/exportar").status_code == 403


# ------------------------------------------------------------------ a tela
def test_tela_conta_entradas_quem_esta_na_academia_e_o_pico(app, academia):
    agora = datetime(HOJE.year, HOJE.month, HOJE.day, 18, 30)
    criar_entrada(academia["dono"], academia["ana"], agora.replace(hour=7, minute=5))      # de manhã: já foi embora
    criar_entrada(academia["dono"], academia["ana"], agora.replace(hour=18, minute=10))
    criar_entrada(academia["dono"], academia["bruno"], agora.replace(hour=18, minute=20), origem="app")
    criar_entrada(academia["dono"], academia["bruno"], agora - DIA)                         # ontem: não entra na conta de hoje

    c = do_servico(app, academia["dono"], frequencia_service.contexto_da_tela, agora=agora)

    assert c["stats"] == {"entradas_hoje": 3, "na_academia": 2, "pico_hora": "18", "pico_qtd": 2, "media": 0}
    assert c["horas"][0] == "06" and c["horas"][-1] == "22" and sum(c["por_hora"]) == 3
    assert c["por_hora"][1] == 1 and c["por_hora"][12] == 2                                # barras das 07h e das 18h
    assert [(n["aluno"]["nome"], n["hora"]) for n in c["na_academia"]] == [("Bruno Dias", "18h20"), ("Ana Souza", "18h10")]
    assert [(e["aluno"]["nome"], e["hora"], e["origem"]) for e in c["entradas"]] == [
        ("Bruno Dias", "18h20", "App"), ("Ana Souza", "18h10", "Recepção"), ("Ana Souza", "07h05", "Recepção")]


def test_dia_sem_nenhuma_entrada_nao_inventa_pico(app, academia):
    html = como(app, academia["dono"]).get("/frequencia").get_data(as_text=True)
    assert html.count("--h") >= 1 and "06h" not in html and ">None<" not in html


def test_busca_ao_vivo_devolve_so_o_pedaco_e_so_da_propria_academia(app, academia):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    criar_aluno(outro, criar_plano(outro, nome="Plano-B"), "Ana Vizinha", "v@exemplo.com", "987.654.321-00")
    recepcao = como(app, academia["recepcao"])

    por_nome = recepcao.get("/frequencia?q=ana&partial=1").get_data(as_text=True)
    por_cpf = recepcao.get("/frequencia?q=555.666&partial=1").get_data(as_text=True)
    nada = recepcao.get("/frequencia?q=zzzz&partial=1").get_data(as_text=True)

    assert "<html" not in por_nome and "Ana Souza" in por_nome and "Ana Vizinha" not in por_nome and "Bruno" not in por_nome
    assert "Bruno Dias" in por_cpf and "Ana Souza" not in por_cpf
    assert "Ninguém com" in nada


def test_sugestoes_sem_busca_sao_quem_costuma_vir_nesta_hora(app, academia):
    agora = datetime(HOJE.year, HOJE.month, HOJE.day, 18, 30)
    for dias in (2, 4, 6):
        criar_entrada(academia["dono"], academia["bruno"], agora - dias * DIA)            # o Bruno vem sempre às 18h
    criar_entrada(academia["dono"], academia["ana"], (agora - 3 * DIA).replace(hour=7))   # a Ana vem de manhã

    nomes = [a["nome"] for a in do_servico(app, academia["dono"], frequencia_service.sugestoes, agora=agora)]
    assert nomes == ["Bruno Dias"]

    criar_entrada(academia["dono"], academia["bruno"], agora - timedelta(minutes=5))      # já entrou hoje: sai da sugestão
    nomes = [a["nome"] for a in do_servico(app, academia["dono"], frequencia_service.sugestoes, agora=agora)]
    assert "Bruno Dias" not in nomes and "Caio Inativo" not in nomes and "Ana Souza" in nomes


def test_exportar_csv_dos_checkins_de_hoje(app, academia):
    criar_entrada(academia["dono"], academia["ana"], AGORA.replace(hour=8, minute=15))
    criar_entrada(academia["dono"], academia["bruno"], AGORA - DIA)
    outro = criar_usuario("outro@teste.local", nome="Otto")
    ligar_checkin(conta_de(outro))
    vizinho = criar_aluno(outro, criar_plano(outro, nome="Plano-B"), "Vizinho Alheio", "v@exemplo.com", "987.654.321-00")
    criar_entrada(outro, vizinho, AGORA.replace(hour=9))

    resposta = como(app, academia["dono"]).get("/frequencia/exportar")
    texto = resposta.get_data(as_text=True)

    assert resposta.headers["Content-Type"].startswith("text/csv") and "checkins-hoje.csv" in resposta.headers["Content-Disposition"]
    assert texto.startswith("﻿Aluno;Horário;Plano;Origem;Situação") and "Ana Souza;08h15;Mensal;Recepção;ativo" in texto
    assert "Bruno" not in texto and "Vizinho" not in texto


# ------------------------------------------------------------------ check-in desligado
def test_com_o_checkin_desligado_a_tela_avisa_e_volta_ao_painel(app, academia):
    ligar_checkin(academia["conta"], False)
    dono = como(app, academia["dono"])
    for metodo, url in [("GET", "/frequencia"), ("POST", "/frequencia/checkin"), ("GET", "/frequencia/exportar")]:
        resposta = dono.open(url, method=metodo, data={"aluno_id": academia["ana"]})
        assert resposta.status_code == 302 and resposta.headers["Location"] == "/", f"{metodo} {url}"
    assert contar(Frequencia) == 0
    assert do_painel(app, academia["dono"])["k"]["ausentes"] is None
    assert "Frequência" not in dono.get(f"/alunos/{academia['ana']}").get_data(as_text=True)     # o perfil não mostra o cartão


# ------------------------------------------------------------------ "sem dado" x ausente
def test_sem_nenhuma_entrada_e_sem_dado_e_nao_zero(app, academia):
    painel = do_painel(app, academia["dono"])
    assert painel["k"]["ausentes"] == "—" and painel["listas"]["ausentes"] == []

    perfil = como(app, academia["dono"]).get(f"/alunos/{academia['ana']}").get_data(as_text=True)
    assert "Sem dado: nenhuma entrada registrada ainda." in perfil and "de assiduidade" not in perfil


def test_ausente_e_quem_tem_entrada_e_sumiu_ha_mais_de_15_dias(app, academia):
    criar_entrada(academia["dono"], academia["ana"], AGORA - 20 * DIA)       # sumiu há 20 dias
    criar_entrada(academia["dono"], academia["bruno"], AGORA - 15 * DIA)     # 15 dias exatos: ainda não é "mais de 15"
    criar_entrada(academia["dono"], academia["caio"], AGORA - 40 * DIA)      # inativo: não conta
    nunca = criar_aluno(academia["dono"], academia["plano"], "Nunca Veio", "nunca@exemplo.com", "987.654.320-29")

    painel = do_painel(app, academia["dono"])

    assert painel["k"]["ausentes"] == 1
    assert [(x["aluno"]["nome"], x["dias"]) for x in painel["listas"]["ausentes"]] == [("Ana Souza", 20)]
    # [back-16-mensagens] o aviso passou a levar o telefone do aluno (o botão do WhatsApp virou link)
    assert {"nome": "Ana Souza", "tipo": "frequencia", "tom": "yellow", "telefone": "11999990000", "motivo": "20 dias sem vir à academia"} in painel["alertas"]["risco"]
    assert painel["k"]["em_risco"] == 1 and nunca                              # quem nunca veio é "sem dado", não ausente

    html = como(app, academia["dono"]).get("/").get_data(as_text=True)
    assert "Ausentes há mais de 15 dias" in html and "20 dias sem vir" in html and ">None<" not in html


def test_assiduidade_no_perfil(app, academia):
    for dias in (0, 2, 3, 9, 29):                                            # 5 dias diferentes nos últimos 30
        criar_entrada(academia["dono"], academia["ana"], datetime(HOJE.year, HOJE.month, HOJE.day, 18, 42) - dias * DIA)
    criar_entrada(academia["dono"], academia["ana"], datetime(HOJE.year, HOJE.month, HOJE.day, 7, 0) - 2 * DIA)   # mesmo dia: não conta em dobro
    criar_entrada(academia["dono"], academia["ana"], AGORA - 45 * DIA)       # fora dos 30 dias

    freq = do_servico(app, academia["dono"], lambda: frequencia_service.frequencia_do(Aluno.query.get(academia["ana"])))

    assert freq["pct"] == round(5 / 30 * 100) and len(freq["semana"]) == 7 and freq["semana"][HOJE.weekday()] == 1
    assert freq["checkins"][0][1] == "18h42" and len(freq["checkins"]) == 3
    perfil = como(app, academia["dono"]).get(f"/alunos/{academia['ana']}").get_data(as_text=True)
    assert "17%" in perfil and "de assiduidade nos últimos 30 dias" in perfil and "Sem dado" not in perfil


# ------------------------------------------------------------------ bloquear e liberar acesso
def test_bloquear_e_liberar_acesso(app, academia):
    dono = como(app, academia["dono"])
    assert dono.get(f"/alunos/{academia['ana']}/acesso").status_code == 405        # só por POST

    resposta = dono.post(f"/alunos/{academia['ana']}/acesso")
    assert resposta.headers["Location"] == f"/alunos/{academia['ana']}" and campo(Aluno, academia["ana"], "acesso_liberado") is False
    assert "Liberar" in dono.get(f"/alunos/{academia['ana']}").get_data(as_text=True)

    dono.post(f"/alunos/{academia['ana']}/acesso")
    assert campo(Aluno, academia["ana"], "acesso_liberado") is True and campo(Aluno, academia["ana"], "ativo") is True


def test_busca_do_popup_de_acesso(app, academia):
    como(app, academia["dono"]).post(f"/alunos/{academia['bruno']}/acesso")
    recepcao = como(app, academia["recepcao"])

    html = recepcao.get("/alunos/acesso/busca?q=br").get_data(as_text=True)
    assert "<html" not in html and "Bruno Dias" in html and "Acesso bloqueado" in html and f'/alunos/{academia["bruno"]}/acesso' in html
    assert "Ana Souza" not in html
    assert "Bruno" not in recepcao.get("/alunos/acesso/busca?q=b").get_data(as_text=True)        # menos de 2 letras: não busca
    assert como(app, academia["instrutor"]).get("/alunos/acesso/busca?q=br").status_code == 403


def test_acesso_de_aluno_de_outra_academia_da_404(app, academia):
    outro = como(app, criar_usuario("outro@teste.local", nome="Otto"))
    assert outro.post(f"/alunos/{academia['ana']}/acesso").status_code == 404
    assert campo(Aluno, academia["ana"], "acesso_liberado") is True
    assert "Ana Souza" not in outro.get("/alunos/acesso/busca?q=ana").get_data(as_text=True)


def test_aluno_com_entrada_nao_pode_ser_excluido(app, academia):
    criar_entrada(academia["dono"], academia["ana"], AGORA)
    como(app, academia["dono"]).post(f"/alunos/{academia['ana']}/excluir")
    assert contar(Aluno, id=academia["ana"]) == 1 and contar(Frequencia) == 1
