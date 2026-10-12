"""Testes da branch back-15-avaliacoes: agenda, agendar, registrar (IMC e RCQ calculados), histórico, resultado, papéis e isolamento."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import Aluno, AvaliacaoAgendada, AvaliacaoFisica
from tests.conftest import (campo, conta_de, contar, criar_agendamento, criar_aluno, criar_avaliacao, criar_plano, criar_usuario,
                            ligar_checkin, logar, numero_do_card)

HOJE = date.today()
DIA = timedelta(days=1)
MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


def br(dia):
    return dia.strftime("%d/%m/%Y")


@pytest.fixture()
def academia(app):
    """Dona, recepção e instrutor; alunas Ana e Bia ativas e Caio inativo. O plano não inclui avaliação."""
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    plano = criar_plano(dono, nome="Mensal")
    return {"dono": dono, "conta": conta, "plano": plano,
            "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
            "instrutor": criar_usuario("igor@teste.local", nome="Igor", conta=conta, papel="instrutor"),
            "ana": criar_aluno(dono, plano, "Ana Souza", "ana@exemplo.com", "111.222.333-96"),
            "bia": criar_aluno(dono, plano, "Bia Lima", "bia@exemplo.com", "555.666.777-20"),
            "caio": criar_aluno(dono, plano, "Caio Inativo", "caio@exemplo.com", "123.456.789-09", ativo=False)}


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def pedido(academia, **trocas):
    """Formulário válido de agendamento da Ana, para daqui a 3 dias, com o instrutor."""
    dados = {"aluno_id": academia["ana"], "tipo": "primeira", "data": br(HOJE + 3 * DIA), "horario": "10:00",
             "avaliador": str(academia["instrutor"]), "observacao": "  vir em   jejum ", "cobranca": "inclusa"}
    dados.update(trocas)
    return dados


MEDIDAS = {"objetivo": "ganhar força", "restricoes": "dor no joelho", "medicamentos": "", "liberacao_medica": "1",
           "peso_kg": "68,4", "altura_cm": "167", "cintura_cm": "72", "quadril_cm": "96,5", "braco_d_cm": "28.4", "coxa_d_cm": "54",
           "torax_cm": "", "panturrilha_cm": "", "dobra_triceps": "12,5", "teste_flexao": "22", "teste_flexibilidade": "-3,5",
           "anotacao": "Boa aderência."}


# ------------------------------------------------------------------ agenda
def test_agenda_vazia(app, academia):
    html = como(app, academia["dono"]).get("/avaliacoes").get_data(as_text=True)
    assert 'class="rail"' in html and "Nenhuma avaliação agendada" in html and f"{MESES[HOJE.month - 1]} · 0 agendadas" in html
    assert "0 alunos sem avaliar há 6 meses" in html and ">None<" not in html


def test_agenda_separa_por_dia_e_so_mostra_o_que_esta_em_aberto(app, academia):
    dono, ana, bia = academia["dono"], academia["ana"], academia["bia"]
    criar_avaliacao(dono, ana, HOJE - 90 * DIA)
    hoje = criar_agendamento(dono, ana, HOJE, "09:00", tipo="reavaliacao")
    criar_agendamento(dono, bia, HOJE + DIA, "14:00")
    criar_agendamento(dono, bia, HOJE + 4 * DIA, "08:00", status="a_confirmar")
    criar_agendamento(dono, bia, HOJE + 30 * DIA, "08:00")
    criar_agendamento(dono, bia, HOJE - 2 * DIA, "08:00")                                  # passou e ninguém registrou
    criar_agendamento(dono, bia, HOJE, "11:00", status="remarcada")
    criar_agendamento(dono, bia, HOJE, "12:00", status="realizada")
    outro = criar_usuario("outro@teste.local", nome="Otto")
    criar_agendamento(outro, criar_aluno(outro, criar_plano(outro, nome="Plano-B"), "Vizinho", "v@exemplo.com", "987.654.321-00"), HOJE, "07:00")

    html = como(app, dono).get("/avaliacoes").get_data(as_text=True)

    for titulo in (f"Hoje, {HOJE.strftime('%d/%m')}", f"Amanhã, {(HOJE + DIA).strftime('%d/%m')}", "Resto da semana", "Mais adiante", "Não realizadas"):
        assert titulo in html, titulo
    assert "Reavaliação · 90 dias" in html and "Primeira avaliação" in html and "A confirmar" in html
    assert html.count("Iniciar avaliação") == 1 and f'/alunos/{ana}/avaliacoes/nova?ag={hoje}' in html     # só a de hoje
    assert "11:00" not in html and "12:00" not in html and "Vizinho" not in html and "07:00" not in html
    cards = html.split('class="mini-grid av-stats"')[1].split("</div>\n{%")[0]
    assert '<div class="stat__val tone-txt-blue">1</div>' in cards and '<div class="stat__val tone-txt-yellow">1</div>' in cards


def test_recepcao_ve_a_agenda_mas_nao_o_botao_de_iniciar(app, academia):
    criar_agendamento(academia["dono"], academia["ana"], HOJE, "09:00")
    html = como(app, academia["recepcao"]).get("/avaliacoes").get_data(as_text=True)
    assert "Ana Souza" in html and "09:00" in html and "Iniciar avaliação" not in html
    assert "Iniciar avaliação" in como(app, academia["instrutor"]).get("/avaliacoes").get_data(as_text=True)


def test_vencidas_e_sem_avaliar(app, academia):
    dono, plano = academia["dono"], academia["plano"]
    criar_avaliacao(dono, academia["ana"], HOJE - 200 * DIA)                                 # venceu (mais de 180 dias)
    criar_avaliacao(dono, academia["bia"], HOJE - 30 * DIA)                                  # em dia
    criar_aluno(dono, plano, "Antigo Nunca", "n@exemplo.com", "222.333.444-05", cadastrado_em=HOJE - 300 * DIA)   # nunca avaliado, cadastro antigo
    criar_aluno(dono, plano, "Novo Nunca", "nn@exemplo.com", "333.444.555-06")                # nunca avaliado, acabou de entrar
    criar_avaliacao(dono, academia["caio"], HOJE - 400 * DIA)                                # inativo: não conta
    html = como(app, dono).get("/avaliacoes").get_data(as_text=True)
    assert '<div class="stat__val tone-txt-orange">1</div>' in html and "2 alunos sem avaliar há 6 meses" in html


# ------------------------------------------------------------------ agendar
def test_agendar_comeca_pela_escolha_do_aluno(app, academia):
    recepcao = como(app, academia["recepcao"])
    html = recepcao.get("/avaliacoes/agendar").get_data(as_text=True)
    assert "Quem vai ser avaliado?" in html and "Ana Souza" in html and "Bia Lima" in html and "Caio Inativo" not in html
    busca = recepcao.get("/avaliacoes/agendar?q=bia").get_data(as_text=True)
    assert "Bia Lima" in busca and "Ana Souza" not in busca
    assert "Ninguém com" in recepcao.get("/avaliacoes/agendar?q=zzz").get_data(as_text=True)


def test_formulario_de_agendar(app, academia):
    html = como(app, academia["recepcao"]).get(f"/avaliacoes/agendar?aluno={academia['ana']}").get_data(as_text=True)
    for trecho in ("Ana Souza", "Ainda sem avaliação", "não inclui avaliação física", "cobrada à parte", ">06:00<", ">20:00<", "Diana", "Igor",
                   br(HOJE + 2 * DIA), 'name="tipo" value="primeira"'):
        assert trecho in html, trecho
    assert f'<option value="{academia["recepcao"]}"' not in html and "Lembretes automáticos" not in html and "R$" not in html and ">None<" not in html
    # quem avalia e abre o formulário já vem como avaliador sugerido
    assert f'<option value="{academia["instrutor"]}" selected>' in como(app, academia["instrutor"]).get(f"/avaliacoes/agendar?aluno={academia['ana']}").get_data(as_text=True)


def test_plano_que_inclui_avaliacao_e_quem_ja_foi_avaliado(app, academia):
    from app.extensions.database import db
    from app.models import Plano
    with app.app_context():
        db.session.get(Plano, academia["plano"]).avaliacoes_incluidas = 2
        db.session.commit()
    criar_avaliacao(academia["dono"], academia["ana"], HOJE - 40 * DIA)
    html = como(app, academia["dono"]).get(f"/avaliacoes/agendar?aluno={academia['ana']}").get_data(as_text=True)
    assert "inclui avaliação física" in html and "não inclui" not in html and 'name="cobranca" value="inclusa"' in html
    assert f"Última avaliação: {br(HOJE - 40 * DIA)}" in html and 'name="tipo" value="reavaliacao"' in html


def test_agendar_grava_o_horario(app, academia):
    resposta = como(app, academia["recepcao"]).post("/avaliacoes/agendar", data=pedido(academia, cobranca="avulsa"))
    assert resposta.headers["Location"] == "/avaliacoes"
    with app.app_context():
        a = AvaliacaoAgendada.query.one()
        assert (a.conta_id, a.aluno_id, a.data, a.hora, a.tipo, a.status, a.avaliador_id, a.observacao, a.cobranca, a.criado_por_id) == (
            academia["conta"], academia["ana"], HOJE + 3 * DIA, "10:00", "primeira", "confirmada", academia["instrutor"], "vir em jejum", "avulsa",
            academia["recepcao"])
    agenda = como(app, academia["recepcao"]).get("/avaliacoes").get_data(as_text=True)
    assert "Ana Souza" in agenda and "10:00" in agenda


@pytest.mark.parametrize("trocas, aviso", [
    ({"data": br(HOJE - DIA)}, "Escolha uma data de hoje em diante."), ({"data": "2026-10-20"}, "Use o formato dd/mm/aaaa."),
    ({"data": "31/02/2027"}, "Use o formato dd/mm/aaaa."), ({"data": br(HOJE + 400 * DIA)}, "Escolha uma data dentro de um ano."),
    ({"horario": "03:00"}, "Escolha um horário."), ({"horario": ""}, "Escolha um horário."),
    ({"avaliador": "RECEPCAO"}, "Escolha o avaliador."), ({"avaliador": "DE_FORA"}, "Escolha o avaliador."), ({"avaliador": "abc"}, "Escolha o avaliador."),
])
def test_agendamento_invalido_avisa_e_nao_grava(app, academia, trocas, aviso):
    if trocas.get("avaliador") == "RECEPCAO":
        trocas = {"avaliador": str(academia["recepcao"])}                                    # recepção não avalia
    elif trocas.get("avaliador") == "DE_FORA":
        trocas = {"avaliador": str(criar_usuario("outro@teste.local", nome="Otto"))}         # usuário de outra academia
    resposta = como(app, academia["dono"]).post("/avaliacoes/agendar", data=pedido(academia, **trocas))
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 200 and contar(AvaliacaoAgendada) == 0
    assert aviso in html and 'value="  vir em   jejum "' in html                              # avisa e devolve o que foi digitado


def test_mesmo_avaliador_nao_tem_dois_alunos_no_mesmo_horario(app, academia):
    dono = como(app, academia["dono"])
    dono.post("/avaliacoes/agendar", data=pedido(academia))
    repetido = dono.post("/avaliacoes/agendar", data=pedido(academia, aluno_id=academia["bia"]))
    assert repetido.status_code == 200 and "Igor Teste já tem avaliação marcada neste horário." in repetido.get_data(as_text=True)
    assert contar(AvaliacaoAgendada) == 1
    assert dono.post("/avaliacoes/agendar", data=pedido(academia, aluno_id=academia["bia"], avaliador=str(academia["dono"]))).status_code == 302
    assert contar(AvaliacaoAgendada) == 2                                                    # com outro avaliador, pode


def test_remarcar_guarda_o_horario_antigo_como_remarcado(app, academia):
    dono = como(app, academia["dono"])
    antigo = criar_agendamento(academia["dono"], academia["ana"], HOJE, "09:00")
    da_bia = criar_agendamento(academia["dono"], academia["bia"], HOJE, "15:00")
    assert f'name="remarcar" value="{antigo}"' in dono.get(f"/avaliacoes/agendar?aluno={academia['ana']}&remarcar={antigo}").get_data(as_text=True)

    dono.post("/avaliacoes/agendar", data=pedido(academia, remarcar=antigo))
    assert campo(AvaliacaoAgendada, antigo, "status") == "remarcada" and contar(AvaliacaoAgendada, aluno_id=academia["ana"], status="confirmada") == 1

    # "remarcar" com o horário de OUTRO aluno não mexe nele
    dono.post("/avaliacoes/agendar", data=pedido(academia, remarcar=da_bia, horario="16:00"))
    assert campo(AvaliacaoAgendada, da_bia, "status") == "confirmada"


def test_agendar_para_inativo_ou_de_outra_academia(app, academia):
    dono = como(app, academia["dono"])
    outro = criar_usuario("outro@teste.local", nome="Otto")
    vizinho = criar_aluno(outro, criar_plano(outro, nome="Plano-B"), "Vizinho", "v@exemplo.com", "987.654.321-00")
    assert dono.get(f"/avaliacoes/agendar?aluno={vizinho}").status_code == 404
    assert dono.post("/avaliacoes/agendar", data=pedido(academia, aluno_id=vizinho)).status_code == 404
    assert dono.get(f"/avaliacoes/agendar?aluno={academia['caio']}").headers["Location"] == "/avaliacoes/agendar"
    assert dono.post("/avaliacoes/agendar", data=pedido(academia, aluno_id=academia["caio"])).headers["Location"] == "/avaliacoes/agendar"
    assert contar(AvaliacaoAgendada) == 0


# ------------------------------------------------------------------ registrar
def test_formulario_da_avaliacao(app, academia):
    instrutor = como(app, academia["instrutor"])
    html = instrutor.get(f"/alunos/{academia['ana']}/avaliacoes/nova?ag=7").get_data(as_text=True)
    for trecho in ("Avaliação de Ana", "Anamnese", "Medidas básicas", "Dobras cutâneas", "Testes físicos", 'name="ag" value="7"', "medida, não diagnóstico"):
        assert trecho in html, trecho
    assert "Fotos de acompanhamento" not in html and 'type="file"' not in html and ">None<" not in html       # as fotos ainda não são guardadas
    assert 'name="altura_cm" inputmode="decimal" value=""' in html                                             # primeira avaliação: nada preenchido

    criar_avaliacao(academia["dono"], academia["ana"], HOJE - 30 * DIA, peso=75, altura=167)
    html = instrutor.get(f"/alunos/{academia['ana']}/avaliacoes/nova").get_data(as_text=True)
    assert 'name="altura_cm" inputmode="decimal" value="167"' in html and 'name="peso_kg" inputmode="decimal" value=""' in html   # só a altura vem da anterior


def test_registrar_calcula_imc_e_rcq_no_servidor(app, academia):
    marcado = criar_agendamento(academia["dono"], academia["ana"], HOJE, "09:00", avaliador_id=academia["instrutor"])
    resposta = como(app, academia["instrutor"]).post(f"/alunos/{academia['ana']}/avaliacoes/nova",
                                                    data=dict(MEDIDAS, ag=marcado, imc="99", rcq="9"))       # IMC e RCQ "digitados" são ignorados
    with app.app_context():
        e = AvaliacaoFisica.query.one()
        assert resposta.headers["Location"] == f"/avaliacoes/{e.id}"
        assert (e.conta_id, e.aluno_id, e.data, e.avaliador_id, e.agendamento_id) == (academia["conta"], academia["ana"], HOJE, academia["instrutor"], marcado)
        assert (e.peso_kg, e.altura_cm, e.imc, e.rcq) == (Decimal("68.4"), Decimal("167"), Decimal("24.5"), Decimal("0.75"))
        assert (e.cintura_cm, e.braco_d_cm, e.torax_cm, e.dobra_triceps, e.teste_flexao, e.teste_abdominal, e.teste_flexibilidade) == (
            Decimal("72"), Decimal("28.4"), None, Decimal("12.5"), 22, None, Decimal("-3.5"))
        assert (e.objetivo, e.restricoes, e.medicamentos, e.liberacao_medica, e.anotacao) == ("ganhar força", "dor no joelho", None, True, "Boa aderência.")
    assert campo(AvaliacaoAgendada, marcado, "status") == "realizada"


def test_sem_cintura_ou_quadril_nao_ha_rcq(app, academia):
    como(app, academia["dono"]).post(f"/alunos/{academia['ana']}/avaliacoes/nova", data={"peso_kg": "80", "altura_cm": "180", "cintura_cm": "90"})
    assert campo(AvaliacaoFisica, 1, "rcq") is None and campo(AvaliacaoFisica, 1, "imc") == Decimal("24.7")
    assert campo(AvaliacaoFisica, 1, "liberacao_medica") is False


@pytest.mark.parametrize("trocas, aviso", [
    ({"peso_kg": ""}, "Informe peso e altura válidos"), ({"altura_cm": ""}, "Informe peso e altura válidos"),
    ({"altura_cm": "1,67"}, "Altura: confira o número"), ({"peso_kg": "684"}, "Peso: confira o número"), ({"peso_kg": "abc"}, "Peso: use só números"),
    ({"peso_kg": "nan"}, "Peso: use só números"), ({"cintura_cm": "5000"}, "Cintura: confira o número"), ({"dobra_triceps": "0"}, "Dobra do tríceps: confira"),
    ({"teste_flexao": "-1"}, "Flexões em 1 minuto: use um número inteiro"), ({"teste_flexao": "12,5"}, "Flexões em 1 minuto: use um número inteiro"),
])
def test_medida_invalida_avisa_e_nao_grava(app, academia, trocas, aviso):
    resposta = como(app, academia["dono"]).post(f"/alunos/{academia['ana']}/avaliacoes/nova", data=dict(MEDIDAS, **trocas))
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 200 and contar(AvaliacaoFisica) == 0
    assert aviso.split(":")[0].split()[0] in html and 'value="ganhar força"' in html          # avisa e devolve o que foi digitado


def test_enviar_duas_vezes_nao_duplica(app, academia):
    dono = como(app, academia["dono"])
    primeira = dono.post(f"/alunos/{academia['ana']}/avaliacoes/nova", data=MEDIDAS).headers["Location"]
    assert dono.post(f"/alunos/{academia['ana']}/avaliacoes/nova", data=MEDIDAS).headers["Location"] == primeira
    assert contar(AvaliacaoFisica) == 1
    dono.post(f"/alunos/{academia['ana']}/avaliacoes/nova", data=dict(MEDIDAS, peso_kg="69"))     # outra medida: é outra avaliação
    assert contar(AvaliacaoFisica) == 2


# ------------------------------------------------------------------ resultado e histórico
def test_resultado_da_primeira_avaliacao(app, academia):
    e = criar_avaliacao(academia["dono"], academia["ana"], HOJE, peso=68.4, altura=167, anotacao="Tudo certo.")
    html = como(app, academia["instrutor"]).get(f"/avaliacoes/{e}").get_data(as_text=True)
    for trecho in ("Avaliação registrada", f"Ana Souza · {br(HOJE)} · Diana", "Primeira avaliação", "Tudo certo.", f'href="/alunos/{academia["ana"]}/ficha"'):
        assert trecho in html, trecho
    assert "O que mudou" not in html and ">None<" not in html
    assert 'href="https://wa.me/5511999990000?text=Oi%20Ana%21' in html and "Peso%3A%2068%2C4%20kg" in html and "IMC%3A%2024%2C5" in html


def test_resultado_compara_com_a_avaliacao_anterior(app, academia):
    dono = academia["dono"]
    criar_avaliacao(dono, academia["ana"], HOJE - 90 * DIA, peso=71.2, altura=167, cintura_cm=78, braco_d_cm=26.1)
    e = criar_avaliacao(dono, academia["ana"], HOJE, peso=68.4, altura=167, cintura_cm=72, braco_d_cm=25.0, coxa_d_cm=54)
    html = como(app, dono).get(f"/avaliacoes/{e}").get_data(as_text=True)

    assert "O que mudou em 90 dias" in html and f"Comparado com {br(HOJE - 90 * DIA)}" in html and "Reavaliação de 90 dias" in html
    linhas = html.split("<tbody>")[1].split("</tbody>")[0]
    assert linhas.count("<tr>") == 4 and "Coxa direita" not in linhas                          # coxa não foi medida antes: não compara
    assert 'tone-txt-teal"><b class="num">-2,8</b>' in linhas                                  # peso caiu: verde
    assert 'tone-txt-teal"><b class="num">-6,0</b>' in linhas                                  # cintura caiu: verde
    assert 'tone-txt-red"><b class="num">-1,1</b>' in linhas                                   # braço caiu: vermelho
    assert "Sem anotação." in html and "Desde%20" in html


def test_historico_do_aluno(app, academia):
    dono = como(app, academia["dono"])
    vazio = dono.get(f"/alunos/{academia['ana']}/avaliacoes").get_data(as_text=True)
    assert "Ainda sem avaliações" in vazio and "data-chart" not in vazio

    criar_avaliacao(academia["dono"], academia["ana"], HOJE - 100 * DIA, peso=71.2, altura=167)
    uma = dono.get(f"/alunos/{academia['ana']}/avaliacoes").get_data(as_text=True)
    assert "Todas as avaliações" in uma and "71,2 kg" in uma and "IMC 25,5" in uma and "data-chart" not in uma       # com uma só não há gráfico

    criar_avaliacao(academia["dono"], academia["ana"], HOJE, peso=68.4, altura=167)
    duas = dono.get(f"/alunos/{academia['ana']}/avaliacoes").get_data(as_text=True)
    anos = sorted({(HOJE - 100 * DIA).year, HOJE.year})
    periodo = str(anos[0]) if len(anos) == 1 else f"{anos[0]} a {anos[-1]}"
    assert f"Peso em {periodo}" in duas and "2 avaliações · −2,8 kg no período" in duas and "data-chart" in duas
    assert duas.index(br(HOJE)) < duas.index(br(HOJE - 100 * DIA)) and ">None<" not in duas    # a mais recente primeiro


# ------------------------------------------------------------------ perfil do aluno e painel
def test_perfil_do_aluno_mostra_a_ultima_avaliacao(app, academia):
    dono, ana = academia["dono"], academia["ana"]
    assert "Última:" not in como(app, dono).get(f"/alunos/{ana}").get_data(as_text=True)       # nunca avaliado: o cartão não aparece

    criar_avaliacao(dono, ana, HOJE - 200 * DIA, peso=71.2, altura=167)
    html = como(app, dono).get(f"/alunos/{ana}").get_data(as_text=True)
    assert f"Última: {br(HOJE - 200 * DIA)}" in html and "71,2 kg · IMC 25,5" in html and ">Vencida<" in html

    criar_avaliacao(dono, ana, HOJE, peso=68.4, altura=167)
    html = como(app, academia["instrutor"]).get(f"/alunos/{ana}").get_data(as_text=True)
    assert f"Última: {br(HOJE)}" in html and "68,4 kg · IMC 24,5 · −2,8 kg desde a anterior" in html and ">Em dia<" in html

    recepcao = como(app, academia["recepcao"]).get(f"/alunos/{ana}").get_data(as_text=True)    # a recepção vê a data, não as medidas
    assert f"Última: {br(HOJE)}" in recepcao and "68,4" not in recepcao and "IMC" not in recepcao


def test_painel_avisa_das_avaliacoes_de_hoje(app, academia):
    dono = como(app, academia["dono"])
    assert "Avaliações de hoje" not in dono.get("/").get_data(as_text=True)                    # sem nenhuma, o card não aparece

    criar_agendamento(academia["dono"], academia["bia"], HOJE, "14:00", avaliador_id=academia["instrutor"])
    marcado = criar_agendamento(academia["dono"], academia["ana"], HOJE, "09:00")
    criar_agendamento(academia["dono"], academia["ana"], HOJE + DIA, "09:00")
    html = dono.get("/").get_data(as_text=True)

    assert numero_do_card(html, "Avaliações de hoje") == "2" and "2 avaliações agendadas para hoje" in html
    assert "09:00 · Primeira avaliação · Confirmada" in html and 'href="https://wa.me/5511999990000"' in html
    assert "Hoje, 09:00" in html and f"/alunos/{academia['ana']}/avaliacoes/nova?ag={marcado}" in html      # o aviso é da próxima do dia
    assert "Aviso já enviado" not in html and "Camila Duarte" not in html and ">None<" not in html

    ligar_checkin(academia["conta"])                                                           # com check-in, o lugar do card é dos ausentes
    assert "Avaliações de hoje</div></div></button>" not in dono.get("/").get_data(as_text=True)


# ------------------------------------------------------------------ quem pode e isolamento
def test_recepcao_agenda_mas_nao_abre_medidas(app, academia):
    e = criar_avaliacao(academia["dono"], academia["ana"], HOJE)
    recepcao = como(app, academia["recepcao"])
    for url in (f"/alunos/{academia['ana']}/avaliacoes", f"/alunos/{academia['ana']}/avaliacoes/nova", f"/avaliacoes/{e}"):
        assert recepcao.get(url).headers["Location"] == "/avaliacoes", url                     # avisa e leva à agenda
    assert recepcao.post(f"/alunos/{academia['ana']}/avaliacoes/nova", data=MEDIDAS).status_code == 403
    assert contar(AvaliacaoFisica) == 1
    for url in ("/avaliacoes", "/avaliacoes/agendar", f"/avaliacoes/agendar?aluno={academia['ana']}"):
        assert recepcao.get(url).status_code == 200, url


def test_dono_e_instrutor_abrem_tudo(app, academia):
    e = criar_avaliacao(academia["dono"], academia["ana"], HOJE)
    for papel in ("dono", "instrutor"):
        cliente = como(app, academia[papel])
        for url in ("/avaliacoes", "/avaliacoes/agendar", f"/alunos/{academia['ana']}/avaliacoes", f"/alunos/{academia['ana']}/avaliacoes/nova", f"/avaliacoes/{e}"):
            assert cliente.get(url).status_code == 200, f"{papel} {url}"


def test_avaliacao_de_outra_academia_da_404(app, academia):
    e = criar_avaliacao(academia["dono"], academia["ana"], HOJE, peso=68.4, altura=167)
    marcado = criar_agendamento(academia["dono"], academia["ana"], HOJE, "09:00")
    outro_id = criar_usuario("outro@teste.local", nome="Otto")
    vizinho = criar_aluno(outro_id, criar_plano(outro_id, nome="Plano-B"), "Vizinho", "v@exemplo.com", "987.654.321-00")
    outro = como(app, outro_id)
    ana = academia["ana"]

    for url in (f"/avaliacoes/{e}", f"/alunos/{ana}/avaliacoes", f"/alunos/{ana}/avaliacoes/nova", f"/avaliacoes/agendar?aluno={ana}"):
        assert outro.get(url).status_code == 404, url
    assert outro.post(f"/alunos/{ana}/avaliacoes/nova", data=MEDIDAS).status_code == 404
    # avaliar o próprio aluno apontando para o horário marcado na OUTRA academia não mexe nesse horário
    outro.post(f"/alunos/{vizinho}/avaliacoes/nova", data=dict(MEDIDAS, ag=marcado))
    assert campo(AvaliacaoAgendada, marcado, "status") == "confirmada" and contar(AvaliacaoFisica, aluno_id=ana) == 1
    html = outro.get("/avaliacoes").get_data(as_text=True)
    assert "Ana Souza" not in html and "Avaliações de hoje" not in outro.get("/").get_data(as_text=True)


def test_sem_login_vai_para_o_login(app, academia):
    cliente = app.test_client()
    for url in ("/avaliacoes", "/avaliacoes/agendar", f"/alunos/{academia['ana']}/avaliacoes", f"/alunos/{academia['ana']}/avaliacoes/nova", "/avaliacoes/1"):
        resposta = cliente.get(url)
        assert resposta.status_code == 302 and "/login" in resposta.headers["Location"], url


def test_abrir_telas_nao_grava_nada(app, academia):
    e = criar_avaliacao(academia["dono"], academia["ana"], HOJE)
    marcado = criar_agendamento(academia["dono"], academia["ana"], HOJE, "09:00")
    dono = como(app, academia["dono"])
    for url in ("/avaliacoes", "/avaliacoes/agendar", f"/avaliacoes/agendar?aluno={academia['ana']}&remarcar={marcado}", f"/alunos/{academia['ana']}/avaliacoes",
                f"/alunos/{academia['ana']}/avaliacoes/nova?ag={marcado}", f"/avaliacoes/{e}", "/"):
        assert dono.get(url).status_code == 200, url
    assert (contar(AvaliacaoFisica), contar(AvaliacaoAgendada), campo(AvaliacaoAgendada, marcado, "status")) == (1, 1, "confirmada")


def test_aluno_com_avaliacao_nao_pode_ser_excluido(app, academia):
    dono = como(app, academia["dono"])
    criar_avaliacao(academia["dono"], academia["ana"], HOJE)
    criar_agendamento(academia["dono"], academia["bia"], HOJE + DIA)
    dono.post(f"/alunos/{academia['ana']}/excluir")
    dono.post(f"/alunos/{academia['bia']}/excluir")
    assert contar(Aluno, id=academia["ana"]) == 1 and contar(Aluno, id=academia["bia"]) == 1
    assert contar(AvaliacaoFisica) == 1 and contar(AvaliacaoAgendada) == 1
