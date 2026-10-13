"""Testes da branch back-19-lgpd: termos e política publicados, aceite registrado, vontade do aluno sobre o WhatsApp, exportar e apagar os dados de um aluno."""
import json
import os
import re
from datetime import date, datetime, timedelta

import pytest

from app.models import (Aluno, AvaliacaoAgendada, AvaliacaoFisica, Cobranca, Ficha, Frequencia, MensagemEnviada, Pagamento, Treino, User)
from app.services import legal_service
from tests.conftest import (SENHA_TESTE, _salvar, campo, conta_de, contar, criar_agendamento, criar_aluno, criar_avaliacao, criar_entrada,
                            criar_ficha, criar_pagamento, criar_plano, criar_treino, criar_usuario, logar)

HOJE = date.today()
DIA = timedelta(days=1)


@pytest.fixture()
def academia(app):
    """Dona, recepção e instrutor. Ana tem de tudo (pagamento, entrada, ficha, avaliação feita e marcada); Bia só o cadastro."""
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    plano = criar_plano(dono, nome="Mensal")
    ana = criar_aluno(dono, plano, "Ana Souza", "ana@exemplo.com", "111.222.333-96", nascimento=date(1990, HOJE.month, min(HOJE.day, 28)))
    bia = criar_aluno(dono, plano, "Bia Lima", "bia@exemplo.com", "555.666.777-20")
    criar_pagamento(dono, ana, 100, HOJE - 5 * DIA, HOJE + 25 * DIA)
    criar_entrada(dono, ana, datetime.now() - timedelta(hours=2))
    criar_treino(criar_ficha(ana, nome="Ficha da Ana"))
    criar_avaliacao(dono, ana, HOJE - 10 * DIA, peso=68.4, altura=167, restricoes="dor no joelho")
    criar_agendamento(dono, ana, HOJE + DIA, "10:00")
    return {"dono": dono, "conta": conta, "plano": plano, "mensal": plano, "ana": ana, "bia": bia,
            "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
            "instrutor": criar_usuario("igor@teste.local", nome="Igor", conta=conta, papel="instrutor")}


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


# ------------------------------------------------------------------ páginas públicas
@pytest.mark.parametrize("url, titulo, trecho", [("/termos", "Termos de Uso", "Período de teste e preço"), ("/privacidade", "Política de Privacidade", "Seus direitos")])
def test_termos_e_politica_sao_paginas_publicas(app, url, titulo, trecho):
    resposta = app.test_client().get(url)                                        # sem login
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 200 and titulo in html and trecho in html and f"Versão {legal_service.VERSAO}" in html
    assert "Versão preliminar 0.2" in html and "ainda em revisão" in html         # avisa que o texto vai passar por revisão
    assert "<mark>a definir</mark>" in html and "PREENCHER" not in html           # o que só o Adauto sabe aparece como "a definir"
    corpo = html.split('<article class="legal">')[1].split("</article>")[0]
    assert "**" not in corpo and "|---" not in corpo and "\n## " not in corpo and "RASCUNHO" not in corpo      # nada de Markdown cru
    assert "<h3>" in corpo and "<ul>" in corpo and "<strong>" in corpo
    assert "default-src 'self'" in resposta.headers["Content-Security-Policy"]


def test_os_dois_textos_apontam_um_para_o_outro_e_a_politica_bate_com_o_sistema(app):
    termos = app.test_client().get("/termos").get_data(as_text=True)
    politica = app.test_client().get("/privacidade").get_data(as_text=True)
    assert '<a href="/privacidade">Política de Privacidade</a>' in termos and 'href="/termos"' in politica
    assert "<table>" in politica and "12 horas sem uso" in politica and "<td>30 dias</td>" in politica        # prazos de sessão que o sistema aplica de fato
    assert "sem nada que identifique o aluno" in politica and 'href="https://www.gov.br/anpd" target="_blank" rel="noopener noreferrer"' in politica


def test_o_leitor_de_markdown_nao_deixa_passar_codigo():
    texto = "# Título\n\nOi <script>alert(1)</script> **forte** e [clique](javascript:alert(1)) e [ok](https://exemplo.com) e [outro](termos-de-uso).\n\n| a | b |\n|---|---|\n| <img src=x onerror=1> | 2 |\n"
    titulo, html = legal_service.para_html(texto, lambda endpoint: f"/{endpoint}")
    html = str(html)
    assert titulo == "Título" and "<script>" not in html and "&lt;script&gt;" in html and "<strong>forte</strong>" in html
    assert "javascript:" not in html and "clique" in html                        # link que não é https nem interno vira só o texto
    assert '<a href="https://exemplo.com" target="_blank" rel="noopener noreferrer">ok</a>' in html and '<a href="/legal.termos">outro</a>' in html
    assert "<img" not in html and "&lt;img" in html and "<td>2</td>" in html


# ------------------------------------------------------------------ aceite ao criar a conta
def test_criar_conta_mostra_os_links_e_grava_a_versao_aceita(app):
    cliente = app.test_client()
    tela = cliente.get("/criar-conta").get_data(as_text=True)
    assert 'href="/termos"' in tela and 'href="/privacidade"' in tela and "#termos" not in tela
    antes = datetime.now() - timedelta(seconds=5)
    cliente.post("/criar-conta", data={"tipo": "academia", "nome": "Nova Dona", "email": "nova@teste.local", "senha": SENHA_TESTE})
    with app.app_context():
        nova = User.query.filter_by(email="nova@teste.local").one()
        assert nova.termos_versao == legal_service.VERSAO and nova.termos_aceitos_em >= antes


def test_quem_ja_tinha_conta_ou_entrou_por_convite_fica_sem_aceite_gravado(app, academia):
    assert campo(User, academia["dono"], "termos_versao") is None and campo(User, academia["recepcao"], "termos_aceitos_em") is None


# ------------------------------------------------------------------ vontade do aluno sobre o WhatsApp
def _cadastro(academia, **trocas):
    from tests.test_alunos import formulario
    return formulario(academia, **trocas)


def test_cadastro_grava_se_o_aluno_aceita_whatsapp(app, academia):
    dono = como(app, academia["dono"])
    tela = dono.get("/alunos/novo").get_data(as_text=True)
    assert "Aceita receber avisos pelo WhatsApp" in tela and 'name="aceita_whatsapp" value="1" aria-labelledby="lb-whats" checked' in tela     # vem marcado

    dono.post("/alunos/novo", data=_cadastro(academia, whatsapp_perguntado="1", aceita_whatsapp="1"))
    dono.post("/alunos/novo", data=_cadastro(academia, nome="Dora Recusa", cpf="529.982.247-25", email="dora@exemplo.com", whatsapp_perguntado="1"))
    dono.post("/alunos/novo", data=_cadastro(academia, nome="Formulario Antigo", cpf="168.995.350-09", email="fa@exemplo.com"))
    with app.app_context():
        valores = {a.nome: a.aceita_whatsapp for a in Aluno.query.all()}
    assert valores["Carlos Prado"] is True and valores["Dora Recusa"] is False and valores["Formulario Antigo"] is None      # sem a caixa na tela, nada muda
    assert valores["Ana Souza"] is None                                                                                    # quem já existia: ainda não perguntado

    with app.app_context():
        dora = Aluno.query.filter_by(nome="Dora Recusa").one().id
    editar = dono.get(f"/alunos/{dora}/editar").get_data(as_text=True)
    assert 'name="aceita_whatsapp" value="1" aria-labelledby="lb-whats"><span' in editar          # quem recusou abre desmarcado
    dono.post(f"/alunos/{dora}/editar", data=_cadastro(academia, nome="Dora Recusa", cpf="529.982.247-25", email="dora@exemplo.com",
                                                        whatsapp_perguntado="1", aceita_whatsapp="1"))
    assert campo(Aluno, dora, "aceita_whatsapp") is True


def test_quem_recusou_whatsapp_nao_entra_na_fila_de_mensagens(app, academia):
    from app.extensions.database import db
    dono = como(app, academia["dono"])
    with app.app_context():
        db.session.get(Aluno, academia["ana"]).data_nascimento = date(1990, HOJE.month, HOJE.day) if (HOJE.month, HOJE.day) != (2, 29) else date(1992, 2, 29)
        db.session.commit()
    fila = dono.get("/mensagens").get_data(as_text=True)
    assert "Ana Souza" in fila and "Avaliação amanhã às 10:00" in fila            # aniversário de hoje e avaliação de amanhã
    with app.app_context():
        db.session.get(Aluno, academia["ana"]).aceita_whatsapp = False
        db.session.commit()
    fila = dono.get("/mensagens").get_data(as_text=True)
    assert "Ana Souza" not in fila and "0 para enviar" in fila
    assert dono.post("/mensagens/enviada", json={"id": f"aniversario-{academia['ana']}"}).status_code == 404     # nem dá para marcar


# ------------------------------------------------------------------ exportar
def test_dono_baixa_tudo_o_que_o_sistema_guarda_sobre_o_aluno(app, academia):
    resposta = como(app, academia["dono"]).get(f"/alunos/{academia['ana']}/dados")
    assert resposta.status_code == 200 and resposta.headers["Content-Type"].startswith("application/json")
    assert f"dados-do-aluno-{academia['ana']}.json" in resposta.headers["Content-Disposition"] and resposta.headers["Cache-Control"] == "no-store"
    dados = json.loads(resposta.get_data(as_text=True))
    assert dados["cadastro"]["nome"] == "Ana Souza" and dados["cadastro"]["cpf"] == "111.222.333-96" and dados["cadastro"]["plano"] == "Mensal"
    assert len(dados["cobrancas"]) == 1 and dados["cobrancas"][0]["pagamentos"][0]["valor"] == 100.0
    assert len(dados["entradas"]) == 1 and dados["fichas_de_treino"][0]["nome"] == "Ficha da Ana" and len(dados["fichas_de_treino"][0]["treinos"]) == 1
    avaliacao = dados["avaliacoes_fisicas"][0]
    assert (avaliacao["peso_kg"], avaliacao["altura_cm"], avaliacao["imc"], avaliacao["restricoes"]) == (68.4, 167.0, 24.5, "dor no joelho")
    assert dados["avaliacoes_marcadas"][0]["hora"] == "10:00" and dados["origem"] == "Vale Tec · Academia de Diana"
    assert "senha" not in resposta.get_data(as_text=True).lower()                 # nada da equipe vai junto

    vazio = json.loads(como(app, academia["dono"]).get(f"/alunos/{academia['bia']}/dados").get_data(as_text=True))
    assert vazio["cobrancas"] == [] and vazio["avaliacoes_fisicas"] == [] and vazio["cadastro"]["nome"] == "Bia Lima"


def test_so_o_dono_exporta_e_so_da_propria_academia(app, academia):
    for papel in ("recepcao", "instrutor"):
        assert como(app, academia[papel]).get(f"/alunos/{academia['ana']}/dados").status_code == 403
    outro = como(app, criar_usuario("outro@teste.local", nome="Otto"))
    assert outro.get(f"/alunos/{academia['ana']}/dados").status_code == 404
    assert "/login" in app.test_client().get(f"/alunos/{academia['ana']}/dados").headers["Location"]
    perfil_do_dono = como(app, academia["dono"]).get(f"/alunos/{academia['ana']}").get_data(as_text=True)
    perfil_da_recepcao = como(app, academia["recepcao"]).get(f"/alunos/{academia['ana']}").get_data(as_text=True)
    assert "Baixar os dados deste aluno (LGPD)" in perfil_do_dono and "Baixar os dados deste aluno" not in perfil_da_recepcao


# ------------------------------------------------------------------ apagar
def test_excluir_aluno_com_historico_apaga_os_dados_e_mantem_o_financeiro(app, academia):
    dono = como(app, academia["dono"])
    with app.app_context():
        from app.extensions.database import db
        Pagamento.query.one().observacao = "pago pela mãe, Maria"
        db.session.add(MensagemEnviada(conta_id=academia["conta"], aluno_id=academia["ana"], tipo="aniversario", referencia=str(academia["ana"]),
                                       data=HOJE, enviada_por_id=academia["dono"]))
        db.session.commit()
    faturamento_antes = re.search(r"R\$\s?[\d.,]+", dono.get("/relatorios/admin").get_data(as_text=True)).group(0)

    resposta = dono.post(f"/alunos/{academia['ana']}/excluir")

    assert resposta.headers["Location"] == "/alunos"
    with app.app_context():
        ana = Aluno.query.get(academia["ana"])
        assert (ana.nome, ana.email, ana.telefone, ana.cpf, ana.data_nascimento, ana.observacoes, ana.ativo, ana.aceita_whatsapp) == (
            "Aluno removido", None, None, None, None, None, False, False) and ana.anonimizado_em is not None
    for modelo in (AvaliacaoFisica, AvaliacaoAgendada, Frequencia, MensagemEnviada, Ficha, Treino):
        assert contar(modelo) == 0, modelo.__name__                               # saúde, treino, presença e mensagens: apagados
    assert contar(Cobranca) == 1 and contar(Pagamento) == 1                       # o financeiro fica
    with app.app_context():
        assert Pagamento.query.one().observacao is None                           # ... sem o texto livre, que tinha nome de pessoa

    # some de todas as telas de alunos; o endereço do perfil passa a não existir
    for url in ("/alunos", "/alunos/buscar?q=ana", "/", "/mensagens", "/avaliacoes/agendar"):
        html = dono.get(url).get_data(as_text=True)
        assert "Ana Souza" not in html and "Aluno removido" not in html, url
    for url in (f"/alunos/{academia['ana']}", f"/alunos/{academia['ana']}/dados", f"/alunos/{academia['ana']}/ficha", f"/alunos/{academia['ana']}/renovar"):
        assert dono.get(url).status_code == 404, url
    assert dono.post(f"/alunos/{academia['ana']}/excluir").status_code == 404     # não há segunda vez
    # o dinheiro do mês não muda por causa do pedido de exclusão
    assert re.search(r"R\$\s?[\d.,]+", dono.get("/relatorios/admin").get_data(as_text=True)).group(0) == faturamento_antes
    assert campo(Aluno, academia["bia"], "nome") == "Bia Lima"                    # e ninguém mais é afetado


def test_excluir_aluno_sem_historico_apaga_a_linha_inteira(app, academia):
    assert como(app, academia["dono"]).post(f"/alunos/{academia['bia']}/excluir").headers["Location"] == "/alunos"
    assert contar(Aluno, id=academia["bia"]) == 0


def test_so_o_dono_apaga_e_outra_academia_nao_alcanca(app, academia):
    for papel in ("recepcao", "instrutor"):
        assert como(app, academia[papel]).post(f"/alunos/{academia['ana']}/excluir").status_code == 403
    assert como(app, criar_usuario("outro@teste.local", nome="Otto")).post(f"/alunos/{academia['ana']}/excluir").status_code == 404
    assert como(app, academia["dono"]).get(f"/alunos/{academia['ana']}/excluir").status_code == 405       # só por POST
    assert campo(Aluno, academia["ana"], "nome") == "Ana Souza" and contar(AvaliacaoFisica) == 1


def test_cpf_e_email_de_quem_foi_apagado_ficam_livres_para_um_novo_cadastro(app, academia):
    dono = como(app, academia["dono"])
    dono.post(f"/alunos/{academia['ana']}/excluir")
    resposta = dono.post("/alunos/novo", data=_cadastro(academia, nome="Ana Souza", cpf="111.222.333-96", email="ana@exemplo.com"))
    assert resposta.status_code == 302 and contar(Aluno, nome="Ana Souza") == 1


# ------------------------------------------------------------------ registros internos
def test_o_codigo_nao_imprime_nem_registra_dado_pessoal():
    """Logs sem CPF, telefone, e-mail nem senha: o app não usa print(), e nenhuma linha de log cita esses campos."""
    raiz = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
    problemas = []
    for pasta, _, arquivos in os.walk(raiz):
        for nome in arquivos:
            if not nome.endswith(".py"):
                continue
            for numero, linha in enumerate(open(os.path.join(pasta, nome), encoding="utf-8"), 1):
                codigo = linha.split("#")[0]
                if re.search(r"(^|[^\w.])print\(", codigo):
                    problemas.append(f"{nome}:{numero} usa print()")
                if re.search(r"\b(logger|logging|log)\.\w+\(", codigo) and re.search(r"cpf|telefone|senha|\.email|token", codigo, re.IGNORECASE):
                    problemas.append(f"{nome}:{numero} registra dado pessoal: {codigo.strip()[:80]}")
    assert problemas == []
