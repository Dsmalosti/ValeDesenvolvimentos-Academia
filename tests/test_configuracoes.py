"""Testes da branch back-12-config: dados da academia, horário, modelos de mensagem, funcionalidades, metas, recebimento e inatividade automática."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from werkzeug.datastructures import MultiDict

from app.models import Aluno, Conta, ModeloMensagem
from app.services import painel_service, relatorio_service
from tests import conftest
from tests.conftest import (campo, conta_de, contar, criar_aluno, criar_pagamento, criar_plano, criar_usuario, logar)


def app_do_teste():
    return conftest._APP

HOJE = date.today()
DIA = timedelta(days=1)


@pytest.fixture()
def academia(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    plano = criar_plano(dono, nome="Mensal")
    return {"dono": dono, "conta": conta, "plano": plano,
            "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
            "instrutor": criar_usuario("igor@teste.local", nome="Igor", conta=conta, papel="instrutor"),
            "ana": criar_aluno(dono, plano, "Ana Souza", "ana@exemplo.com", "111.222.333-96")}


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def logado(app, usuario_id, funcao, *args, **kwargs):
    with app.test_request_context():
        from flask_login import login_user
        from app.extensions.database import db
        from app.models import User
        login_user(db.session.get(User, usuario_id))
        return funcao(*args, **kwargs)


def da_conta_(academia, nome_do_campo):
    return campo(Conta, academia["conta"], nome_do_campo)


# ------------------------------------------------------------------ a tela
@pytest.mark.parametrize("aba", ["", "academia", "equipe", "mensagens", "cobranca", "integracoes", "metas", "nao-existe"])
def test_cada_aba_abre_sem_none(app, academia, aba):
    html = como(app, academia["dono"]).get(f"/configuracoes?aba={aba}").get_data(as_text=True)
    assert 'class="rail"' in html and "Configurações" in html and ">None<" not in html and 'value="None"' not in html


def test_tela_mostra_equipe_modelos_padrao_e_horario_sem_dado(app, academia):
    html = como(app, academia["dono"]).get("/configuracoes?aba=academia").get_data(as_text=True)
    assert "Diana Teste" in html and "Rita Teste" in html and "Igor Teste" in html and "Proprietário" in html and "Instrutor" in html
    assert "Cobrança de mensalidade" in html and "Sua mensalidade de [valor] venceu em [data]" in html
    assert "Não informado" in html


def test_instrutor_nao_ve_metas(app, academia):
    html = como(app, academia["instrutor"]).get("/configuracoes?aba=metas").get_data(as_text=True)
    assert "Salvar metas" not in html and "aba=metas" not in html


# ------------------------------------------------------------------ dados da academia e horário
def test_salvar_dados_da_academia_e_o_nome_aparece_no_sistema(app, academia):
    dono = como(app, academia["dono"])
    resposta = dono.post("/configuracoes/academia", data={"nome": "  Corpo em   Movimento ", "cnpj": "41.234.567/0001-89", "telefone": "(12) 3333-4444",
                                                          "email": "Contato@Corpo.com", "cidade": "Tremembé / SP", "endereco": "Rua das Acácias, 120"})
    assert resposta.headers["Location"] == "/configuracoes?aba=academia"
    assert [da_conta_(academia, c) for c in ("nome", "cnpj", "telefone", "email", "cidade", "endereco")] == [
        "Corpo em Movimento", "41.234.567/0001-89", "(12) 3333-4444", "contato@corpo.com", "Tremembé / SP", "Rua das Acácias, 120"]
    assert "Corpo em Movimento" in dono.get("/").get_data(as_text=True)


@pytest.mark.parametrize("dados", [{"nome": ""}, {"nome": "x" * 121}, {"nome": "Ok", "cnpj": "123"}, {"nome": "Ok", "email": "sem-arroba"}])
def test_dados_invalidos_nao_gravam(app, academia, dados):
    antes = da_conta_(academia, "nome")
    como(app, academia["dono"]).post("/configuracoes/academia", data=dados)
    assert da_conta_(academia, "nome") == antes and da_conta_(academia, "cnpj") is None


def test_horario(app, academia):
    dono = como(app, academia["dono"])
    dono.post("/configuracoes/horario", data={"semana": "06h - 22h", "sabado": "08h - 14h", "domingo": "Fechado"})
    assert [da_conta_(academia, c) for c in ("horario_semana", "horario_sabado", "horario_domingo")] == ["06h - 22h", "08h - 14h", "Fechado"]
    html = dono.get("/configuracoes?aba=academia").get_data(as_text=True)
    assert "06h - 22h" in html and "Não informado" not in html

    dono.post("/configuracoes/horario", data={"semana": "", "sabado": "08h", "domingo": "Fechado"})       # falta um: não grava
    dono.post("/configuracoes/horario", data={"semana": "x" * 41, "sabado": "08h", "domingo": "Fechado"})
    assert da_conta_(academia, "horario_semana") == "06h - 22h"


# ------------------------------------------------------------------ modelos de mensagem
def test_modelo_de_mensagem_e_por_academia(app, academia):
    recepcao = como(app, academia["recepcao"])                                  # é a recepção que manda as mensagens
    recepcao.post("/configuracoes/mensagem", data={"tipo": "sumido", "texto": "Oi [nome], bora voltar?"})
    recepcao.post("/configuracoes/mensagem", data={"tipo": "sumido", "texto": "Oi [nome], sentimos sua falta!"})      # altera a mesma linha
    with app.app_context():
        modelo = ModeloMensagem.query.one()
        assert (modelo.tipo, modelo.texto, modelo.conta_id) == ("sumido", "Oi [nome], sentimos sua falta!", academia["conta"])

    html = recepcao.get("/configuracoes?aba=mensagens").get_data(as_text=True)
    assert "Oi [nome], sentimos sua falta!" in html and "Parabéns, [nome]!" in html           # os outros continuam no padrão
    outra = como(app, criar_usuario("outro@teste.local", nome="Otto")).get("/configuracoes?aba=mensagens").get_data(as_text=True)
    assert "sentimos sua falta!" not in outra.replace("[nome], sentimos sua falta! Faz", "")   # a outra academia vê o padrão dela


@pytest.mark.parametrize("dados", [{"tipo": "sumido", "texto": "   "}, {"tipo": "inventado", "texto": "Oi"}, {"tipo": "sumido", "texto": "x" * 501}])
def test_mensagem_invalida_nao_grava(app, academia, dados):
    como(app, academia["dono"]).post("/configuracoes/mensagem", data=dados)
    assert contar(ModeloMensagem) == 0


def test_texto_da_mensagem_nao_vira_codigo_na_tela(app, academia):
    dono = como(app, academia["dono"])
    dono.post("/configuracoes/mensagem", data={"tipo": "sumido", "texto": "<script>alert(1)</script>"})
    html = dono.get("/configuracoes?aba=mensagens").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html


# ------------------------------------------------------------------ funcionalidades
def test_ligar_e_desligar_o_checkin_persiste(app, academia):
    dono = como(app, academia["dono"])
    dono.post("/configuracoes/funcionalidade", data={"chave": "frequencia", "ligado": "1"})
    assert da_conta_(academia, "checkin_ativo") is True and dono.get("/frequencia").status_code == 200

    dono.post("/configuracoes/funcionalidade", data={"chave": "frequencia", "ligado": "0"})
    assert da_conta_(academia, "checkin_ativo") is False and dono.get("/frequencia").headers["Location"] == "/"


def test_inatividade_e_lembretes(app, academia):
    dono = como(app, academia["dono"])
    # [back-22-ajustes-de-produto] antes: (True, 60, True). A inatividade automática nasce desligada.
    assert (da_conta_(academia, "inatividade_ligada"), da_conta_(academia, "inatividade_dias"), da_conta_(academia, "lembretes_ligados")) == (False, 60, True)

    dono.post("/configuracoes/funcionalidade", data={"chave": "inatividade", "ligado": "1", "dias": "30"})
    dono.post("/configuracoes/funcionalidade", data={"chave": "lembretes", "ligado": "0"})
    assert (da_conta_(academia, "inatividade_dias"), da_conta_(academia, "lembretes_ligados")) == (30, False)

    for dias in ("5", "999", "abc"):                                            # fora de 15 a 365: não grava
        dono.post("/configuracoes/funcionalidade", data={"chave": "inatividade", "ligado": "1", "dias": dias})
    dono.post("/configuracoes/funcionalidade", data={"chave": "inventada", "ligado": "1"})
    assert da_conta_(academia, "inatividade_dias") == 30


# ------------------------------------------------------------------ metas
def test_metas_viram_a_linha_dos_graficos(app, academia):
    criar_pagamento(academia["dono"], academia["ana"], 500, HOJE, HOJE + 30 * DIA)
    dono = como(app, academia["dono"])
    assert logado(app, academia["dono"], painel_service.montar_painel)["k"]["fat_meta"] is None       # sem meta definida

    resposta = dono.post("/configuracoes/metas", data={"alunos_ativos": "250", "faturamento": "2.000,00", "retencao": "70"})

    assert resposta.headers["Location"] == "/configuracoes?aba=metas"
    assert [da_conta_(academia, c) for c in ("meta_alunos_ativos", "meta_faturamento", "meta_retencao")] == [250, Decimal("2000.00"), 70]
    painel = logado(app, academia["dono"], painel_service.montar_painel)
    assert painel["serie"]["meta"] == 250 and (painel["k"]["fat_meta"], painel["k"]["fat_meta_pct"]) == (2000.0, 25)
    adm = logado(app, academia["dono"], relatorio_service.contexto_do_painel, MultiDict())
    assert (adm["grafico"]["meta"], adm["grafico"]["meta_rotulo"], adm["retencao"]["meta"]) == (2000, "meta", 70)
    tela = dono.get("/configuracoes?aba=metas").get_data(as_text=True)
    assert 'value="250"' in tela and 'value="2.000,00"' in tela and "25% da meta" in tela and "sem dado ainda" in tela
    assert ">None<" not in dono.get("/").get_data(as_text=True)


def test_metas_invalidas_voltam_com_os_avisos(app, academia):
    resposta = como(app, academia["dono"]).post("/configuracoes/metas", data={"alunos_ativos": "0", "faturamento": "2000.00", "retencao": "150"})
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    for aviso in ("Use um número de alunos maior que zero.", "Informe um valor maior que zero", "A retenção vai de 1% a 100%."):
        assert aviso in html
    assert da_conta_(academia, "meta_alunos_ativos") is None


# ------------------------------------------------------------------ recebimento
def test_recebimento_mostra_de_onde_veio_cada_confirmacao(app, academia):
    for forma in ("pix", "pix", "debito", "dinheiro"):
        criar_pagamento(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA, forma=forma)
    criar_pagamento(academia["dono"], academia["ana"], 100, HOJE - 40 * DIA, HOJE - 10 * DIA)        # outro mês: fora
    dono = como(app, academia["dono"])

    html = dono.get("/configuracoes/recebimento").get_data(as_text=True)
    assert "4 pagamentos recebidos" in html and "Setembro ·" not in html.replace(relatorio_service.MESES[HOJE.month - 1].capitalize() + " ·", "")
    origem = logado(app, academia["dono"], lambda: __import__("app.services.config_service", fromlist=["x"]).contexto_do_recebimento())["origem"]
    assert [(i["nome"], i["qtd"], i["pct"]) for i in origem["itens"]] == [
        ("Confirmado pelo banco", 0, 0), ("PIX, na mão", 2, 50), ("Maquininha, na mão", 1, 25), ("Dinheiro, na mão", 1, 25)]

    assert dono.post("/configuracoes/recebimento/pix", data={"ligado": "1"}).headers["Location"] == "/configuracoes/recebimento"
    assert da_conta_(academia, "pix_ligado") is False                            # PIX automático ainda não existe: não liga


# ------------------------------------------------------------------ quem pode
def test_so_o_dono_muda_a_academia_e_a_recepcao_so_as_mensagens(app, academia):
    posts = ["/configuracoes/academia", "/configuracoes/horario", "/configuracoes/funcionalidade", "/configuracoes/metas",
             "/configuracoes/equipe", "/configuracoes/recebimento/pix"]
    dados = {"nome": "Invadida", "semana": "x", "sabado": "x", "domingo": "x", "chave": "frequencia", "ligado": "1",
             "alunos_ativos": "1", "faturamento": "1,00", "retencao": "1", "tipo": "sumido", "texto": "Oi"}
    for papel in ("recepcao", "instrutor"):
        for url in posts:
            assert como(app, academia[papel]).post(url, data=dados).status_code == 403, f"{papel} {url}"
    assert como(app, academia["instrutor"]).post("/configuracoes/mensagem", data=dados).status_code == 403
    assert como(app, academia["instrutor"]).get("/configuracoes/recebimento").status_code == 403
    assert como(app, academia["recepcao"]).get("/configuracoes/recebimento").status_code == 200
    assert da_conta_(academia, "nome") != "Invadida" and da_conta_(academia, "checkin_ativo") is False and contar(ModeloMensagem) == 0


# (convidar, trocar papel e remover da equipe: tests/test_equipe.py, da back-13)


# ------------------------------------------------------------------ inatividade automática
def ligar_inatividade(academia):
    """[back-22-ajustes-de-produto] a regra nasce desligada; os testes dela ligam pela tela de Configurações, como o dono faria."""
    como(app_do_teste(), academia["dono"]).post("/configuracoes/funcionalidade", data={"chave": "inatividade", "ligado": "1", "dias": "60"})
    assert da_conta_(academia, "inatividade_ligada") is True


def test_nasce_desligada_e_ninguem_e_desativado(app, academia):
    """[back-22-ajustes-de-produto] sem ligar a regra, abrir o painel não desativa ninguém."""
    criar_pagamento(academia["dono"], academia["ana"], 100, HOJE - 100 * DIA, HOJE - 70 * DIA)       # venceu há 70 dias
    como(app, academia["dono"]).get("/")
    assert campo(Aluno, academia["ana"], "ativo") is True


def test_quem_nao_renova_ha_mais_de_60_dias_vira_inativo_sozinho(app, academia):
    ligar_inatividade(academia)
    bruno = criar_aluno(academia["dono"], academia["plano"], "Bruno Dias", "bruno@exemplo.com", "555.666.777-20")
    nunca = criar_aluno(academia["dono"], academia["plano"], "Nunca Pagou", "nunca@exemplo.com", "123.456.789-09")
    criar_pagamento(academia["dono"], academia["ana"], 100, HOJE - 100 * DIA, HOJE - 70 * DIA)       # venceu há 70 dias
    criar_pagamento(academia["dono"], bruno, 100, HOJE - 60 * DIA, HOJE - 30 * DIA)                  # venceu há 30: ainda não
    outro = criar_usuario("outro@teste.local", nome="Otto")
    vizinho = criar_aluno(outro, criar_plano(outro, nome="Plano-B"), "Vizinho", "v@exemplo.com", "987.654.321-00")
    criar_pagamento(outro, vizinho, 100, HOJE - 200 * DIA, HOJE - 170 * DIA)                         # de outra academia

    como(app, academia["dono"]).get("/")                                         # abrir o painel roda a regra

    assert campo(Aluno, academia["ana"], "ativo") is False and campo(Aluno, academia["ana"], "data_inativacao") is not None
    assert campo(Aluno, bruno, "ativo") is True and campo(Aluno, nunca, "ativo") is True
    assert campo(Aluno, vizinho, "ativo") is True                                # o painel de uma academia não mexe em outra
    assert da_conta_(academia, "inatividade_conferida_em") == HOJE


def test_regra_roda_uma_vez_por_dia_e_respeita_o_desligado(app, academia):
    ligar_inatividade(academia)
    dono = como(app, academia["dono"])
    dono.get("/")                                                                # já rodou hoje (ninguém para desativar)
    criar_pagamento(academia["dono"], academia["ana"], 100, HOJE - 100 * DIA, HOJE - 70 * DIA)
    dono.get("/")
    assert campo(Aluno, academia["ana"], "ativo") is True                         # hoje não roda de novo

    outro = criar_usuario("outro@teste.local", nome="Otto")
    vizinho = criar_aluno(outro, criar_plano(outro, nome="Plano-B"), "Vizinho", "v@exemplo.com", "987.654.321-00")
    criar_pagamento(outro, vizinho, 100, HOJE - 200 * DIA, HOJE - 170 * DIA)
    cliente = como(app, outro)
    cliente.post("/configuracoes/funcionalidade", data={"chave": "inatividade", "ligado": "0"})
    cliente.get("/")
    assert campo(Aluno, vizinho, "ativo") is True                                 # regra desligada: ninguém é desativado
