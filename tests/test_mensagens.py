"""Testes da branch back-16-mensagens: a fila do dia (aniversário, avaliação de amanhã, cobrança atrasada), o registro do envio e os links do WhatsApp."""
from datetime import date, timedelta
from urllib.parse import quote

import pytest

from app.models import Aluno, MensagemEnviada
from tests.conftest import (_salvar, campo, conta_de, contar, criar_agendamento, criar_aluno, criar_pagamento, criar_plano, criar_usuario,
                            logar)

HOJE = date.today()
DIA = timedelta(days=1)
# um aniversário que cai hoje (e, se hoje for 29/02, num ano bissexto)
NASCEU_HOJE = date(1992 if (HOJE.day, HOJE.month) == (29, 2) else 1990, HOJE.month, HOJE.day)
OUTRO_DIA = (HOJE + 100 * DIA).replace(year=1990) if (HOJE + 100 * DIA).month != 2 else date(1990, 6, 15)


@pytest.fixture()
def academia(app):
    """
    Dona, recepção e instrutor. Ana faz aniversário hoje; Bia tem avaliação amanhã às 10:00; Caio está com a
    mensalidade vencida há 10 dias; Duda está em dia e não tem nada; Edu (inativo) faz aniversário e deve.
    """
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    plano = criar_plano(dono, nome="Mensal")
    ana = criar_aluno(dono, plano, "Ana Souza", "ana@exemplo.com", "111.222.333-96", nascimento=NASCEU_HOJE)
    bia = criar_aluno(dono, plano, "Bia Lima", "bia@exemplo.com", "555.666.777-20", nascimento=OUTRO_DIA)
    caio = criar_aluno(dono, plano, "Caio Dias", "caio@exemplo.com", "123.456.789-09", nascimento=OUTRO_DIA)
    duda = criar_aluno(dono, plano, "Duda Reis", "duda@exemplo.com", "222.333.444-05", nascimento=OUTRO_DIA)
    edu = criar_aluno(dono, plano, "Edu Inativo", "edu@exemplo.com", "333.444.555-06", ativo=False, nascimento=NASCEU_HOJE)
    for aluno in (ana, bia, duda):
        criar_pagamento(dono, aluno, 100, HOJE - 5 * DIA, HOJE + 25 * DIA)              # em dia
    for aluno in (caio, edu):
        criar_pagamento(dono, aluno, 100, HOJE - 40 * DIA, HOJE - 10 * DIA)             # venceu há 10 dias
    return {"dono": dono, "conta": conta, "plano": plano, "ana": ana, "bia": bia, "caio": caio, "duda": duda, "edu": edu,
            "marcada": criar_agendamento(dono, bia, HOJE + DIA, "10:00"),
            "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
            "instrutor": criar_usuario("igor@teste.local", nome="Igor", conta=conta, papel="instrutor")}


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def linha(html, nome):
    """O pedaço do HTML da linha da fila que é desse aluno."""
    return next(p for p in html.split('<li class="msg-item') if f">{nome}</a>" in p)


def marcar(cliente, id_do_item):
    return cliente.post("/mensagens/enviada", json={"id": id_do_item})


# ------------------------------------------------------------------ a fila
def test_fila_do_dia_tem_os_tres_motivos(app, academia):
    html = como(app, academia["dono"]).get("/mensagens").get_data(as_text=True)

    assert 'class="rail"' in html and "Fila de hoje · 3 para enviar" in html and ">None<" not in html
    assert html.count('<li class="msg-item') == 3 and "Duda Reis" not in html and "Edu Inativo" not in html       # quem não tem motivo, e inativo, fica fora
    assert html.index("Ana Souza") < html.index("Bia Lima") < html.index("Caio Dias")                           # aniversário, avaliação, cobrança
    for rotulo in ("Todas&nbsp;3", "Aniversários&nbsp;1", "Avaliações de amanhã&nbsp;1", "Cobranças atrasadas&nbsp;1"):
        assert rotulo in html, rotulo

    ana, bia, caio = linha(html, "Ana Souza"), linha(html, "Bia Lima"), linha(html, "Caio Dias")
    assert f"Completa {HOJE.year - NASCEU_HOJE.year} anos hoje" in ana and "Parabéns, Ana! A equipe da Academia de Diana deseja um dia ótimo." in ana
    amanha = (HOJE + DIA).strftime("%d/%m")
    assert "Avaliação amanhã às 10:00 · Primeira avaliação" in bia and f"Sua avaliação física é amanhã, {amanha} às 10:00, na Academia de Diana." in bia
    venceu = (HOJE - 10 * DIA).strftime("%d/%m") if (HOJE - 10 * DIA).year == HOJE.year else (HOJE - 10 * DIA).strftime("%d/%m/%y")
    assert f"Venceu {venceu} · R$ 100,00" in caio and f"Sua mensalidade de R$ 100,00 venceu em {venceu}." in caio
    assert "[" not in ana + bia + caio.split("msg-balao")[1].split("</p>")[0]                                    # nenhuma variável sobrou sem trocar


def test_cada_linha_abre_o_whatsapp_do_aluno_com_o_texto(app, academia):
    html = como(app, academia["dono"]).get("/mensagens").get_data(as_text=True)
    texto = "Parabéns, Ana! A equipe da Academia de Diana deseja um dia ótimo."
    assert f'href="https://wa.me/5511999990000?text={quote(texto)}"' in linha(html, "Ana Souza")
    assert f'data-msg-enviar="aniversario-{academia["ana"]}"' in html and f'data-msg-enviar="avaliacao-{academia["marcada"]}"' in html
    assert f'data-msg-enviar="cobranca-{academia["caio"]}"' in html and html.count("Enviar no WhatsApp") == 3


def test_texto_personalizado_nas_configuracoes_vale_na_fila(app, academia):
    dono = como(app, academia["dono"])
    dono.post("/configuracoes/mensagem", data={"tipo": "aniversario", "texto": "Feliz aniversário, [nome]! Abraço da [academia]. <b>oi</b>"})
    html = dono.get("/mensagens").get_data(as_text=True)
    assert "Feliz aniversário, Ana! Abraço da Academia de Diana. &lt;b&gt;oi&lt;/b&gt;" in linha(html, "Ana Souza")      # e o HTML digitado não vira HTML


def test_fila_vazia(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    html = como(app, dono).get("/mensagens").get_data(as_text=True)
    assert "Fila de hoje · 0 para enviar" in html and "Todas&nbsp;0" in html and "<li class=\"msg-item" not in html
    assert '<p class="muted ta-c" data-vazio style' in html                                                      # "Nada pra mandar" visível


def test_aviso_do_topo_nao_promete_envio_automatico(app, academia):
    """A chave "lembretes" das configurações nasce ligada, mas o sistema não envia sozinho: a tela não diz que envia."""
    dono = como(app, academia["dono"])
    for ligado in ("1", "0"):
        dono.post("/configuracoes/funcionalidade", data={"chave": "lembretes", "ligado": ligado})
        html = dono.get("/mensagens").get_data(as_text=True)
        assert "Você toca, o WhatsApp abre pronto" in html and "sai sozinha" not in html and "Lembretes automáticos ligados" not in html


def test_avaliacao_que_nao_e_amanha_ou_nao_esta_em_aberto_fica_fora(app, academia):
    dono = academia["dono"]
    criar_agendamento(dono, academia["duda"], HOJE, "09:00")                                # hoje: o lembrete era ontem
    criar_agendamento(dono, academia["duda"], HOJE + 2 * DIA, "09:00")                      # depois de amanhã
    criar_agendamento(dono, academia["duda"], HOJE + DIA, "11:00", status="remarcada")
    criar_agendamento(dono, academia["edu"], HOJE + DIA, "12:00")                           # aluno inativo
    html = como(app, dono).get("/mensagens").get_data(as_text=True)
    assert "Duda Reis" not in html and "Edu Inativo" not in html and "Avaliações de amanhã&nbsp;1" in html


# ------------------------------------------------------------------ marcar como enviada
def test_tocar_em_enviar_grava_e_a_linha_vira_enviada(app, academia):
    recepcao = como(app, academia["recepcao"])
    resposta = marcar(recepcao, f"cobranca-{academia['caio']}")
    assert resposta.status_code == 200 and resposta.get_json() == {"ok": True}
    with app.app_context():
        m = MensagemEnviada.query.one()
        assert (m.conta_id, m.aluno_id, m.tipo, m.referencia, m.data, m.enviada_por_id) == (
            academia["conta"], academia["caio"], "cobranca", str(academia["caio"]), HOJE, academia["recepcao"])

    html = como(app, academia["dono"]).get("/mensagens").get_data(as_text=True)                                   # a dona também vê como enviada
    caio = linha(html, "Caio Dias")
    assert "Fila de hoje · 2 para enviar" in html and "is-enviada" in caio and "Enviar de novo" in caio and "data-msg-feito>" in caio
    assert "data-msg-feito hidden>" in linha(html, "Ana Souza")

    assert marcar(recepcao, f"cobranca-{academia['caio']}").get_json() == {"ok": True}                           # tocar de novo não duplica
    assert contar(MensagemEnviada) == 1


@pytest.mark.parametrize("id_do_item", ["cobranca-99999", "cobranca-DUDA", "aniversario-EDU", "avaliacao-99999", "sumido-1", "cobranca", "", "x" * 500])
def test_so_marca_o_que_esta_na_fila_de_hoje(app, academia, id_do_item):
    id_do_item = id_do_item.replace("DUDA", str(academia["duda"])).replace("EDU", str(academia["edu"]))          # Duda está em dia; Edu é inativo
    resposta = marcar(como(app, academia["dono"]), id_do_item)
    assert resposta.status_code == 404 and resposta.get_json() == {"ok": False} and contar(MensagemEnviada) == 0


def test_cobranca_nao_volta_no_dia_seguinte(app, academia):
    """Quem foi cobrado ontem ou anteontem sai da fila; no terceiro dia volta."""
    def cobrado_em(dia):
        with app.app_context():
            from app.extensions.database import db
            MensagemEnviada.query.delete()
            db.session.add(MensagemEnviada(conta_id=academia["conta"], aluno_id=academia["caio"], tipo="cobranca", referencia=str(academia["caio"]),
                                           data=dia, enviada_por_id=academia["dono"]))
            db.session.commit()
        return como(app, academia["dono"]).get("/mensagens").get_data(as_text=True)

    assert "Caio Dias" not in cobrado_em(HOJE - DIA) and "Caio Dias" not in cobrado_em(HOJE - 2 * DIA)
    volta = cobrado_em(HOJE - 3 * DIA)
    assert "Caio Dias" in volta and "is-enviada" not in linha(volta, "Caio Dias")
    # aniversário de hoje não some por causa de um envio de outro dia
    assert "Ana Souza" in volta


def test_envio_sem_csrf_e_recusado(app, academia):
    app.config["WTF_CSRF_ENABLED"] = True
    cliente = como(app, academia["dono"])
    assert cliente.post("/mensagens/enviada", json={"id": f"cobranca-{academia['caio']}"}).status_code == 400
    assert contar(MensagemEnviada) == 0


# ------------------------------------------------------------------ quem vê o quê e isolamento
def test_instrutor_nao_ve_nem_marca_cobranca(app, academia):
    instrutor = como(app, academia["instrutor"])
    html = instrutor.get("/mensagens").get_data(as_text=True)
    assert "Ana Souza" in html and "Bia Lima" in html and "Caio Dias" not in html and "Cobranças atrasadas" not in html
    assert "Fila de hoje · 2 para enviar" in html and "R$" not in html
    assert marcar(instrutor, f"cobranca-{academia['caio']}").status_code == 404 and contar(MensagemEnviada) == 0
    assert marcar(instrutor, f"aniversario-{academia['ana']}").status_code == 200                                  # o resto ele envia


def test_outra_academia_nao_ve_nem_marca(app, academia):
    outro = como(app, criar_usuario("outro@teste.local", nome="Otto"))
    html = outro.get("/mensagens").get_data(as_text=True)
    assert "Ana Souza" not in html and "Caio Dias" not in html and "0 para enviar" in html
    for id_do_item in (f"aniversario-{academia['ana']}", f"cobranca-{academia['caio']}", f"avaliacao-{academia['marcada']}"):
        assert marcar(outro, id_do_item).status_code == 404
    assert contar(MensagemEnviada) == 0


def test_sem_login(app, academia):
    cliente = app.test_client()
    assert "/login" in cliente.get("/mensagens").headers["Location"]
    assert cliente.post("/mensagens/enviada", json={"id": "x"}).status_code in (302, 401)


def test_abrir_a_tela_nao_grava_nada(app, academia):
    como(app, academia["dono"]).get("/mensagens")
    assert contar(MensagemEnviada) == 0


# ------------------------------------------------------------------ os botões de WhatsApp que eram demonstração
def test_cobranca_em_lote_do_painel_leva_a_fila(app, academia):
    assert como(app, academia["recepcao"]).post("/cobrancas/lembrete").headers["Location"] == "/mensagens"
    assert como(app, academia["instrutor"]).post("/cobrancas/lembrete").status_code == 403                         # cobrança continua fechada ao instrutor


def test_botoes_de_whatsapp_viraram_links(app, academia):
    dono = como(app, academia["dono"])
    link = 'href="https://wa.me/5511999990000" target="_blank" rel="noopener"'
    perfil = dono.get(f"/alunos/{academia['ana']}").get_data(as_text=True)
    assert perfil.count(link) == 2 and "WhatsApp aberto para" not in perfil                                        # desktop e celular
    lista = dono.get("/alunos").get_data(as_text=True)
    assert link in lista and "WhatsApp aberto para" not in lista
    painel = dono.get("/").get_data(as_text=True)
    assert link in painel and "WhatsApp aberto para" not in painel and "Mensagem de WhatsApp aberta" not in painel
    assert "Mensagens de parabéns enviadas" not in painel and "Lembretes de renovação enviados" not in painel
    assert painel.count('<a class="btn btn-primary btn-block" href="/mensagens">') == 2


def test_aluno_sem_telefone(app, academia):
    sem = _salvar(Aluno(nome="Sem Fone", email="s@exemplo.com", cpf="444.555.666-07", telefone=None, ativo=True, data_nascimento=NASCEU_HOJE,
                        plano_id=academia["plano"], instrutor_id=academia["dono"], conta_id=academia["conta"]))
    dono = como(app, academia["dono"])
    fila = linha(dono.get("/mensagens").get_data(as_text=True), "Sem Fone")
    assert 'href="https://wa.me/?text=' in fila                                                                    # abre o WhatsApp para escolher o contato
    perfil = dono.get(f"/alunos/{sem}").get_data(as_text=True)
    assert "wa.me" not in perfil and "Sem não tem telefone cadastrado." in perfil


def test_excluir_aluno_leva_junto_o_registro_de_mensagem(app, academia):
    """O registro de envio é só um toque: não segura a exclusão de um cadastro feito por engano."""
    novo = _salvar(Aluno(nome="Engano Total", email="e@exemplo.com", cpf="666.777.888-08", telefone="11999990000", ativo=True, data_nascimento=NASCEU_HOJE,
                         plano_id=academia["plano"], instrutor_id=academia["dono"], conta_id=academia["conta"]))
    dono = como(app, academia["dono"])
    assert marcar(dono, f"aniversario-{novo}").status_code == 200 and contar(MensagemEnviada) == 1
    dono.post(f"/alunos/{novo}/excluir")
    assert campo(Aluno, novo, "nome") is None and contar(MensagemEnviada) == 0
