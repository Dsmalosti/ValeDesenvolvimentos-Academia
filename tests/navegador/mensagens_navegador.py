"""
Teste da central de MENSAGENS do front novo num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro): a fila do dia, o filtro
por motivo, o toque em "Enviar no WhatsApp" (abre o wa.me com o texto e a linha vira "Enviada
hoje"), os botões de WhatsApp do perfil e do painel que eram demonstração e a cobrança em lote do
painel. Salva fotos.

O teste NÃO sai para a internet: o endereço wa.me é interceptado e respondido aqui mesmo.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/mensagens_navegador.py [pasta-das-fotos]
"""
import os
import sys
import tempfile
import threading
from datetime import date, timedelta

sys.dont_write_bytecode = True  # não gerar .pyc ao testar
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

_PASTA = tempfile.mkdtemp(prefix="vt-navegador-")
os.environ["DATABASE_URL"] = os.environ["DATABASE_URI"] = "sqlite:///" + os.path.join(_PASTA, "navegador.db").replace("\\", "/")
os.environ["SECRET_KEY"] = "chave-so-de-teste"
os.environ["FLASK_CONFIG"] = "testing"
FOTOS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_PASTA, "fotos")
os.makedirs(FOTOS, exist_ok=True)

from playwright.sync_api import sync_playwright  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions.database import db  # noqa: E402
from app.extensions.security import bcrypt  # noqa: E402
from app.models import Aluno, AvaliacaoAgendada, Conta, Plano, User  # noqa: E402
from tests.navegador._base import (CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, pagamento_recebido,  # noqa: E402
                                   sem_none_nem_rolagem)

EMAIL, SENHA = "marina@valetec.com", "Senha-de-teste-123"
HOJE = date.today()
NASCEU_HOJE = date(1992 if (HOJE.day, HOJE.month) == (29, 2) else 1990, HOJE.month, HOJE.day)
OUTRO_DIA = date(1990, 6, 15) if (HOJE.day, HOJE.month) != (15, 6) else date(1990, 7, 15)
resultados = []
ids = {}


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """Duas aniversariantes (uma por cenário), Bia com avaliação amanhã, Caio com a mensalidade vencida e Duda sem nada."""
    app = create_app()
    assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
    with app.app_context():
        db.create_all()
        conta = Conta(nome="Academia Corpo em Movimento")
        db.session.add(conta)
        db.session.flush()
        dona = User(nome="Marina", sobrenome="Albuquerque", email=EMAIL, ativo=True, conta_id=conta.id,
                    senha=bcrypt.generate_password_hash(SENHA).decode("utf-8"))
        db.session.add(dona)
        db.session.flush()
        plano = Plano(nome="Mensal", valor=149.90, duracao_dias=30, descricao="", ativo=True, instrutor_id=dona.id, conta_id=conta.id)
        db.session.add(plano)
        db.session.flush()
        for i, (nome, nascimento) in enumerate([("Ana Celular", NASCEU_HOJE), ("Ana Desktop", NASCEU_HOJE), ("Bia Lima", OUTRO_DIA),
                                                 ("Caio Dias", OUTRO_DIA), ("Duda Reis", OUTRO_DIA)]):
            aluno = Aluno(nome=nome, email=f"aluno{i}@exemplo.com", cpf=f"111.222.333-0{i}", telefone="(12) 98211-4400", ativo=True,
                          data_nascimento=nascimento, plano_id=plano.id, instrutor_id=dona.id, conta_id=conta.id)
            db.session.add(aluno)
            db.session.flush()
            ids[nome] = aluno.id
            if nome == "Caio Dias":
                pagamento_recebido(db, aluno, dona, 149.90, HOJE - timedelta(days=40), HOJE - timedelta(days=10))    # venceu há 10 dias
            else:
                pagamento_recebido(db, aluno, dona, 149.90, HOJE - timedelta(days=5), HOJE + timedelta(days=25))     # em dia
        db.session.add(AvaliacaoAgendada(conta_id=conta.id, aluno_id=ids["Bia Lima"], data=HOJE + timedelta(days=1), hora="10:00", tipo="primeira",
                                         status="confirmada", avaliador_id=dona.id, cobranca="inclusa", criado_por_id=dona.id))
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5103, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5103"

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        ana = "Ana Celular" if celular else "Ana Desktop"
        ja = 0 if celular else 1        # o cenário do desktop roda depois do celular, que já enviou uma
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)
        # nada de internet no teste: o WhatsApp é respondido aqui
        ctx.route("https://wa.me/**", lambda rota: rota.fulfill(status=200, content_type="text/html", body="<title>WhatsApp de teste</title>"))

        def acionar(seletor):
            pg.locator(seletor).first.scroll_into_view_if_needed()
            (pg.tap if celular else pg.click)(seletor)

        def visiveis():
            return pg.locator("#lista-msgs .msg-item >> visible=true").count()

        entrar(pg, BASE, EMAIL, SENHA, celular)

        # ------------------------------------------------------------ chegar pela navegação
        if celular:
            pg.tap("[data-open='gaveta']")
            pg.wait_for_timeout(500)
            with pg.expect_navigation(wait_until="load", timeout=10000):
                pg.tap("#gaveta .dlink:has-text('Mensagens')")
        else:
            with pg.expect_navigation(wait_until="load", timeout=10000):
                pg.click(".rail .navicon[aria-label='Mensagens']")
        topo = pg.inner_text("body").lower()
        checa(f"[{nome}] o menu abre a fila de mensagens do dia", pg.url.endswith("/mensagens") and f"fila de hoje · {4 - ja} para enviar" in topo, topo[:160])
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] a fila tem os quatro: duas aniversariantes, a avaliação de amanhã e a cobrança", visiveis() == 4 and "Duda Reis" not in texto
              and "Parabéns, Ana!" in texto and "Sua avaliação física é amanhã" in texto and "Sua mensalidade de R$ 149,90 venceu em" in texto)
        checa(f"[{nome}] fila: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-fila.png"), full_page=True)

        # ------------------------------------------------------------ filtro por motivo
        acionar("nav.pills .pill[data-filtro='cobranca']")
        pg.wait_for_timeout(300)
        checa(f"[{nome}] o filtro 'Cobranças atrasadas' deixa só a cobrança", visiveis() == 1 and "Caio Dias" in pg.inner_text("#lista-msgs .msg-item >> visible=true"))
        acionar("nav.pills .pill[data-filtro='aniversario']")
        pg.wait_for_timeout(300)
        checa(f"[{nome}] o filtro 'Aniversários' deixa as duas aniversariantes", visiveis() == 2)
        acionar("nav.pills .pill[data-filtro='todos']")
        pg.wait_for_timeout(300)
        checa(f"[{nome}] 'Todas' mostra as quatro de novo", visiveis() == 4)

        # ------------------------------------------------------------ enviar: abre o WhatsApp e a linha vira "Enviada hoje"
        item = f"#lista-msgs .msg-item:has-text('{ana}')"
        checa(f"[{nome}] antes do toque a linha não está marcada", "is-enviada" not in (pg.get_attribute(item, "class") or "")
              and not pg.locator(f"{item} [data-msg-feito]").is_visible())
        with ctx.expect_page() as aba, pg.expect_response("**/mensagens/enviada") as gravou:
            acionar(f"{item} [data-msg-enviar]")
        zap = aba.value
        zap.wait_for_load_state()
        checa(f"[{nome}] o toque abre o WhatsApp da aluna com o parabéns escrito", zap.url.startswith("https://wa.me/5512982114400?text=Parab") and "Ana" in zap.url, zap.url[:90])
        zap.close()
        checa(f"[{nome}] o servidor gravou o envio", gravou.value.status == 200 and gravou.value.json() == {"ok": True})
        checa(f"[{nome}] a linha vira 'Enviada hoje' na hora, com 'Enviar de novo'", "is-enviada" in pg.get_attribute(item, "class")
              and pg.locator(f"{item} [data-msg-feito]").is_visible() and pg.inner_text(f"{item} [data-msg-rotulo]").strip() == "Enviar de novo")
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-enviada.png"), full_page=True)

        pg.reload()
        checa(f"[{nome}] depois de recarregar continua enviada e a contagem desce", "is-enviada" in pg.get_attribute(item, "class")
              and f"fila de hoje · {3 - ja} para enviar" in pg.inner_text("body").lower())

        if not celular:
            with pg.expect_navigation(wait_until="load", timeout=10000):
                pg.click("a:has-text('Editar textos') >> visible=true")
            checa(f"[{nome}] 'Editar textos' leva aos modelos de mensagem das configurações", "/configuracoes" in pg.url and "aba=mensagens" in pg.url)

        # ------------------------------------------------------------ botões de WhatsApp que eram demonstração
        pg.goto(BASE + f"/alunos/{ids['Caio Dias']}")
        checa(f"[{nome}] o botão 'WhatsApp' do perfil abre a conversa do aluno", pg.locator("a.btn-green[href='https://wa.me/5512982114400'] >> visible=true").count() == 1)

        pg.evaluate("sessionStorage.removeItem('vt-popup-pop-avisos')")      # o popup de avisos abre uma vez por sessão: simula uma nova
        pg.goto(BASE + "/")
        pg.wait_for_selector("#pop-avisos[open]", timeout=5000)
        checa(f"[{nome}] no aviso do painel, cada aluno tem o link do WhatsApp", pg.locator("#pop-avisos a.iconbtn[href='https://wa.me/5512982114400']").count() >= 3
              and pg.locator("#pop-avisos [data-toast*='WhatsApp']").count() == 0)
        checa(f"[{nome}] 'Enviar mensagem para todos' leva à fila (antes só mostrava um aviso)", pg.locator("#pop-avisos a.btn-primary[href='/mensagens']").count() == 2)
        acionar("#pop-avisos [data-close] >> visible=true")
        pg.wait_for_timeout(500)

        if not celular:      # a cobrança em lote é um atalho do painel do computador
            pg.click("[data-open='cobrar-whatsapp'] >> visible=true")
            pg.wait_for_selector("#cobrar-whatsapp[open]", timeout=3000)
            pg.wait_for_timeout(300)
            pg.click("#cobrar-whatsapp label.check:has(input[data-marcar-todos])")
            pg.wait_for_timeout(200)
            pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-cobranca-em-lote.png"))
            with pg.expect_navigation(wait_until="load", timeout=10000):
                pg.click("#cobrar-whatsapp button[type=submit]")
            checa(f"[{nome}] a cobrança em lote do painel leva à fila, com a cobrança pronta", pg.url.endswith("/mensagens") and "Caio Dias" in pg.inner_text("#lista-msgs"))

        conferir_console_e_rede(checa, nome, erros, falhas_rede)
        ctx.close()
    nav.close()

srv.shutdown()
ok = sum(1 for r in resultados if r[1])
print(f"\n{ok}/{len(resultados)} passaram")
print("fotos em:", FOTOS)
for n, passou, d in resultados:
    if not passou:
        print(" -", n, "|", d)
