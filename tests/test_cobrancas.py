"""Testes da branch back-09-cobranca: gerar a cobrança, receber (PIX manual, cartão, dinheiro), renovar, diária e extrato."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import Aluno, Cobranca, Pagamento, Plano
from app.services import painel_service
from tests.conftest import (campo, conta_de, contar, criar_aluno, criar_cobranca_em_aberto, criar_pagamento, criar_plano,
                            criar_usuario, logar, _salvar)

HOJE = date.today()
DIA = timedelta(days=1)


@pytest.fixture()
def academia(app):
    """Dona, recepção (Rita) e instrutor; planos Mensal (R$ 100, 30 dias) e Anual (R$ 900, 365 dias); a aluna Ana, no Mensal."""
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    dados = {"dono": dono, "conta": conta,
             "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
             "instrutor": criar_usuario("igor@teste.local", nome="Igor", conta=conta, papel="instrutor"),
             "mensal": criar_plano(dono, nome="Mensal"),
             "anual": _salvar(Plano(nome="Anual", valor=900, duracao_dias=365, descricao="", ativo=True, instrutor_id=dono, conta_id=conta))}
    dados["ana"] = criar_aluno(dono, dados["mensal"], "Ana Souza", "ana@exemplo.com", "111.222.333-96")
    return dados


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def do_painel(app, usuario_id):
    """O dicionário que o painel monta para este usuário."""
    with app.test_request_context():
        from flask_login import login_user
        from app.extensions.database import db
        from app.models import User
        login_user(db.session.get(User, usuario_id))
        return painel_service.montar_painel()


def unica(app, modelo, **filtros):
    with app.app_context():
        registro = modelo.query.filter_by(**filtros).one()
        return {c.name: getattr(registro, c.name) for c in modelo.__table__.columns}


# ------------------------------------------------------------------ tela de receber
def test_tela_de_receber_mostra_a_cobranca_e_o_pix_manual(app, academia):
    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    html = como(app, academia["recepcao"]).get(f"/cobrancas/{cobranca}/receber").get_data(as_text=True)

    assert 'class="rail"' in html and "Receber de Ana Souza" in html and "R$ 100,00" in html and "Mensal" in html
    assert (HOJE + 30 * DIA).strftime("%d/%m/%Y") in html
    # PIX do lançamento: a recepção confere e confirma. A opção fica habilitada, sem "Não configurado" e sem QR Code.
    assert "Já recebi o PIX" in html and "Você confirma" in html
    assert "Não configurado" not in html and "Gerar cobrança PIX" not in html and "Ligar o PIX agora" not in html
    assert ">None<" not in html


@pytest.mark.parametrize("forma", ["pix", "debito", "credito", "dinheiro"])
def test_confirmar_cria_o_pagamento_e_quita_a_cobranca(app, academia, forma):
    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    recepcao = como(app, academia["recepcao"])

    resposta = recepcao.post(f"/cobrancas/{cobranca}/confirmar", data={"forma": forma, "valor_recebido": "100,00"})

    assert resposta.status_code == 302 and resposta.headers["Location"] == f"/cobrancas/{cobranca}/receber?ok=1"
    pagamento = unica(app, Pagamento, cobranca_id=cobranca)
    assert (pagamento["forma"], pagamento["valor_pago"], pagamento["origem_confirmacao"]) == (forma, Decimal("100.00"), "manual")
    assert pagamento["confirmado_por_instrutor_id"] == academia["recepcao"] and pagamento["conta_id"] == academia["conta"]
    assert pagamento["data_pagamento"].date() == HOJE
    assert campo(Cobranca, cobranca, "status") == "paga"

    tela = recepcao.get(resposta.headers["Location"]).get_data(as_text=True)
    assert "Pagamento confirmado" in tela and "Confirmado manualmente por Rita" in tela     # toda confirmação mostra a origem


def test_confirmar_duas_vezes_nao_cria_dois_pagamentos(app, academia):
    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    recepcao = como(app, academia["recepcao"])
    for _ in range(2):      # toque duplo no botão, ou página recarregada
        assert recepcao.post(f"/cobrancas/{cobranca}/confirmar", data={"forma": "dinheiro"}).status_code == 302
    assert contar(Pagamento, cobranca_id=cobranca) == 1


def test_valor_recebido_diferente_fica_gravado_no_pagamento(app, academia):
    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    como(app, academia["dono"]).post(f"/cobrancas/{cobranca}/confirmar", data={"forma": "credito", "valor_recebido": "97,50"})

    assert unica(app, Pagamento, cobranca_id=cobranca)["valor_pago"] == Decimal("97.50")
    assert campo(Cobranca, cobranca, "valor") == Decimal("100.00")      # o que era devido não muda


@pytest.mark.parametrize("dados", [{"forma": "cheque"}, {"forma": ""}, {"forma": "pix", "valor_recebido": "100.00"},
                                   {"forma": "pix", "valor_recebido": "0,00"}, {"forma": "pix", "valor_recebido": "abc"}])
def test_confirmacao_invalida_nao_quita(app, academia, dados):
    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    resposta = como(app, academia["dono"]).post(f"/cobrancas/{cobranca}/confirmar", data=dados)

    assert resposta.status_code == 302 and "ok=1" not in resposta.headers["Location"]
    assert contar(Pagamento) == 0 and campo(Cobranca, cobranca, "status") == "pendente"


def test_cobranca_cancelada_some(app, academia):
    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    with app.app_context():
        from app.extensions.database import db
        db.session.get(Cobranca, cobranca).status = "cancelada"
        db.session.commit()
    dono = como(app, academia["dono"])
    assert dono.get(f"/cobrancas/{cobranca}/receber").status_code == 404
    assert dono.post(f"/cobrancas/{cobranca}/confirmar", data={"forma": "pix"}).status_code == 404


# ------------------------------------------------------------------ situação do aluno
def test_quem_paga_fica_em_dia_ate_o_vencimento_da_cobranca(app, academia):
    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    dono = como(app, academia["dono"])
    assert "Ana Souza" in dono.get("/alunos?status=pendente").get_data(as_text=True)     # em aberto e já começou: pendente

    dono.post(f"/cobrancas/{cobranca}/confirmar", data={"forma": "pix"})

    assert "Ana Souza" not in dono.get("/alunos?status=pendente").get_data(as_text=True)
    perfil = dono.get(f"/alunos/{academia['ana']}").get_data(as_text=True)
    assert (HOJE + 30 * DIA).strftime("%d/%m/%Y") in perfil and "R$ 100,00" in perfil and "Em dia" in perfil


def test_cobranca_em_aberto_que_ainda_nao_comecou_nao_deixa_pendente(app, academia):
    criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE + 5 * DIA, HOJE + 35 * DIA)
    dono = como(app, academia["dono"])
    assert "Ana Souza" not in dono.get("/alunos?status=pendente").get_data(as_text=True)
    assert do_painel(app, academia["dono"])["k"]["inad_qtd"] == 0


def test_painel_soma_o_que_entrou_e_o_que_esta_em_aberto(app, academia):
    bia = criar_aluno(academia["dono"], academia["anual"], "Bia Lima", "bia@exemplo.com", "555.666.777-20")
    criar_pagamento(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    criar_cobranca_em_aberto(academia["dono"], bia, 900, HOJE - 3 * DIA, HOJE + 362 * DIA)

    k = do_painel(app, academia["dono"])["k"]

    assert k["faturamento"] == 100.0                      # só o que foi recebido
    assert (k["inad_qtd"], k["inadimplencia"]) == (1, 900.0)   # a Bia deve a cobrança em aberto, pelo valor DELA


def test_pagar_reativa_aluno_inativo(app, academia):
    with app.app_context():
        from app.extensions.database import db
        db.session.get(Aluno, academia["ana"]).ativo = False
        db.session.commit()
    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    como(app, academia["dono"]).post(f"/cobrancas/{cobranca}/confirmar", data={"forma": "pix"})
    assert campo(Aluno, academia["ana"], "ativo") is True


def test_excluir_aluno_com_cobranca_mantem_a_cobranca_sem_o_nome(app, academia):
    # [back-19-lgpd] antes: aluno com histórico não podia ser excluído. Agora os dados pessoais são apagados e o cadastro, anonimizado.
    criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    dono = como(app, academia["dono"])
    dono.post(f"/alunos/{academia['ana']}/excluir")
    dono.post(f"/alunos/excluir/{academia['ana']}")       # a rota antiga também
    assert contar(Aluno, id=academia["ana"]) == 1 and contar(Cobranca, aluno_id=academia["ana"]) == 1      # o financeiro não muda
    assert campo(Aluno, academia["ana"], "nome") == "Aluno removido" and campo(Aluno, academia["ana"], "cpf") is None


# ------------------------------------------------------------------ renovar
def test_tela_de_renovar_mostra_os_planos_com_o_novo_vencimento(app, academia):
    criar_pagamento(academia["dono"], academia["ana"], 100, HOJE - 20 * DIA, HOJE + 10 * DIA)     # em dia até daqui a 10 dias
    html = como(app, academia["recepcao"]).get(f"/alunos/{academia['ana']}/renovar").get_data(as_text=True)

    assert "Renovar com qual plano?" in html and "Mensal" in html and "Anual" in html
    assert (HOJE + 40 * DIA).strftime("%d/%m/%Y") in html      # Mensal: começa no vencimento atual, não hoje
    assert (HOJE + 375 * DIA).strftime("%d/%m/%Y") in html     # Anual


def test_renovar_e_receber_gera_a_cobranca_e_troca_o_plano(app, academia):
    criar_pagamento(academia["dono"], academia["ana"], 100, HOJE - 60 * DIA, HOJE - 30 * DIA)     # venceu há 30 dias
    resposta = como(app, academia["recepcao"]).post(f"/alunos/{academia['ana']}/renovar",
                                                    data={"plano_id": str(academia["anual"]), "acao": "receber"})

    cobranca = unica(app, Cobranca, aluno_id=academia["ana"], status="pendente")
    assert resposta.headers["Location"] == f"/cobrancas/{cobranca['id']}/receber"
    assert (cobranca["tipo"], cobranca["plano_id"], cobranca["valor"]) == ("renovacao", academia["anual"], Decimal("900.00"))
    assert (cobranca["data_inicio"], cobranca["data_vencimento"]) == (HOJE, HOJE + 365 * DIA)     # já venceu: recomeça hoje
    assert campo(Aluno, academia["ana"], "plano_id") == academia["anual"]


def test_renovar_sem_cobrar_deixa_em_aberto_e_nao_empilha(app, academia):
    dono = como(app, academia["dono"])
    for plano in ("mensal", "anual"):       # renovou, mudou de ideia e renovou de novo: continua UMA cobrança
        resposta = dono.post(f"/alunos/{academia['ana']}/renovar", data={"plano_id": str(academia[plano]), "acao": "sem_cobrar"})
        assert resposta.headers["Location"] == f"/alunos/{academia['ana']}"

    cobranca = unica(app, Cobranca, aluno_id=academia["ana"])
    assert (cobranca["status"], cobranca["tipo"], cobranca["plano_id"]) == ("pendente", "matricula", academia["anual"])   # nunca pagou: é matrícula
    assert contar(Pagamento) == 0


@pytest.mark.parametrize("plano_id", ["", "abc", "999", "DE_FORA", "PAUSADO"])
def test_renovar_com_plano_invalido_nao_gera_nada(app, academia, plano_id):
    if plano_id == "DE_FORA":
        plano_id = str(criar_plano(criar_usuario("outro@teste.local", nome="Otto"), nome="Plano-B"))
    elif plano_id == "PAUSADO":
        plano_id = str(_salvar(Plano(nome="Antigo", valor=50, duracao_dias=30, descricao="", ativo=False,
                                     instrutor_id=academia["dono"], conta_id=academia["conta"])))
    como(app, academia["dono"]).post(f"/alunos/{academia['ana']}/renovar", data={"plano_id": plano_id, "acao": "receber"})
    assert contar(Cobranca) == 0 and campo(Aluno, academia["ana"], "plano_id") == academia["mensal"]


def test_valor_da_cobranca_fica_congelado(app, academia):
    dono = como(app, academia["dono"])
    dono.post(f"/alunos/{academia['ana']}/renovar", data={"plano_id": str(academia["mensal"]), "acao": "sem_cobrar"})
    dono.post(f"/planos/{academia['mensal']}/editar", data={"nome": "Mensal", "valor": "150,00", "duracao_dias": "30", "ativo": "1"})

    assert campo(Plano, academia["mensal"], "valor") == Decimal("150.00")
    assert unica(app, Cobranca, aluno_id=academia["ana"])["valor"] == Decimal("100.00")


def test_faturamento_por_plano_usa_o_plano_da_epoca(app, academia):
    criar_pagamento(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)      # pagou estando no Mensal
    with app.app_context():
        from app.extensions.database import db
        db.session.get(Aluno, academia["ana"]).plano_id = academia["anual"]             # depois trocou de plano
        db.session.commit()

    por_plano = {x["nome"]: x["valor"] for x in do_painel(app, academia["dono"])["planos_fat"]}
    assert por_plano == {"Mensal": 100.0, "Anual": 0.0}


# ------------------------------------------------------------------ diária avulsa
def test_diaria_avulsa_e_entrada_de_caixa_sem_aluno(app, academia):
    recepcao = como(app, academia["recepcao"])
    resposta = recepcao.post("/cobrancas/diaria", data={"nome_visitante": "João da Silva", "valor": "25,00", "forma_pagamento": "dinheiro"})

    cobranca = unica(app, Cobranca, tipo="diaria")
    assert resposta.headers["Location"] == f"/cobrancas/{cobranca['id']}/receber?forma=dinheiro"
    assert (cobranca["aluno_id"], cobranca["plano_id"], cobranca["valor"], cobranca["nome_visitante"]) == (None, None, Decimal("25.00"), "João da Silva")
    tela = recepcao.get(resposta.headers["Location"]).get_data(as_text=True)
    assert "Receber de João da Silva" in tela and "Diária avulsa" in tela and ">None<" not in tela

    recepcao.post(f"/cobrancas/{cobranca['id']}/confirmar", data={"forma": "dinheiro", "valor_recebido": "25,00"})
    painel = do_painel(app, academia["dono"])
    assert painel["k"]["faturamento"] == 25.0
    assert [(x["nome"], x["valor"], x["alunos"]) for x in painel["planos_fat"] if x.get("avulso")] == [("Avulsos", 25.0, 1)]
    assert "João da Silva" not in recepcao.get("/alunos").get_data(as_text=True)     # visitante não vira aluno


@pytest.mark.parametrize("valor", ["0,00", "abc", "25.00"])
def test_diaria_com_valor_invalido_nao_gera_cobranca(app, academia, valor):
    resposta = como(app, academia["dono"]).post("/cobrancas/diaria", data={"valor": valor})
    assert resposta.headers["Location"] == "/" and contar(Cobranca) == 0


# ------------------------------------------------------------------ extrato
def test_extrato_do_aluno_na_tela_e_em_csv(app, academia):
    criar_pagamento(academia["recepcao"], academia["ana"], 100, HOJE, HOJE + 30 * DIA, forma="dinheiro")
    dono = como(app, academia["dono"])

    html = dono.get(f"/alunos/{academia['ana']}/pagamentos").get_data(as_text=True)
    assert "Todos os pagamentos" in html and "Dinheiro" in html and "Rita confirmou" in html and "R$ 100,00" in html

    csv = dono.get(f"/alunos/{academia['ana']}/pagamentos?formato=csv")
    texto = csv.get_data(as_text=True)
    assert csv.headers["Content-Type"].startswith("text/csv") and f"extrato-{academia['ana']}.csv" in csv.headers["Content-Disposition"]
    assert texto.startswith("﻿Data;Forma;Valor;Confirmado por") and f"{HOJE.strftime('%d/%m/%Y')};Dinheiro;100,00;Rita" in texto


# ------------------------------------------------------------------ quem pode e isolamento
def test_instrutor_nao_entra_em_nada_de_dinheiro(app, academia):
    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    instrutor = como(app, academia["instrutor"])
    for metodo, url in [("GET", f"/cobrancas/{cobranca}/receber"), ("POST", f"/cobrancas/{cobranca}/confirmar"),
                        ("GET", f"/cobrancas/{cobranca}/status"), ("GET", f"/cobrancas/{cobranca}/depois"),
                        ("GET", f"/cobrancas/matricula/{academia['ana']}"), ("POST", "/cobrancas/diaria"),
                        ("POST", f"/cobrancas/{cobranca}/pix"), ("POST", "/cobrancas/lembrete"),
                        ("GET", f"/alunos/{academia['ana']}/renovar"), ("POST", f"/alunos/{academia['ana']}/renovar"),
                        ("GET", f"/alunos/{academia['ana']}/pagamentos")]:
        assert instrutor.open(url, method=metodo, data={"forma": "pix", "plano_id": str(academia["mensal"])}).status_code == 403, f"{metodo} {url}"
    assert campo(Cobranca, cobranca, "status") == "pendente" and contar(Cobranca) == 1


def test_cobranca_e_aluno_de_outra_academia_dao_404(app, academia):
    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    outro = como(app, criar_usuario("outro@teste.local", nome="Otto"))
    for metodo, url in [("GET", f"/cobrancas/{cobranca}/receber"), ("POST", f"/cobrancas/{cobranca}/confirmar"),
                        ("GET", f"/cobrancas/{cobranca}/status"), ("GET", f"/cobrancas/{cobranca}/depois"),
                        ("POST", f"/cobrancas/{cobranca}/pix"), ("POST", f"/cobrancas/{cobranca}/cancelar-pix"),
                        ("GET", f"/cobrancas/matricula/{academia['ana']}"),
                        ("GET", f"/alunos/{academia['ana']}/renovar"), ("POST", f"/alunos/{academia['ana']}/renovar"),
                        ("GET", f"/alunos/{academia['ana']}/pagamentos"), ("GET", f"/alunos/{academia['ana']}/pagamentos?formato=csv"),
                        ("GET", f"/pagamentos/registrar/{academia['ana']}"), ("GET", f"/pagamentos/listar/{academia['ana']}")]:
        assert outro.open(url, method=metodo, data={"forma": "pix", "plano_id": str(academia["mensal"])}).status_code == 404, f"{metodo} {url}"
    assert campo(Cobranca, cobranca, "status") == "pendente" and contar(Pagamento) == 0 and contar(Cobranca) == 1


# ------------------------------------------------------------------ rotas de apoio
def test_status_cobrar_depois_e_atalho_da_matricula(app, academia):
    dono = como(app, academia["dono"])
    assert dono.get(f"/cobrancas/matricula/{academia['ana']}").headers["Location"] == f"/alunos/{academia['ana']}/renovar"   # nada em aberto
    assert contar(Cobranca) == 0                                                           # um GET nunca cria cobrança

    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    assert dono.get(f"/cobrancas/matricula/{academia['ana']}").headers["Location"] == f"/cobrancas/{cobranca}/receber"
    assert dono.get(f"/cobrancas/{cobranca}/status").get_json() == {"estado": "pendente", "origem": None}
    assert dono.get(f"/cobrancas/{cobranca}/depois").headers["Location"] == f"/alunos/{academia['ana']}"
    assert campo(Cobranca, cobranca, "status") == "pendente"                               # "cobrar depois" não muda nada

    dono.post(f"/cobrancas/{cobranca}/confirmar", data={"forma": "pix"})
    assert dono.get(f"/cobrancas/{cobranca}/status").get_json() == {"estado": "confirmado", "origem": "manual"}


def test_pix_automatico_ainda_nao_existe(app, academia):
    cobranca = criar_cobranca_em_aberto(academia["dono"], academia["ana"], 100, HOJE, HOJE + 30 * DIA)
    dono = como(app, academia["dono"])
    assert dono.post(f"/cobrancas/{cobranca}/pix").headers["Location"] == f"/cobrancas/{cobranca}/receber?forma=pix"
    assert dono.post(f"/cobrancas/{cobranca}/cancelar-pix").headers["Location"] == f"/cobrancas/{cobranca}/receber"
    assert campo(Cobranca, cobranca, "status") == "pendente" and contar(Pagamento) == 0


def test_telas_antigas_de_pagamento_levam_para_as_novas(app, academia):
    dono = como(app, academia["dono"])
    assert dono.get(f"/pagamentos/registrar/{academia['ana']}").headers["Location"] == f"/alunos/{academia['ana']}/renovar"
    assert dono.get(f"/pagamentos/listar/{academia['ana']}").headers["Location"] == f"/alunos/{academia['ana']}/pagamentos"
    assert dono.get("/pagamentos/situacao/").headers["Location"] == "/alunos?status=pendente"
