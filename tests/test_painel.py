"""Testes da branch back-04-painel: painel novo, pontes para as telas antigas, telas pendentes e páginas de erro."""
from datetime import date

import pytest
from flask_login import login_user

from app.blueprints.pendentes import PENDENTES
from app.extensions.database import db
from app.models import User
from app.services.painel_service import montar_painel
from tests.conftest import (criar_aluno, criar_pagamento, criar_plano, criar_usuario, logar,
                            numero_do_card)

HOJE = date(2026, 10, 15)


@pytest.fixture()
def academia(app):
    """
    Uma academia com situações conhecidas, vista em 15/10/2026:
      Ana    ativa, entrou em outubro, pagou 150 em 05/10 (vence 05/11)   -> em dia
      Bia    ativa, entrou em maio,    pagou 100 em 01/09 (vence 01/10)   -> 14 dias em atraso
      Caio   ativo, entrou em setembro, nunca pagou                        -> sem vencimento
      Duda   ativa, entrou em 2025,    pagou 100 em 20/09 (vence 20/10)   -> vence este mês
      Enzo   inativo
    E outra academia (B) com aluno e pagamento, que não pode entrar em nenhuma conta.
    """
    dono = criar_usuario("dono@teste.local", nome="Marina")
    mensal = criar_plano(dono, nome="Mensal")          # valor 100
    ana = criar_aluno(dono, mensal, "Ana Souza", "ana@teste.local", "1", cadastrado_em=date(2026, 10, 3),
                      nascimento=date(1990, 10, 15))   # faz aniversário em 15/10
    bia = criar_aluno(dono, mensal, "Bia Lima", "bia@teste.local", "2", cadastrado_em=date(2026, 5, 10))
    criar_aluno(dono, mensal, "Caio Reis", "caio@teste.local", "3", cadastrado_em=date(2026, 9, 20))
    duda = criar_aluno(dono, mensal, "Duda Paz", "duda@teste.local", "4", cadastrado_em=date(2025, 3, 1))
    criar_aluno(dono, mensal, "Enzo Dias", "enzo@teste.local", "5", ativo=False, cadastrado_em=date(2026, 1, 5))
    criar_pagamento(dono, ana, 150, date(2026, 10, 5), date(2026, 11, 5))
    criar_pagamento(dono, bia, 100, date(2026, 9, 1), date(2026, 10, 1))
    criar_pagamento(dono, duda, 100, date(2026, 9, 20), date(2026, 10, 20))

    outro = criar_usuario("outro@teste.local", nome="Outro")
    plano_b = criar_plano(outro, nome="Plano-B")
    aluno_b = criar_aluno(outro, plano_b, "Aluno-B", "b@teste.local", "9", cadastrado_em=date(2026, 10, 1))
    criar_pagamento(outro, aluno_b, 777, date(2026, 10, 2), date(2026, 9, 1))
    return dono


def painel_de(app, usuario_id, hoje=HOJE):
    """Roda montar_painel() como se o usuário estivesse logado."""
    with app.test_request_context():
        login_user(db.session.get(User, usuario_id))
        return montar_painel(hoje=hoje)


def test_indicadores_do_painel(app, academia):
    k = painel_de(app, academia)["k"]

    assert k["ativos"] == 4 and k["inativos"] == 1
    assert k["novas"] == 1 and k["ativos_delta"] == 1          # só a Ana entrou em outubro
    assert k["novas_delta"] == 0                               # setembro também teve 1 (o Caio)
    assert k["faturamento"] == 150                             # só o pagamento de outubro
    assert k["fat_delta"] == -25                               # setembro recebeu 200
    assert k["inad_qtd"] == 1 and k["inadimplencia"] == 100    # só a Bia está em atraso
    assert k["vencimentos"] == 1 and k["vencimentos_valor"] == 100   # só a Duda vence ainda este mês
    assert k["ticket"] == pytest.approx(37.5)                  # 150 / 4 ativos
    assert k["aniversarios"] == 1
    assert k["ano_delta"] == 300                               # 1 ativo já cadastrado em 2025 -> 4 hoje
    assert k["ausentes"] is None and k["fat_meta_pct"] is None  # sem dado, não zero


def test_listas_batem_com_os_numeros(app, academia):
    painel = painel_de(app, academia)

    assert [x["nome"] for x in painel["pendentes"]] == ["Bia Lima"]
    assert painel["pendentes"][0]["vence_txt"] == "Venceu 01/10"
    assert [x["nome"] for x in painel["listas"]["vencem"]] == ["Duda Paz"]
    assert [x["aluno"]["nome"] for x in painel["listas"]["novas"]] == ["Ana Souza"]
    assert painel["alertas"]["risco"][0]["motivo"] == "Pagamento atrasado há 14 dias"
    assert painel["alertas"]["aniversarios"][0] == {"nome": "Ana Souza", "motivo": "Completa 36 anos hoje"}
    assert [x["nome"] for x in painel["alertas"]["renovacao"]] == ["Bia Lima"]
    assert painel["alunos"][0]["nome"] == "Ana Souza" and painel["alunos"][0]["status"] == "ativo"
    assert {x["nome"]: x["status"] for x in painel["alunos"]}["Bia Lima"] == "pendente"
    assert painel["hoje"] == "Quinta-feira, 15 de outubro"


def test_graficos(app, academia):
    painel = painel_de(app, academia)

    serie = painel["serie"]
    assert serie["labels"] == ["Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out"]
    assert serie["valores"] == [1, 1, 1, 2, 2, 2, 2, 3, 4]     # ativos de hoje já cadastrados em cada mês
    assert serie["meta"] is None and serie["periodo"] == "Fevereiro a outubro de 2026"
    assert painel["planos_fat"] == [{"plano_id": 1, "nome": "Mensal", "alunos": 4, "dias": 30,
                                     "valor": 150.0, "pct": 100, "cor": "blue-dark"}]


def test_painel_nao_mistura_contas(app, academia):
    """A outra academia tem um aluno e um pagamento de 777; nada disso pode aparecer."""
    painel = painel_de(app, academia)
    texto = str(painel)

    assert "Aluno-B" not in texto and "Plano-B" not in texto and "777" not in texto


def test_academia_sem_nada_nao_quebra(app):
    vazio = criar_usuario("novo@teste.local", nome="Novo")
    painel = painel_de(app, vazio)

    assert painel["k"]["ativos"] == 0 and painel["k"]["ticket"] == 0
    assert painel["k"]["fat_delta"] is None and painel["k"]["ano_delta"] is None
    assert painel["planos_fat"] == [] and painel["alunos"] == []


@pytest.mark.parametrize("com_dados", [True, False])
def test_pagina_do_painel_abre_no_layout_novo(cliente, app, com_dados):
    dono = criar_usuario("dono@teste.local", nome="Marina")
    if com_dados:
        plano = criar_plano(dono)
        aluno = criar_aluno(dono, plano, "Ana Souza", "ana@teste.local", "1")
        criar_pagamento(dono, aluno, 100, date.today(), date.today())
    logar(cliente, dono)

    pagina = cliente.get("/")
    html = pagina.get_data(as_text=True)

    assert pagina.status_code == 200
    assert 'class="rail"' in html and "Painel Gerencial" in html and "Olá, Marina" in html
    assert numero_do_card(html, "Alunos ativos") == ("1" if com_dados else "0")
    # nada de "None" escapando para a tela quando falta dado
    for sujeira in (">None<", "None%", "+None", "meta None", "R$ None"):
        assert sujeira not in html, f'apareceu "{sujeira}" no painel'
    # o card e o popup de avaliações com nomes de exemplo ficam escondidos
    assert "Camila Duarte" not in html and "dlg-avaliacoes-hoje" not in html


def test_login_leva_para_o_painel_novo(cliente):
    dono = criar_usuario("dono@teste.local")
    logar(cliente, dono)

    assert cliente.get("/login").headers["Location"] == "/"
    assert cliente.get("/inicio-antigo/").headers["Location"] == "/"   # a tela inicial antiga virou atalho


@pytest.mark.parametrize("origem, destino", [
    ("/alunos/7/renovar", "/pagamentos/registrar/7"),      # as pontes de lista, cadastro, busca e perfil viraram telas de verdade na back-07
    ("/alunos/7/pagamentos", "/pagamentos/listar/7"),
    # as pontes de planos (/planos e /planos/novo) viraram telas de verdade na back-08
    ("/exercicios", "/exercicios/listar/"),
    ("/treinos", "/fichas/listar/"),
])
def test_pontes_levam_para_as_telas_antigas(cliente, origem, destino):
    logar(cliente, criar_usuario("dono@teste.local"))
    resposta = cliente.get(origem)
    assert resposta.status_code == 302 and resposta.headers["Location"] == destino


def test_telas_pendentes_respondem_em_construcao(cliente):
    logar(cliente, criar_usuario("dono@teste.local"))
    for _bp, _funcao, endereco, metodos, nome in PENDENTES:
        url = endereco.replace("<int:id>", "1")
        if metodos == ["POST"]:
            resposta = cliente.post(url)
            assert resposta.status_code == 302 and resposta.headers["Location"] == "/", url
        else:
            resposta = cliente.get(url)
            html = resposta.get_data(as_text=True)
            assert resposta.status_code == 200 and "Em construção" in html and nome in html, url
            assert 'class="rail"' in html, f"{url} não usa o layout novo"
    assert "Em construção" in cliente.get("/notificacoes").get_data(as_text=True)


def test_pagina_de_erro_404_do_front_novo(cliente):
    anonimo = cliente.get("/endereco-que-nao-existe")
    assert anonimo.status_code == 404 and "Página não encontrada" in anonimo.get_data(as_text=True)

    logar(cliente, criar_usuario("dono@teste.local"))
    logado = cliente.get("/alunos/editar/99999")
    assert logado.status_code == 404 and "Página não encontrada" in logado.get_data(as_text=True)
