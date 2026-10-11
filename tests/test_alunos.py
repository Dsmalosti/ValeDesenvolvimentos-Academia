"""Testes da branch back-07-alunos: telas de alunos do front novo (lista, busca, perfil, cadastro, edição)."""
from datetime import date, timedelta

import pytest

from app.models import Aluno, Plano
from tests.conftest import (campo, conta_de, contar, criar_aluno, criar_ficha, criar_pagamento, criar_plano,
                            criar_usuario, logar, _salvar)

HOJE = date.today()


@pytest.fixture()
def academia(app):
    """Dono, recepção e instrutor de uma academia com um plano ativo, um pausado e dois alunos."""
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    dados = {"dono": dono, "conta": conta,
             "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
             "instrutor": criar_usuario("igor@teste.local", nome="Igor", conta=conta, papel="instrutor"),
             "mensal": criar_plano(dono, nome="Mensal"),
             "pausado": _salvar(Plano(nome="Plano Antigo", valor=80, duracao_dias=30, descricao="", ativo=False,
                                      instrutor_id=dono, conta_id=conta))}
    dados["ana"] = criar_aluno(dono, dados["mensal"], "Ana Souza", "ana@exemplo.com", "111.222.333-96")
    dados["bia"] = criar_aluno(dono, dados["mensal"], "Bia Lima", "bia@exemplo.com", "55566677720", ativo=False)
    return dados


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def formulario(academia, **trocas):
    """Um cadastro válido, como o navegador envia (com máscaras). `trocas` muda campos para cada teste."""
    dados = {"nome": "Carlos Prado", "cpf": "123.456.789-09", "telefone": "(12) 98211-4432", "email": "Carlos@Exemplo.com",
             "data_nascimento": "25/12/1990", "plano_id": str(academia["mensal"]), "data_inicio": HOJE.strftime("%d/%m/%Y"),
             "forma_pagamento": "pix", "dia_vencimento": "10", "observacoes": "Prefere treinar cedo."}
    dados.update(trocas)
    return dados


# ------------------------------------------------------------------ lista
def test_lista_mostra_os_alunos_e_as_contagens(app, academia):
    criar_pagamento(academia["dono"], academia["ana"], 100, HOJE - timedelta(days=40), HOJE - timedelta(days=10))
    html = como(app, academia["dono"]).get("/alunos").get_data(as_text=True)

    assert 'class="rail"' in html                                   # layout novo
    assert "Ana Souza" in html and "Bia Lima" in html
    assert "2 cadastros · 1 ativos · 1 com pagamento pendente" in html
    assert "None" not in html


@pytest.mark.parametrize("consulta, aparece, some", [
    ("q=ana", "Ana Souza", "Bia Lima"),              # pedaço do nome, sem diferenciar maiúscula
    ("q=555.666", "Bia Lima", "Ana Souza"),          # números do CPF, com ou sem pontos
    ("status=ativos", "Ana Souza", "Bia Lima"),
    ("status=inativo", "Bia Lima", "Ana Souza"),
])
def test_filtros_da_lista(app, academia, consulta, aparece, some):
    html = como(app, academia["dono"]).get("/alunos?" + consulta).get_data(as_text=True)
    corpo = html.split('id="novo-aluno"')[0]          # ignora o popup de cadastro, que vem depois da lista
    assert aparece in corpo and some not in corpo


def test_filtro_pendente_usa_a_mesma_regra_do_painel(app, academia):
    criar_pagamento(academia["dono"], academia["ana"], 100, HOJE - timedelta(days=40), HOJE - timedelta(days=10))
    corpo = como(app, academia["dono"]).get("/alunos?status=pendente").get_data(as_text=True).split('id="novo-aluno"')[0]
    assert "Ana Souza" in corpo and "Bia Lima" not in corpo and "Pendente" in corpo


def test_lista_pagina_de_8_em_8(app, academia):
    for i in range(9):
        criar_aluno(academia["dono"], academia["mensal"], f"Aluno Extra{i}", f"extra{i}@exemplo.com", f"000{i}")
    dono = como(app, academia["dono"])
    pagina1 = dono.get("/alunos").get_data(as_text=True).split('id="novo-aluno"')[0]
    pagina2 = dono.get("/alunos?pagina=2").get_data(as_text=True).split('id="novo-aluno"')[0]

    assert "Mostrando 1-8 de 11 alunos" in pagina1 and "Mostrando 9-11 de 11 alunos" in pagina2
    assert "Aluno Extra8" in pagina1 and "Ana Souza" not in pagina1 and "Ana Souza" in pagina2   # os mais novos vêm primeiro
    assert dono.get("/alunos?pagina=99").status_code == 200           # página que não existe cai na última


def test_lista_nao_mostra_aluno_de_outra_academia(app, academia):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    criar_aluno(outro, criar_plano(outro, nome="Plano-B"), "Zeca Vizinho", "zeca@exemplo.com", "999")
    html = como(app, academia["dono"]).get("/alunos").get_data(as_text=True)
    assert "Zeca Vizinho" not in html and "Plano-B" not in html


# ------------------------------------------------------------------ cadastro
def test_tela_de_cadastro_so_oferece_plano_ativo_da_conta(app, academia):
    html = como(app, academia["dono"]).get("/alunos/novo").get_data(as_text=True)
    assert "Mensal" in html and "Plano Antigo" not in html


def test_cadastrar_aluno(app, academia):
    resposta = como(app, academia["recepcao"]).post("/alunos/novo", data=formulario(academia))
    novo_id = int(resposta.headers["Location"].rsplit("/", 1)[1])

    assert resposta.status_code == 302 and resposta.headers["Location"] == f"/alunos/{novo_id}"
    esperado = {"nome": "Carlos Prado", "cpf": "123.456.789-09", "email": "carlos@exemplo.com", "telefone": "(12) 98211-4432",
                "data_nascimento": date(1990, 12, 25), "data_inicio": HOJE, "dia_vencimento": 10, "forma_pagamento": "pix",
                "observacoes": "Prefere treinar cedo.", "plano_id": academia["mensal"], "ativo": True,
                "conta_id": academia["conta"], "instrutor_id": academia["recepcao"]}
    for nome_do_campo, valor in esperado.items():
        assert campo(Aluno, novo_id, nome_do_campo) == valor, nome_do_campo


@pytest.mark.parametrize("trocas, campo_com_erro, mensagem", [
    ({"nome": "Carlos"}, "nome", "Informe nome e sobrenome."),
    ({"cpf": "123.456"}, "cpf", "CPF inválido"),
    ({"cpf": "123.456.789-00"}, "cpf", "CPF inválido"),                               # 11 números, dígitos finais errados
    ({"cpf": "111.111.111-11"}, "cpf", "CPF inválido"),                               # todos iguais
    ({"cpf": "111.222.333-96"}, "cpf", "Já existe um aluno com este CPF."),           # o da Ana
    ({"cpf": "555.666.777-20"}, "cpf", "Já existe um aluno com este CPF."),           # o da Bia, gravado sem pontos
    ({"telefone": "9821"}, "telefone", "Informe o telefone com DDD."),
    ({"email": "sem-arroba"}, "email", "E-mail inválido."),
    ({"email": "ANA@exemplo.com"}, "email", "Já existe um aluno com este e-mail."),
    ({"data_nascimento": "31/02/1990"}, "data_nascimento", "Data inválida"),
    ({"data_nascimento": "01/01/2999"}, "data_nascimento", "Confira a data de nascimento."),
    ({"plano_id": ""}, "plano_id", "Escolha um plano."),
    ({"plano_id": "PAUSADO"}, "plano_id", "Este plano está pausado."),
    ({"plano_id": "DE_OUTRA_CONTA"}, "plano_id", "Escolha um plano."),
    ({"forma_pagamento": "cheque"}, "forma_pagamento", "Escolha a forma de pagamento."),
    ({"dia_vencimento": "31"}, "dia_vencimento", "Escolha um dia entre 1 e 28."),
    ({"data_inicio": ""}, "data_inicio", "Informe a data de início."),
])
def test_cadastro_invalido_avisa_e_nao_grava(app, academia, trocas, campo_com_erro, mensagem):
    if trocas.get("plano_id") == "PAUSADO":
        trocas = {"plano_id": str(academia["pausado"])}
    elif trocas.get("plano_id") == "DE_OUTRA_CONTA":
        trocas = {"plano_id": str(criar_plano(criar_usuario("outro@teste.local", nome="Otto"), nome="Plano-B"))}
    antes = contar(Aluno)

    resposta = como(app, academia["dono"]).post("/alunos/novo", data=formulario(academia, **trocas))
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 200 and mensagem in html, f"faltou a mensagem de {campo_com_erro}"
    assert contar(Aluno) == antes
    assert 'value="Prefere' not in html and "Prefere treinar cedo." in html      # devolve o que foi digitado


def test_observacoes_grandes_demais_avisa_no_topo(app, academia):
    # o campo de observações é o único sem lugar para mensagem no front: o aviso vai no topo da tela
    resposta = como(app, academia["dono"]).post("/alunos/novo", data=formulario(academia, observacoes="x" * 1001))

    # o aviso do topo vai dentro de um JSON (os acentos saem codificados), por isso confere só o trecho sem acento
    assert "1000 letras." in resposta.get_data(as_text=True)
    assert contar(Aluno, nome="Carlos Prado") == 0


def test_mesmo_cpf_em_outra_academia_pode(app, academia):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    dados = formulario(academia, cpf="111.222.333-96", email="ana@exemplo.com", plano_id=str(criar_plano(outro, nome="Plano-B")))
    assert como(app, outro).post("/alunos/novo", data=dados).status_code == 302
    assert contar(Aluno, cpf="111.222.333-96") == 2


def test_nome_com_html_nao_vira_codigo_na_tela(app, academia):
    """Texto digitado pelo usuário sempre aparece como texto, nunca como HTML (proteção contra XSS)."""
    dono = como(app, academia["dono"])
    resposta = dono.post("/alunos/novo", data=formulario(academia, nome="<script>alert(1)</script> Silva", observacoes="<b>negrito</b>"))
    perfil = dono.get(resposta.headers["Location"]).get_data(as_text=True)
    lista = dono.get("/alunos").get_data(as_text=True)
    for html in (perfil, lista):
        assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    assert "<b>negrito</b>" not in perfil


# ------------------------------------------------------------------ perfil
def test_perfil_do_aluno(app, academia):
    dono = como(app, academia["dono"])
    novo = dono.post("/alunos/novo", data=formulario(academia)).headers["Location"]
    novo_id = int(novo.rsplit("/", 1)[1])
    criar_pagamento(academia["dono"], novo_id, 149.9, HOJE, HOJE + timedelta(days=30))

    html = dono.get(novo).get_data(as_text=True)

    for trecho in ("Carlos Prado", "123.456.789-09", "Mensal", "PIX", "Prefere treinar cedo.", "R$ 149,90", "Em dia",
                   (HOJE + timedelta(days=30)).strftime("%d/%m/%Y")):
        assert trecho in html, trecho
    assert "None" not in html


def test_perfil_de_aluno_antigo_sem_os_campos_novos_nao_quebra(app, academia):
    html = como(app, academia["dono"]).get(f"/alunos/{academia['ana']}").get_data(as_text=True)
    assert "Ana Souza" in html and "Não informada" in html and "Sem pagamento registrado" in html
    assert "None" not in html and "Nenhum pagamento registrado ainda." in html


def test_perfil_de_outra_academia_da_404(app, academia):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    for metodo, url in [("GET", "/alunos/{}"), ("GET", "/alunos/{}/editar"), ("POST", "/alunos/{}/editar"),
                        ("POST", "/alunos/{}/inativar"), ("POST", "/alunos/{}/excluir"), ("POST", "/alunos/{}/acesso"),
                        ("GET", "/alunos/{}/ficha")]:
        resposta = como(app, outro).open(url.format(academia["ana"]), method=metodo, data=formulario(academia))
        assert resposta.status_code in (404, 302), f"{metodo} {url}"
        if resposta.status_code == 302:                       # só a ponte da ficha redireciona; e para a lista, sem achar nada
            assert resposta.headers["Location"] == "/fichas/listar/"
    assert campo(Aluno, academia["ana"], "nome") == "Ana Souza" and campo(Aluno, academia["ana"], "ativo") is True


def test_instrutor_ve_o_aluno_mas_nao_os_pagamentos(app, academia):
    criar_pagamento(academia["dono"], academia["ana"], 432, HOJE, HOJE + timedelta(days=30))
    do_instrutor = como(app, academia["instrutor"]).get(f"/alunos/{academia['ana']}").get_data(as_text=True)
    do_dono = como(app, academia["dono"]).get(f"/alunos/{academia['ana']}").get_data(as_text=True)
    assert "Ana Souza" in do_instrutor and "R$ 432,00" not in do_instrutor
    assert "R$ 432,00" in do_dono


def test_botao_da_ficha_leva_a_ficha_do_aluno(app, academia):
    dono = como(app, academia["dono"])
    assert dono.get(f"/alunos/{academia['ana']}/ficha").headers["Location"] == "/fichas/listar/"
    ficha = criar_ficha(academia["ana"])
    assert dono.get(f"/alunos/{academia['ana']}/ficha").headers["Location"] == f"/fichas/detalhes/{ficha}"


# ------------------------------------------------------------------ edição, inativar, excluir
def test_editar_aluno(app, academia):
    dono = como(app, academia["dono"])
    tela = dono.get(f"/alunos/{academia['ana']}/editar").get_data(as_text=True)
    assert 'value="Ana Souza"' in tela and 'value="111.222.333-96"' in tela

    resposta = dono.post(f"/alunos/{academia['ana']}/editar", data=formulario(academia, nome="Ana Souza Lima", cpf="111.222.333-96",
                                                                             email="ana@exemplo.com", dia_vencimento="5"))
    assert resposta.status_code == 302 and resposta.headers["Location"] == f"/alunos/{academia['ana']}"
    assert campo(Aluno, academia["ana"], "nome") == "Ana Souza Lima"       # o próprio CPF e e-mail não contam como repetidos
    assert campo(Aluno, academia["ana"], "dia_vencimento") == 5
    assert campo(Aluno, academia["ana"], "data_inicio") is None             # a data de início não é campo da edição


def test_inativar_nao_apaga(app, academia):
    dono = como(app, academia["dono"])
    assert dono.get(f"/alunos/{academia['ana']}/inativar").status_code == 405     # só por POST
    assert dono.post(f"/alunos/{academia['ana']}/inativar").headers["Location"] == "/alunos"
    assert contar(Aluno, id=academia["ana"]) == 1 and campo(Aluno, academia["ana"], "ativo") is False


def test_excluir_e_so_do_dono_e_recusa_quem_tem_historico(app, academia):
    assert como(app, academia["recepcao"]).post(f"/alunos/{academia['ana']}/excluir").status_code == 403
    criar_pagamento(academia["dono"], academia["bia"], 100, HOJE, HOJE)
    dono = como(app, academia["dono"])

    com_historico = dono.post(f"/alunos/{academia['bia']}/excluir", follow_redirects=True).get_data(as_text=True)
    assert contar(Aluno, id=academia["bia"]) == 1 and "tem fichas ou pagamentos registrados" in com_historico

    assert dono.post(f"/alunos/{academia['ana']}/excluir").headers["Location"] == "/alunos"
    assert contar(Aluno, id=academia["ana"]) == 0


@pytest.mark.parametrize("metodo, url", [("GET", "/alunos/novo"), ("POST", "/alunos/novo"), ("GET", "/alunos/1/editar"),
                                         ("POST", "/alunos/1/inativar"), ("POST", "/alunos/1/excluir"), ("GET", "/alunos/exportar")])
def test_instrutor_nao_cadastra_nem_exporta(app, academia, metodo, url):
    assert como(app, academia["instrutor"]).open(url, method=metodo).status_code == 403


# ------------------------------------------------------------------ exportar e buscar
def test_exportar_csv_respeita_o_filtro(app, academia):
    resposta = como(app, academia["dono"]).get("/alunos/exportar?status=ativos")
    texto = resposta.get_data(as_text=True)

    assert resposta.headers["Content-Type"].startswith("text/csv") and "alunos.csv" in resposta.headers["Content-Disposition"]
    assert texto.startswith("\ufeffNome;CPF;Telefone;E-mail;Plano;Vencimento;Status")
    assert "Ana Souza;111.222.333-96" in texto and "Bia Lima" not in texto


def test_exportar_csv_nao_leva_aluno_de_outra_academia_nem_formula(app, academia):
    outro = criar_usuario("outro-csv@teste.local", nome="Olga")
    criar_aluno(outro, criar_plano(outro, nome="Plano-B"), "Vizinho Alheio", "vizinho@exemplo.com", "987.654.321-00")
    # nome que o Excel executaria como fórmula se fosse escrito do jeito que veio
    criar_aluno(academia["dono"], academia["mensal"], "=HYPERLINK(\"http://x\")", "formula@exemplo.com", "987.654.320-29")

    texto = como(app, academia["dono"]).get("/alunos/exportar").get_data(as_text=True)

    assert "Ana Souza" in texto and "Vizinho Alheio" not in texto
    assert "'=HYPERLINK" in texto and "\n=HYPERLINK" not in texto and ";=HYPERLINK" not in texto


def test_busca_ao_vivo_devolve_so_o_pedaco(app, academia):
    dono = como(app, academia["dono"])
    pagina = dono.get("/alunos/buscar?q=ana").get_data(as_text=True)
    pedaco = dono.get("/alunos/buscar?q=ana&partial=1").get_data(as_text=True)
    renovar = dono.get("/alunos/buscar?q=ana&partial=1&acao=renovar").get_data(as_text=True)

    assert "<html" in pagina and "Ana Souza" in pagina
    assert "<html" not in pedaco and "Ana Souza" in pedaco and f'/alunos/{academia["ana"]}"' in pedaco
    assert f'/alunos/{academia["ana"]}/renovar' in renovar
    assert "Ana Souza" not in dono.get("/alunos/buscar?q=a&partial=1").get_data(as_text=True)   # menos de 2 letras não busca
