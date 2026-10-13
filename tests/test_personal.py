"""Testes da branch back-17-personal: pacotes de sessões, saldo, renovação, agenda, painel, configurações e mensagens da conta de personal trainer."""
from datetime import date, datetime, timedelta

import pytest

from app.models import Aluno, Cobranca, Conta, Plano, Sessao
from tests.conftest import (campo, conta_de, contar, criar_aluno, criar_compra, criar_pacote, criar_personal, criar_plano, criar_sessao,
                            criar_usuario, logar)

HOJE = date.today()
DIA = timedelta(days=1)


def br(dia):
    return dia.strftime("%d/%m/%Y")


@pytest.fixture()
def personal(app):
    """
    Paulo, personal trainer, com três pacotes (8 sessões por R$ 960, 4 por R$ 520 e a sessão avulsa de R$ 140).
    Ana comprou e pagou o Pacote 8; Bia comprou o Pacote 4 e ainda não pagou; Caio está inativo; Duda nunca comprou.
    """
    dono = criar_personal()
    p8, p4, p1 = criar_pacote(dono, "Pacote 8", 8, 960), criar_pacote(dono, "Pacote 4", 4, 520), criar_pacote(dono, "Sessão avulsa", 1, 140)
    ana = criar_aluno(dono, p8, "Ana Souza", "ana@exemplo.com", "111.222.333-96")
    bia = criar_aluno(dono, p4, "Bia Lima", "bia@exemplo.com", "555.666.777-20")
    caio = criar_aluno(dono, p4, "Caio Inativo", "caio@exemplo.com", "123.456.789-09", ativo=False)
    duda = criar_aluno(dono, p8, "Duda Reis", "duda@exemplo.com", "222.333.444-05")
    criar_compra(dono, ana, p8, paga=True, quando=datetime.utcnow() - timedelta(days=20))
    criar_compra(dono, bia, p4, paga=False, quando=datetime.utcnow() - timedelta(days=3))
    return {"dono": dono, "conta": conta_de(dono), "p8": p8, "p4": p4, "p1": p1, "ana": ana, "bia": bia, "caio": caio, "duda": duda}


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def saldo(app, dono_id, aluno_id):
    """O pacote do aluno, calculado como o sistema calcula, com `dono_id` logado."""
    from flask_login import login_user
    from app.extensions.database import db
    from app.models import User
    from app.services import pacote_service
    with app.test_request_context():
        login_user(db.session.get(User, dono_id))
        return pacote_service.pacote_do(db.session.get(Aluno, aluno_id))


def sessao_valida(personal, **trocas):
    dados = {"aluno_id": personal["ana"], "data": br(HOJE + 2 * DIA), "horario": "07:30", "duracao": "45", "local": "parque", "repete": "unica", "acao": "marcar"}
    dados.update(trocas)
    return dados


# ------------------------------------------------------------------ painel
def test_painel_do_personal_e_outra_tela(app, personal):
    criar_sessao(personal["dono"], personal["ana"], HOJE, "07:30")
    html = como(app, personal["dono"]).get("/").get_data(as_text=True)
    for trecho in ("Olá, Paulo", "Pacotes acabando", "Sessões hoje", "Marcar sessão", "Criar pacote", "Participação de cada pacote", "Personal trainer"):
        assert trecho in html, trecho
    assert "Vencimentos no mês" not in html and ">None<" not in html and "None%" not in html and "meta de None" not in html
    assert "sobram 8 sessões" in html and 'href="https://wa.me/5511999990000"' in html           # tabela de alunos com o saldo e o WhatsApp de verdade


def test_painel_conta_pacotes_acabando_e_avisa_da_ultima_sessao(app, personal):
    dono = personal["dono"]
    for i in range(7):                                                                           # Ana usou 7 das 8: sobra 1
        criar_sessao(dono, personal["ana"], HOJE - (i + 1) * DIA, status="concluida")
    for i in range(2):                                                                           # Bia usou 2 das 4: sobram 2
        criar_sessao(dono, personal["bia"], HOJE - (i + 1) * DIA, "10:00", status="concluida")
    html = como(app, dono).get("/").get_data(as_text=True)
    from tests.conftest import numero_do_card
    assert numero_do_card(html, "Pacotes acabando") == "2"
    assert "Pacote acaba na próxima sessão" in html and "2 alunos precisam renovar logo" in html
    assert html.index("Ana Souza</b><span class=\"pop-item__linha tone-txt-yellow\">Pacote 8 · sobra 1 sessão") > 0


def test_academia_continua_com_o_painel_dela(app, personal):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    html = como(app, dono).get("/").get_data(as_text=True)
    assert "Pacotes acabando" not in html and "Sessões hoje" not in html and "Vencimentos no mês" in html


# ------------------------------------------------------------------ pacotes
def test_lista_e_formulario_de_pacotes(app, personal):
    dono = como(app, personal["dono"])
    lista = dono.get("/planos").get_data(as_text=True)
    for trecho in ("Pacotes", "3 pacotes · ticket médio", "8 sessões · R$ 120,00 cada", "1 sessão · R$ 140,00 cada", "Novo pacote", "Criar pacote"):
        assert trecho in lista, trecho
    assert "duracao_dias" not in lista and ">None<" not in lista
    form = dono.get("/planos/novo").get_data(as_text=True)
    assert 'name="quantidade_sessoes"' in form and 'name="duracao_dias"' not in form and "Dados do pacote" in form
    editar = dono.get(f"/planos/{personal['p8']}/editar").get_data(as_text=True)
    assert 'name="quantidade_sessoes" type="number" min="1" max="100" inputmode="numeric" value="8"' in editar and "Quem está nesse pacote" in editar


def test_criar_e_editar_pacote(app, personal):
    dono = como(app, personal["dono"])
    resposta = dono.post("/planos/novo", data={"nome": " Pacote 12 ", "valor": "1.440,00", "quantidade_sessoes": "12", "descricao": "três por semana",
                                               "ativo": "1", "avaliacoes_incluidas": "1"})
    assert resposta.headers["Location"] == "/planos"
    with app.app_context():
        p = Plano.query.filter_by(nome="Pacote 12").one()
        assert (p.quantidade_sessoes, float(p.valor), p.duracao_dias, p.avaliacoes_incluidas, p.conta_id, p.ativo) == (12, 1440.0, 90, 1, personal["conta"], True)
        novo = p.id
        p.duracao_dias = 120
        from app.extensions.database import db
        db.session.commit()
    dono.post(f"/planos/{novo}/editar", data={"nome": "Pacote 12", "valor": "1.500,00", "quantidade_sessoes": "10", "descricao": "", "ativo": "1"})
    assert (campo(Plano, novo, "quantidade_sessoes"), float(campo(Plano, novo, "valor")), campo(Plano, novo, "duracao_dias")) == (10, 1500.0, 120)   # a validade não muda
    assert dono.post(f"/planos/{novo}/alternar").headers["Location"] == "/planos" and campo(Plano, novo, "ativo") is False


@pytest.mark.parametrize("trocas, aviso", [({"quantidade_sessoes": "0"}, "A quantidade vai de 1 a 100 sessões."), ({"quantidade_sessoes": "101"}, "A quantidade vai de 1 a 100"),
                                           ({"quantidade_sessoes": "oito"}, "A quantidade vai de 1 a 100"), ({"quantidade_sessoes": ""}, "A quantidade vai de 1 a 100"),
                                           ({"nome": ""}, "Dê um nome ao pacote."), ({"nome": "pacote 8"}, "Já existe um pacote com este nome."),
                                           ({"valor": "0,00"}, "Informe um valor maior que zero.")])
def test_pacote_invalido_avisa_e_nao_grava(app, personal, trocas, aviso):
    dados = {"nome": "Pacote 12", "valor": "1.440,00", "quantidade_sessoes": "12", "descricao": "", "ativo": "1"}
    dados.update(trocas)
    resposta = como(app, personal["dono"]).post("/planos/novo", data=dados)
    assert resposta.status_code == 200 and aviso in resposta.get_data(as_text=True) and contar(Plano) == 3


def test_plano_de_academia_nao_ganha_sessoes(app, personal):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    como(app, dono).post("/planos/novo", data={"nome": "Mensal", "valor": "149,90", "duracao_dias": "30", "descricao": "", "ativo": "1", "quantidade_sessoes": "12"})
    with app.app_context():
        p = Plano.query.filter_by(nome="Mensal").one()
        assert (p.quantidade_sessoes, p.duracao_dias) == (None, 30)


# ------------------------------------------------------------------ saldo
def test_saldo_e_o_que_comprou_menos_o_que_abateu(app, personal):
    dono = personal["dono"]
    assert saldo(app, dono, personal["ana"]) == {"id": personal["p8"], "nome": "Pacote 8", "total": 8, "usadas": 0, "saldo": 8, "valor": 960.0,
                                                 "valor_sessao": 120.0, "avulso": False}
    for i in range(3):
        criar_sessao(dono, personal["ana"], HOJE - (i + 1) * DIA, status="concluida")
    criar_sessao(dono, personal["ana"], HOJE - 5 * DIA, status="cancelada")                      # cancelada não conta
    criar_sessao(dono, personal["ana"], HOJE + DIA)                                              # agendada ainda não conta
    criar_sessao(dono, personal["ana"], HOJE - 6 * DIA, status="concluida", abateu=False)        # fechada sem saldo: fora do pacote
    pacote = saldo(app, dono, personal["ana"])
    assert (pacote["total"], pacote["usadas"], pacote["saldo"]) == (8, 3, 5)
    assert saldo(app, dono, personal["duda"])["saldo"] == 0 and saldo(app, dono, personal["duda"])["nome"] == "Pacote 8"      # nunca comprou


def test_lista_e_perfil_mostram_o_saldo_no_lugar_do_vencimento(app, personal):
    dono = como(app, personal["dono"])
    criar_sessao(personal["dono"], personal["ana"], HOJE - DIA, status="concluida")
    lista = dono.get("/alunos").get_data(as_text=True)
    assert "sobram 7 sessões" in lista and "sobram 4 sessões" in lista and "pacote encerrado" in lista and "sem saldo" in lista
    perfil = dono.get(f"/alunos/{personal['ana']}").get_data(as_text=True)
    assert "Sobram 7 sessões" in perfil and ">None<" not in perfil


def test_pendente_e_quem_tem_cobranca_em_aberto_e_nao_quem_passou_da_validade(app, personal):
    dono = personal["dono"]
    with app.app_context():                                                                      # a compra da Ana foi há 200 dias: a validade passou
        from app.extensions.database import db
        c = Cobranca.query.filter_by(aluno_id=personal["ana"]).one()
        c.data_inicio, c.data_vencimento = HOJE - 200 * DIA, HOJE - 110 * DIA
        db.session.commit()
    html = como(app, dono).get("/alunos?status=pendente").get_data(as_text=True)
    assert "Bia Lima" in html and "Ana Souza" not in html                                        # Bia deve o pacote; Ana está em dia


# ------------------------------------------------------------------ renovar
def test_tela_de_renovar_mostra_o_novo_saldo(app, personal):
    dono = personal["dono"]
    for i in range(3):
        criar_sessao(dono, personal["ana"], HOJE - (i + 1) * DIA, status="concluida")
    html = como(app, dono).get(f"/alunos/{personal['ana']}/renovar").get_data(as_text=True)
    for trecho in ("Renovar pacote", "Renovar com qual pacote?", "Pacote 8 · sobram 5 sessões", 'data-e-novo="13 sessões"', 'data-e-novo="9 sessões"',
                   'data-e-novo="6 sessões"', "As 5 sessões que sobraram do pacote atual somam no saldo novo.", "R$ 120,00 cada"):
        assert trecho in html, trecho
    assert "novo_venc" not in html and ">None<" not in html


def test_renovar_soma_o_que_sobrou(app, personal):
    dono = personal["dono"]
    for i in range(3):
        criar_sessao(dono, personal["ana"], HOJE - (i + 1) * DIA, status="concluida")
    cliente = como(app, dono)
    resposta = cliente.post(f"/alunos/{personal['ana']}/renovar", data={"plano_id": personal["p4"], "acao": "sem_cobrar"})
    assert resposta.headers["Location"] == f"/alunos/{personal['ana']}"
    pacote = saldo(app, dono, personal["ana"])
    assert (pacote["nome"], pacote["total"], pacote["usadas"], pacote["saldo"], pacote["valor_sessao"]) == ("Pacote 4", 9, 0, 9, 130.0)
    with app.app_context():
        nova = Cobranca.query.filter_by(aluno_id=personal["ana"], status="pendente").one()
        assert (nova.quantidade_sessoes, float(nova.valor), nova.tipo, nova.plano_id) == (4, 520.0, "renovacao", personal["p4"])
    assert campo(Aluno, personal["ana"], "plano_id") == personal["p4"]
    # renovar de novo com a cobrança ainda em aberto TROCA a compra pendente, não soma outra
    cliente.post(f"/alunos/{personal['ana']}/renovar", data={"plano_id": personal["p8"], "acao": "sem_cobrar"})
    assert saldo(app, dono, personal["ana"])["saldo"] == 13 and contar(Cobranca, aluno_id=personal["ana"]) == 2


def test_renovar_e_receber_leva_a_cobranca_de_pacote(app, personal):
    cliente = como(app, personal["dono"])
    destino = cliente.post(f"/alunos/{personal['ana']}/renovar", data={"plano_id": personal["p8"], "acao": "receber"}).headers["Location"]
    assert destino.startswith("/cobrancas/") and "/receber" in destino
    tela = cliente.get(destino).get_data(as_text=True)
    assert "Renovação do pacote" in tela and "<dt>Pacote</dt>" in tela and " dias" not in tela.split("<dt>Pacote</dt>")[1].split("</dd>")[0]
    cobranca = int(destino.split("/")[2])
    cliente.post(f"/cobrancas/{cobranca}/confirmar", data={"forma": "pix"})
    assert "Pacote quitado" in cliente.get(destino).get_data(as_text=True)
    assert saldo(app, personal["dono"], personal["ana"])["saldo"] == 16                          # pagar não credita de novo


def test_renovar_com_pacote_de_outra_conta_ou_inativo(app, personal):
    outro = criar_personal("outro@teste.local", "Otto")
    de_fora = criar_pacote(outro, "Pacote do vizinho", 50, 10)
    parado = criar_pacote(personal["dono"], "Parado", 20, 100, ativo=False)
    cliente = como(app, personal["dono"])
    for pacote in (de_fora, parado, "abc"):
        cliente.post(f"/alunos/{personal['ana']}/renovar", data={"plano_id": pacote, "acao": "sem_cobrar"})
    assert saldo(app, personal["dono"], personal["ana"])["saldo"] == 8 and contar(Cobranca, aluno_id=personal["ana"]) == 1


# ------------------------------------------------------------------ agenda
def test_agenda_vazia_e_so_para_personal(app, personal):
    html = como(app, personal["dono"]).get("/agenda").get_data(as_text=True)
    assert 'class="rail"' in html and "Nenhuma sessão marcada a partir de hoje." in html and "0 sessões" in html and ">None<" not in html
    academia = como(app, criar_usuario("dono@teste.local", nome="Diana"))
    for url in ("/agenda", "/agenda/nova", "/agenda/1"):
        assert academia.get(url).headers["Location"] == "/", url
    assert academia.post("/agenda/nova", data={}).status_code == 404 and academia.post("/agenda/1/concluir").status_code == 404


def test_marcar_sessao(app, personal):
    cliente = como(app, personal["dono"])
    escolher = cliente.get("/agenda/nova").get_data(as_text=True)
    assert "Com quem?" in escolher and "Ana Souza" in escolher and "sobram 8 sessões" in escolher and "Caio Inativo" not in escolher
    form = cliente.get(f"/agenda/nova?aluno={personal['ana']}").get_data(as_text=True)
    for trecho in ("Marcar sessão", "Pacote de 8 · sobram 8 sessões", ">06:00<", ">21:30<", "Estúdio", "Casa do aluno", "Toda semana", br(HOJE + DIA)):
        assert trecho in form, trecho
    assert "última sessão do pacote" not in form

    resposta = cliente.post("/agenda/nova", data=sessao_valida(personal))
    assert resposta.headers["Location"] == "/agenda"
    with app.app_context():
        s = Sessao.query.one()
        assert (s.conta_id, s.aluno_id, s.instrutor_id, s.data, s.hora, s.duracao, s.local, s.repete, s.status, s.abateu) == (
            personal["conta"], personal["ana"], personal["dono"], HOJE + 2 * DIA, "07:30", 45, "parque", "unica", "agendada", False)
    agenda = cliente.get("/agenda").get_data(as_text=True)
    assert "Ana Souza" in agenda and "07:30" in agenda and "Treino · 45min · Parque" in agenda and "Agendada" in agenda


@pytest.mark.parametrize("trocas, aviso", [({"data": br(HOJE - DIA)}, "Escolha hoje ou uma data futura."), ({"data": "amanhã"}, "Data inválida. Use dd/mm/aaaa."),
                                           ({"data": br(HOJE + 400 * DIA)}, "Escolha uma data dentro de um ano."), ({"horario": "03:00"}, "Escolha um horário."),
                                           ({"horario": ""}, "Escolha um horário.")])
def test_sessao_invalida_avisa_e_nao_grava(app, personal, trocas, aviso):
    resposta = como(app, personal["dono"]).post("/agenda/nova", data=sessao_valida(personal, **trocas))
    assert resposta.status_code == 200 and aviso in resposta.get_data(as_text=True) and contar(Sessao) == 0


def test_sessao_no_mesmo_horario_inativo_outra_conta_e_local_desligado(app, personal):
    cliente = como(app, personal["dono"])
    cliente.post("/agenda/nova", data=sessao_valida(personal))
    ocupado = cliente.post("/agenda/nova", data=sessao_valida(personal, aluno_id=personal["bia"]))
    assert ocupado.status_code == 200 and "Você já tem sessão com Ana neste horário." in ocupado.get_data(as_text=True)
    assert cliente.post("/agenda/nova", data=sessao_valida(personal, aluno_id=personal["caio"])).headers["Location"] == "/agenda/nova"       # inativo
    outro = criar_personal("outro@teste.local", "Otto")
    vizinho = criar_aluno(outro, criar_pacote(outro), "Vizinho", "v@exemplo.com", "987.654.321-00")
    assert cliente.post("/agenda/nova", data=sessao_valida(personal, aluno_id=vizinho)).status_code == 404
    assert contar(Sessao) == 1

    cliente.post("/configuracoes/locais", data={"ativos": ["estudio", "online"], "endereco_estudio": "Rua XV, 220"})
    cliente.post("/agenda/nova", data=sessao_valida(personal, aluno_id=personal["bia"], horario="08:00", local="parque"))       # parque foi desligado
    with app.app_context():
        assert Sessao.query.filter_by(aluno_id=personal["bia"]).one().local == "estudio"


def test_remarcar_muda_a_mesma_sessao(app, personal):
    cliente = como(app, personal["dono"])
    antiga = criar_sessao(personal["dono"], personal["ana"], HOJE + DIA, "09:00")
    da_bia = criar_sessao(personal["dono"], personal["bia"], HOJE + DIA, "10:00")
    form = cliente.get(f"/agenda/nova?aluno={personal['ana']}&remarcar={antiga}").get_data(as_text=True)
    assert "Remarcar sessão" in form and f'name="remarcar" value="{antiga}"' in form and 'name="horario" value="09:00"' in form

    cliente.post("/agenda/nova", data=sessao_valida(personal, remarcar=antiga, horario="18:00"))
    assert (campo(Sessao, antiga, "hora"), campo(Sessao, antiga, "data"), campo(Sessao, antiga, "status")) == ("18:00", HOJE + 2 * DIA, "agendada")
    assert contar(Sessao) == 2
    # "remarcar" apontando para a sessão de OUTRO aluno não mexe nela: marca uma nova para a Ana
    cliente.post("/agenda/nova", data=sessao_valida(personal, remarcar=da_bia, horario="19:00"))
    assert campo(Sessao, da_bia, "hora") == "10:00" and contar(Sessao) == 3


def test_concluir_abate_uma_do_saldo_uma_vez_so(app, personal):
    cliente = como(app, personal["dono"])
    hoje = criar_sessao(personal["dono"], personal["ana"], HOJE, "07:30")
    assert cliente.post(f"/agenda/{hoje}/concluir").headers["Location"] == "/agenda"
    assert (campo(Sessao, hoje, "status"), campo(Sessao, hoje, "abateu")) == ("concluida", True) and campo(Sessao, hoje, "concluida_em") is not None
    assert saldo(app, personal["dono"], personal["ana"])["saldo"] == 7
    assert cliente.post(f"/agenda/{hoje}/concluir").headers["Location"] == f"/agenda/{hoje}"                      # tocar de novo: avisa e não abate outra vez
    assert saldo(app, personal["dono"], personal["ana"])["saldo"] == 7

    futura = criar_sessao(personal["dono"], personal["ana"], HOJE + DIA, "07:30")
    cliente.post(f"/agenda/{futura}/concluir")
    assert campo(Sessao, futura, "status") == "agendada"                                                          # sessão de amanhã não se fecha hoje
    atrasada = criar_sessao(personal["dono"], personal["ana"], HOJE - 2 * DIA, "07:30")
    cliente.post(f"/agenda/{atrasada}/concluir")
    assert campo(Sessao, atrasada, "status") == "concluida" and saldo(app, personal["dono"], personal["ana"])["saldo"] == 6   # a que ficou sem fechar, pode


def test_concluir_sem_saldo_fecha_fora_do_pacote(app, personal):
    cliente = como(app, personal["dono"])
    sessao = criar_sessao(personal["dono"], personal["duda"], HOJE, "07:30")                                      # Duda nunca comprou
    cliente.post(f"/agenda/{sessao}/concluir")
    assert (campo(Sessao, sessao, "status"), campo(Sessao, sessao, "abateu")) == ("concluida", False)
    cliente.post(f"/alunos/{personal['duda']}/renovar", data={"plano_id": personal["p4"], "acao": "sem_cobrar"})
    assert saldo(app, personal["dono"], personal["duda"])["saldo"] == 4                                           # a sessão fora do pacote não vira dívida de sessão


def test_cancelar_nao_abate(app, personal):
    cliente = como(app, personal["dono"])
    sessao = criar_sessao(personal["dono"], personal["ana"], HOJE, "07:30")
    assert cliente.get(f"/agenda/{sessao}/cancelar").status_code == 405                                           # só por POST
    assert cliente.post(f"/agenda/{sessao}/cancelar").headers["Location"] == "/agenda"
    assert campo(Sessao, sessao, "status") == "cancelada" and saldo(app, personal["dono"], personal["ana"])["saldo"] == 8
    cliente.post(f"/agenda/{sessao}/concluir")
    assert campo(Sessao, sessao, "status") == "cancelada"                                                         # cancelada não vira presença
    fechada = criar_sessao(personal["dono"], personal["ana"], HOJE - DIA, status="concluida")
    cliente.post(f"/agenda/{fechada}/cancelar")
    assert campo(Sessao, fechada, "status") == "concluida"                                                        # e a fechada não se cancela


def test_sessao_semanal_anda_uma_semana_ao_ser_concluida(app, personal):
    cliente = como(app, personal["dono"])
    semanal = criar_sessao(personal["dono"], personal["ana"], HOJE, "07:30", repete="semanal", local="casa", duracao=45)
    cliente.post(f"/agenda/{semanal}/concluir")
    with app.app_context():
        proxima = Sessao.query.filter_by(status="agendada").one()
        assert (proxima.data, proxima.hora, proxima.local, proxima.duracao, proxima.repete, proxima.aluno_id) == (HOJE + 7 * DIA, "07:30", "casa", 45, "semanal", personal["ana"])
        da_proxima = proxima.id
    cliente.post(f"/agenda/{da_proxima}/cancelar")                                                                # cancelar interrompe a repetição
    assert contar(Sessao) == 2 and contar(Sessao, status="agendada") == 0


def test_agenda_agrupa_por_dia_e_avisa_de_quem_esta_na_ultima_sessao(app, personal):
    dono = personal["dono"]
    for i in range(7):
        criar_sessao(dono, personal["ana"], HOJE - (i + 1) * DIA, status="concluida")                             # Ana fica com 1
    criar_sessao(dono, personal["ana"], HOJE, "07:30")
    criar_sessao(dono, personal["bia"], HOJE, "18:00", duracao=90)
    criar_sessao(dono, personal["bia"], HOJE + DIA, "09:00")
    criar_sessao(dono, personal["bia"], HOJE, "20:00", status="cancelada")
    html = como(app, dono).get("/agenda").get_data(as_text=True)
    assert f"Hoje, {HOJE.strftime('%d/%m')}" in html and f"Amanhã, {(HOJE + DIA).strftime('%d/%m')}" in html
    assert "2 sessões · 2h30 de trabalho" in html and "1 sessão · 1h de trabalho" in html and "20:00" not in html
    assert "R$ 250" in html                                                                                      # 960/8 + 520/4 = 120 + 130
    assert "1 pacote acabando" in html and "Ana tem 1 sessão restante" in html.replace("\n", " ").replace("  ", " ")
    form = como(app, dono).get(f"/agenda/nova?aluno={personal['ana']}").get_data(as_text=True)
    assert "Essa é a última sessão do pacote" in form and "Marcar e renovar o pacote" in form


def test_detalhe_da_sessao(app, personal):
    dono = personal["dono"]
    for i in range(3):
        criar_sessao(dono, personal["ana"], HOJE - (i + 1) * DIA, status="concluida")
    hoje, futura = criar_sessao(dono, personal["ana"], HOJE, "07:30", local="parque"), criar_sessao(dono, personal["ana"], HOJE + 3 * DIA, "07:30")
    cliente = como(app, dono)
    html = cliente.get(f"/agenda/{hoje}").get_data(as_text=True)
    for trecho in ("Ana Souza", "Hoje às 07:30", "07:30 — 08:30", "1 hora", "Parque · treino ao ar livre", "3 de 8 usadas", "8 sessões · R$ 960,00", "R$ 120,00",
                   "5 sessões", 'href="https://wa.me/5511999990000"', "Marcar presença e fechar sessão", "Remarcar", "Cancelar a sessão?", "sem ficha de treino"):
        assert trecho in html, trecho
    assert "já confirmou" not in html and "Ainda não confirmou" not in html and ">None<" not in html              # a tela não inventa lembrete
    assert "Marcar presença e fechar sessão" not in cliente.get(f"/agenda/{futura}").get_data(as_text=True)
    cliente.post(f"/agenda/{hoje}/concluir")
    fechada = cliente.get(f"/agenda/{hoje}").get_data(as_text=True)
    assert "Sessão fechada" in fechada and "Marcar presença" not in fechada and "4 de 8 usadas" in fechada


def test_marcar_e_renovar_leva_para_a_renovacao(app, personal):
    resposta = como(app, personal["dono"]).post("/agenda/nova", data=sessao_valida(personal, acao="renovar"))
    assert resposta.headers["Location"] == f"/alunos/{personal['ana']}/renovar" and contar(Sessao) == 1


# ------------------------------------------------------------------ configurações
def test_configuracoes_do_personal(app, personal):
    cliente = como(app, personal["dono"])
    hub = cliente.get("/configuracoes").get_data(as_text=True)
    for trecho in ("Dados e contato", "Locais de atendimento", "Estúdio, casa do aluno, parque e online", "3 pacotes ativos", ">Perfil<", ">Locais<"):
        assert trecho in hub, trecho
    assert "Equipe" not in hub and "Horário de funcionamento" not in hub and ">None<" not in hub

    cliente.post("/configuracoes/academia", data={"nome": " Paulo  Rocha ", "cpf": "111.444.777-35", "cref": "012345-g/sp", "telefone": "(12) 99812-3344",
                                                  "email": "PAULO@exemplo.com", "cidade": "Tremembé / SP"})
    with app.app_context():
        c = Conta.query.get(personal["conta"])
        assert (c.nome, c.cpf, c.cref, c.telefone, c.email, c.cidade) == ("Paulo Rocha", "111.444.777-35", "012345-G/SP", "(12) 99812-3344", "paulo@exemplo.com", "Tremembé / SP")
    perfil = cliente.get("/configuracoes?aba=perfil").get_data(as_text=True)
    assert 'value="111.444.777-35"' in perfil and 'value="012345-G/SP"' in perfil and "CREF 012345-G/SP · Tremembé" in perfil

    cliente.post("/configuracoes/academia", data={"nome": "Paulo Rocha", "cpf": "111.111.111-11"})                 # CPF inválido não grava
    assert campo(Conta, personal["conta"], "cpf") == "111.444.777-35"


def test_locais_de_atendimento(app, personal):
    cliente = como(app, personal["dono"])
    cliente.post("/configuracoes/locais", data={"ativos": ["estudio", "online", "inventado"], "endereco_estudio": " Rua XV,  220 "})
    assert (campo(Conta, personal["conta"], "locais_ativos"), campo(Conta, personal["conta"], "endereco")) == ("estudio,online", "Rua XV, 220")
    form = cliente.get(f"/agenda/nova?aluno={personal['ana']}").get_data(as_text=True)
    assert "Rua XV, 220" in form and "Online" in form and "Parque" not in form and "Casa do aluno" not in form
    cliente.post("/configuracoes/locais", data={"endereco_estudio": "x"})                                          # nenhum ligado: recusa
    assert campo(Conta, personal["conta"], "locais_ativos") == "estudio,online"
    academia = como(app, criar_usuario("dono@teste.local", nome="Diana"))
    assert academia.post("/configuracoes/locais", data={"ativos": ["estudio"]}).status_code == 404


def test_textos_padrao_de_mensagem_do_personal(app, personal):
    html = como(app, personal["dono"]).get("/configuracoes?aba=mensagens").get_data(as_text=True)
    assert "Seu pacote ([plano]) de [valor] está em aberto" in html and "Bora comemorar com um treino caprichado" in html
    academia = como(app, criar_usuario("dono@teste.local", nome="Diana")).get("/configuracoes?aba=mensagens").get_data(as_text=True)
    assert "Sua mensalidade de [valor] venceu em [data]" in academia and "Seu pacote" not in academia


# ------------------------------------------------------------------ mensagens
def test_fila_de_mensagens_do_personal(app, personal):
    dono = personal["dono"]
    amanha = criar_sessao(dono, personal["ana"], HOJE + DIA, "07:30", local="parque")
    criar_sessao(dono, personal["ana"], HOJE + 2 * DIA, "07:30")
    criar_sessao(dono, personal["ana"], HOJE + DIA, "09:00", status="cancelada")
    cliente = como(app, dono)
    html = cliente.get("/mensagens").get_data(as_text=True)
    assert "Sessões de amanhã&nbsp;1" in html and "Avaliações de amanhã" not in html and "Cobranças atrasadas&nbsp;1" in html
    assert "Sessão amanhã às 07:30 · parque" in html and f"Confirmando nosso treino amanhã, {(HOJE + DIA).strftime('%d/%m')} às 07:30, no parque." in html
    assert "Pacote em aberto · R$ 520,00" in html and "Seu pacote (Pacote 4) de R$ 520,00 está em aberto." in html
    assert cliente.post("/mensagens/enviada", json={"id": f"sessao-{amanha}"}).get_json() == {"ok": True}
    assert "is-enviada" in cliente.get("/mensagens").get_data(as_text=True)


# ------------------------------------------------------------------ isolamento e exclusão
def test_sessao_de_outra_conta_da_404(app, personal):
    sessao = criar_sessao(personal["dono"], personal["ana"], HOJE, "07:30")
    outro = como(app, criar_personal("outro@teste.local", "Otto"))
    assert outro.get(f"/agenda/{sessao}").status_code == 404 and outro.get(f"/agenda/nova?aluno={personal['ana']}").status_code == 404
    for acao in ("concluir", "cancelar"):
        assert outro.post(f"/agenda/{sessao}/{acao}").status_code == 404
    assert campo(Sessao, sessao, "status") == "agendada" and "Ana Souza" not in outro.get("/agenda").get_data(as_text=True)


def test_sem_login_e_get_nao_grava(app, personal):
    sessao = criar_sessao(personal["dono"], personal["ana"], HOJE, "07:30")
    assert "/login" in app.test_client().get("/agenda").headers["Location"]
    cliente = como(app, personal["dono"])
    for url in ("/", "/agenda", f"/agenda/{sessao}", "/agenda/nova", f"/agenda/nova?aluno={personal['ana']}&remarcar={sessao}", "/planos", f"/alunos/{personal['ana']}/renovar",
                "/configuracoes", "/configuracoes?aba=locais", "/mensagens", "/alunos", f"/alunos/{personal['ana']}"):
        assert cliente.get(url).status_code == 200, url
    assert (contar(Sessao), contar(Cobranca), campo(Sessao, sessao, "status")) == (1, 2, "agendada")


def test_excluir_aluno_com_sessao_apaga_as_sessoes(app, personal):
    # [back-19-lgpd] antes: aluno com histórico não podia ser excluído. Agora os dados pessoais são apagados e o cadastro, anonimizado.
    criar_sessao(personal["dono"], personal["duda"], HOJE + DIA)
    como(app, personal["dono"]).post(f"/alunos/{personal['duda']}/excluir")
    assert campo(Aluno, personal["duda"], "nome") == "Aluno removido" and contar(Sessao) == 0
