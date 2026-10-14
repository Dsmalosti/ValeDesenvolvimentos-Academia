"""
Testes da branch back-25-admin: painel de administração (/admin), quem é admin, números de cada conta, ações de
assinatura, bloqueio à mão, entrar na conta como o dono e apagar a conta depois do prazo.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import inspect

from app.extensions.database import db
from app.helpers.datas import somar_meses
from app.models import AcaoAdmin, Aluno, Conta, Mensalidade, User
from app.services import admin_service
from tests import conftest
from tests.conftest import (conta_de, contar, criar_agendamento, criar_aluno, criar_avaliacao, criar_cobranca_em_aberto, criar_custo,
                            criar_entrada, criar_exercicio, criar_ficha, criar_pagamento, criar_plano, criar_treino, criar_usuario, logar)

HOJE = date.today()
DIA = timedelta(days=1)


@pytest.fixture()
def cenario(app):
    """O admin (com a própria conta) e uma academia cliente com dono, recepção, dois alunos, pagamentos, custos e check-ins."""
    admin = criar_usuario("adauto@teste.local", nome="Adauto")
    with conftest._APP.app_context():
        db.session.get(User, admin).admin_sistema = True
        db.session.commit()
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    plano = criar_plano(dono, nome="Mensal")
    ana = criar_aluno(dono, plano, "Ana Souza", "ana@exemplo.com", "111.222.333-96")
    criar_aluno(dono, plano, "Bia Inativa", "bia@exemplo.com", "529.982.247-25", ativo=False)
    criar_pagamento(dono, ana, 150, HOJE.replace(day=1), HOJE.replace(day=1) + 30 * DIA)
    criar_custo(dono, "Aluguel", 400)
    criar_entrada(dono, ana, datetime.now() - timedelta(hours=1))
    return {"admin": admin, "dono": dono, "conta": conta, "ana": ana, "plano": plano,
            "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao")}


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def da_conta(conta_id, campo):
    with conftest._APP.app_context():
        return getattr(db.session.get(Conta, conta_id), campo)


def mudar(conta_id, **campos):
    with conftest._APP.app_context():
        conta = db.session.get(Conta, conta_id)
        for nome, valor in campos.items():
            setattr(conta, nome, valor)
        db.session.commit()


# ------------------------------------------------------------------ quem entra
def test_so_admin_abre_o_painel(app, cenario):
    for quem in ("dono", "recepcao"):
        cliente = como(app, cenario[quem])
        for url in ("/admin", f"/admin/contas/{cenario['conta']}"):
            assert cliente.get(url).status_code == 404, (quem, url)        # para quem não é admin, a tela não existe
        assert cliente.post(f"/admin/contas/{cenario['conta']}/pagamento", data={"meses": "1"}).status_code == 404
    assert app.test_client().get("/admin").headers["Location"].startswith("/login")
    assert como(app, cenario["admin"]).get("/admin").status_code == 200


def test_comando_liga_e_desliga_o_admin(app, cenario):
    runner = app.test_cli_runner()
    assert runner.invoke(args=["admin-do-sistema", "--email", "DONO@teste.local "]).exit_code == 0
    with conftest._APP.app_context():
        assert db.session.get(User, cenario["dono"]).admin_sistema is True
    assert runner.invoke(args=["admin-do-sistema", "--email", "dono@teste.local", "--remover"]).exit_code == 0
    with conftest._APP.app_context():
        assert db.session.get(User, cenario["dono"]).admin_sistema is False
    assert runner.invoke(args=["admin-do-sistema", "--email", "ninguem@teste.local"]).exit_code != 0


# ------------------------------------------------------------------ números
def test_lista_mostra_os_numeros_de_cada_conta(app, cenario):
    como(app, cenario["dono"]).get("/")                                      # o dono usa o sistema: grava o último acesso
    html = como(app, cenario["admin"]).get("/admin").get_data(as_text=True)
    linha = html.split("Academia de Diana")[1].split("</tr>")[0]
    assert "Teste grátis" in linha and "dias de teste" in linha and "dono@teste.local" in linha
    assert ">1<" in linha                                                    # alunos ativos: só a Ana
    assert "R$ 150,00" in linha and "R$ 400,00" in linha                     # entradas (pagamento do mês) e saídas (custos)
    assert "nunca" not in linha and "parada" not in linha                    # acessou agora há pouco
    assert "Em teste grátis" in html and "Receita por mês" in html

    with conftest._APP.app_context():
        n = admin_service.numeros_da_conta(db.session.get(Conta, cenario["conta"]))
    assert (n["alunos_ativos"], n["pagamentos_mes"], n["entradas_mes"], n["saidas_mes"], n["saldo_mes"], n["checkins_mes"]) == (
        1, 1, Decimal("150"), Decimal("400"), Decimal("-250"), 1)
    assert n["dias_de_teste"] == (somar_meses(HOJE, 2) - HOJE).days


def test_filtro_por_situacao(app, cenario):
    mudar(cenario["conta"], teste_ate=HOJE - 20 * DIA)
    admin = como(app, cenario["admin"])
    assert "Academia de Diana" in admin.get("/admin?situacao=bloqueada").get_data(as_text=True)
    assert "Academia de Diana" not in admin.get("/admin?situacao=teste").get_data(as_text=True)


# ------------------------------------------------------------------ assinatura pelo painel
def test_confirmar_pagamento_e_mudar_o_teste(app, cenario):
    admin = como(app, cenario["admin"])
    ate = HOJE + 90 * DIA                                                    # o piloto ganha 3 meses no total
    admin.post(f"/admin/contas/{cenario['conta']}/teste", data={"ate": ate.isoformat()})
    assert da_conta(cenario["conta"], "teste_ate") == ate
    resposta = admin.post(f"/admin/contas/{cenario['conta']}/pagamento", data={"meses": "2", "valor": "99,98"})
    assert resposta.headers["Location"] == f"/admin/contas/{cenario['conta']}"
    assert da_conta(cenario["conta"], "pago_ate") == somar_meses(ate, 2)
    with conftest._APP.app_context():
        m = Mensalidade.query.one()
        assert (m.valor, m.meses, m.registrado_por_id) == (Decimal("99.98"), 2, cenario["admin"])
        assert [a.acao for a in AcaoAdmin.query.order_by(AcaoAdmin.id)] == ["teste", "pagamento"]
    tela = admin.get(f"/admin/contas/{cenario['conta']}").get_data(as_text=True)
    assert "Mensalidades pagas" in tela and "R$ 99,98" in tela and "adauto@teste.local" in tela
    assert admin.post(f"/admin/contas/{cenario['conta']}/pagamento", data={"meses": "0"}).status_code == 302 and contar(Mensalidade) == 1
    assert admin.post(f"/admin/contas/{cenario['conta']}/teste", data={"ate": "1990-01-01"}).status_code == 302
    assert da_conta(cenario["conta"], "teste_ate") == ate                    # data antes da criação: recusada


def test_bloquear_a_mao_e_retirar(app, cenario):
    admin, dono = como(app, cenario["admin"]), como(app, cenario["dono"])
    admin.post(f"/admin/contas/{cenario['conta']}/bloquear", data={"motivo": ""})
    assert da_conta(cenario["conta"], "bloqueio_manual_em") is None           # sem motivo, não bloqueia
    admin.post(f"/admin/contas/{cenario['conta']}/bloquear", data={"motivo": "Uso em desacordo com os termos"})
    assert da_conta(cenario["conta"], "bloqueio_manual_em") == HOJE
    assert dono.get("/alunos").headers["Location"] == "/assinatura"
    tela = dono.get("/assinatura").get_data(as_text=True)
    assert "bloqueada pelo suporte" in tela and "Uso em desacordo com os termos" in tela and "Pagar por PIX" not in tela
    admin.post(f"/admin/contas/{cenario['conta']}/desbloquear")
    assert dono.get("/alunos").status_code == 200


def test_admin_nunca_e_barrado_e_nao_bloqueia_conta_de_admin(app, cenario):
    mudar(conta_de(cenario["admin"]), teste_ate=HOJE - 30 * DIA)             # a própria conta do admin, vencida há muito
    admin = como(app, cenario["admin"])
    assert admin.get("/alunos").status_code == 200 and admin.get("/admin").status_code == 200
    admin.post(f"/admin/contas/{conta_de(cenario['admin'])}/bloquear", data={"motivo": "teste"})
    assert da_conta(conta_de(cenario["admin"]), "bloqueio_manual_em") is None


# ------------------------------------------------------------------ entrar como o dono
def test_entrar_na_conta_como_o_dono_e_voltar(app, cenario):
    admin = como(app, cenario["admin"])
    resposta = admin.post(f"/admin/contas/{cenario['conta']}/entrar")
    assert resposta.headers["Location"] == "/"
    painel = admin.get("/").get_data(as_text=True)
    assert 'Você está na conta "Academia de Diana" como administrador' in painel and 'action="/admin/voltar"' in painel
    assert "Ana Souza" in admin.get("/alunos").get_data(as_text=True)        # vê os alunos do cliente
    assert admin.get("/admin").status_code == 404                            # dentro da conta, é o dono: o painel não abre
    volta = admin.post("/admin/voltar")
    assert volta.headers["Location"] == f"/admin/contas/{cenario['conta']}"
    assert admin.get("/admin").status_code == 200 and "como administrador" not in admin.get("/").get_data(as_text=True)
    with conftest._APP.app_context():
        assert [a.acao for a in AcaoAdmin.query.order_by(AcaoAdmin.id)] == ["entrou", "saiu"]
        assert db.session.get(User, cenario["dono"]).ultimo_acesso_em is None     # o que o admin fez não conta como acesso do dono
    assert como(app, cenario["dono"]).post("/admin/voltar").status_code == 404    # sem ter entrado como admin, não existe


def test_admin_dentro_de_conta_bloqueada_nao_e_barrado(app, cenario):
    mudar(cenario["conta"], teste_ate=HOJE - 30 * DIA)
    admin = como(app, cenario["admin"])
    admin.post(f"/admin/contas/{cenario['conta']}/entrar")
    assert admin.get("/alunos").status_code == 200                            # para ajudar, o admin vê tudo
    assert como(app, cenario["dono"]).get("/alunos").headers["Location"] == "/assinatura"   # o dono continua bloqueado


def test_ultimo_acesso_e_gravado(app, cenario):
    como(app, cenario["recepcao"]).get("/alunos")
    with conftest._APP.app_context():
        assert db.session.get(User, cenario["recepcao"]).ultimo_acesso_em is not None


# ------------------------------------------------------------------ apagar a conta
def _semear_tudo(dono, ana):
    """Um registro de quase toda tabela ligado à conta (para provar que a exclusão apaga tudo)."""
    criar_cobranca_em_aberto(dono, ana, 100, HOJE, HOJE + 30 * DIA)
    criar_treino(criar_ficha(ana))
    criar_exercicio("Supino da academia", dono)
    criar_avaliacao(dono, ana, HOJE)
    criar_agendamento(dono, ana, HOJE)


def test_apagar_so_depois_do_prazo_e_apaga_tudo_da_conta(app, cenario):
    _semear_tudo(cenario["dono"], cenario["ana"])
    outro = criar_usuario("outro@teste.local", nome="Otto")                  # outra academia, que não pode ser tocada
    vizinho = criar_aluno(outro, criar_plano(outro, nome="B"), "Vizinho", "v@exemplo.com", "987.654.321-00")
    admin = como(app, cenario["admin"])

    admin.post(f"/admin/contas/{cenario['conta']}/apagar", data={"confirmacao": "Academia de Diana"})
    assert da_conta(cenario["conta"], "nome") == "Academia de Diana"          # ainda em teste: não apaga
    mudar(cenario["conta"], teste_ate=HOJE - 20 * DIA)                       # bloqueada há 12 dias: ainda no prazo de guarda
    admin.post(f"/admin/contas/{cenario['conta']}/apagar", data={"confirmacao": "Academia de Diana"})
    assert da_conta(cenario["conta"], "nome") == "Academia de Diana"
    mudar(cenario["conta"], teste_ate=HOJE - 60 * DIA)                       # passou dos 30 dias de guarda
    admin.post(f"/admin/contas/{cenario['conta']}/apagar", data={"confirmacao": "academia errada"})
    assert da_conta(cenario["conta"], "nome") == "Academia de Diana"          # o nome tem de bater
    resposta = admin.post(f"/admin/contas/{cenario['conta']}/apagar", data={"confirmacao": "Academia de Diana"})
    assert resposta.headers["Location"] == "/admin"

    with conftest._APP.app_context():
        assert db.session.get(Conta, cenario["conta"]) is None
        for tabela in inspect(db.engine).get_table_names():                 # nenhuma tabela guarda nada da conta apagada
            colunas = {c["name"] for c in inspect(db.engine).get_columns(tabela)}
            if "conta_id" in colunas and tabela != "acoes_admin":
                assert db.session.execute(db.text(f"SELECT count(*) FROM {tabela} WHERE conta_id = :c"), {"c": cenario["conta"]}).scalar() == 0, tabela
        assert db.session.execute(db.text("SELECT count(*) FROM ficha")).scalar() == 0
        assert db.session.execute(db.text("SELECT count(*) FROM treino")).scalar() == 0
        assert db.session.get(Aluno, vizinho) is not None and db.session.get(User, outro) is not None
        apagou = AcaoAdmin.query.filter_by(acao="apagou").one()
        assert (apagou.conta_nome, apagou.admin_email) == ("Academia de Diana", "adauto@teste.local")
    with conftest._APP.app_context():
        assert db.session.get(User, cenario["dono"]) is None and db.session.get(User, cenario["recepcao"]) is None   # os logins da conta somem
    assert "<b>Academia de Diana</b>" not in admin.get("/admin").get_data(as_text=True)     # some da lista (o aviso de sucesso ainda cita o nome)
