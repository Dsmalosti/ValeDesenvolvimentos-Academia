"""
Teste de CRIAR CONTA, CONVITE DA EQUIPE e TROCA DE SENHA num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro): o dono cria a conta,
convida um instrutor, copia o link; o convidado abre o link em outro navegador, cria a senha e
entra; o link não vale duas vezes; o dono troca o papel e remove a pessoa; e a troca de senha
pelo link de "esqueci a senha". Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/equipe_navegador.py [pasta-das-fotos]
"""
import os
import sys
import tempfile
import threading

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
from app.services import acesso_service  # noqa: E402
from tests.navegador._base import CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, sem_none_nem_rolagem  # noqa: E402

SENHA, SENHA_NOVA = "uma frase comprida 2026", "outra frase comprida 2027"
resultados = []


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


app = create_app()
assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
with app.app_context():
    db.create_all()
srv = make_server("127.0.0.1", 5100, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5100"

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        cenario = "celular" if celular else "desktop"
        email_dono, email_novo = f"marina-{cenario}@exemplo.com", f"paulo-{cenario}@exemplo.com"
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)

        def acionar(seletor, pagina=None):
            pagina = pagina or pg
            pagina.locator(seletor).first.scroll_into_view_if_needed()
            (pagina.tap if celular else pagina.click)(seletor)

        def enviar(seletor, pagina=None):
            """Aciona um botão que envia formulário e espera a página nova terminar de carregar."""
            pagina = pagina or pg
            with pagina.expect_navigation(wait_until="load", timeout=10000):
                acionar(seletor, pagina)

        # --- o dono cria a conta ---
        pg.goto(BASE + "/login")
        try:                                                  # o popup "Como você vai entrar?" abre sozinho: fecha
            pg.wait_for_selector("#dlg-perfil[open]", timeout=3000)
            acionar('#dlg-perfil [data-valor="recepcao"]')
            pg.wait_for_timeout(400)
        except Exception:
            pass
        enviar("a:has-text('Criar conta')")
        checa(f"[{nome}] o link 'Criar conta' do login abre a tela", pg.url.endswith("/criar-conta") and "Criar sua conta" in pg.inner_text("body"))
        acionar("button[type=submit]")
        pg.wait_for_timeout(400)
        checa(f"[{nome}] enviar vazio: o navegador segura", pg.url.endswith("/criar-conta") and pg.locator(".is-invalid").count() >= 1)
        pg.fill("#f-nome", "Marina Albuquerque")
        pg.fill("#f-email", email_dono)
        pg.fill("#f-senha", SENHA)
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-criar-conta.png"), full_page=True)
        enviar("button[type=submit]")
        pg.wait_for_selector(".m-only .kpi" if celular else ".d-only .kpi")
        checa(f"[{nome}] conta criada: já entra no painel, vazio e sem 'None'", pg.url == BASE + "/" and sem_none_nem_rolagem(pg) and "Marina" in pg.inner_text("body"))

        # --- convida um instrutor e copia o link ---
        pg.goto(BASE + "/configuracoes?aba=equipe")
        acionar("button[data-open='dlg-convidar']")
        pg.wait_for_selector("#dlg-convidar[open]", timeout=3000)
        pg.fill("#dlg-convidar [name=email]", email_novo)
        pg.select_option("#dlg-convidar [name=papel]", "instrutor")
        enviar("#dlg-convidar button[type=submit]")
        lista = pg.inner_text(".eq-list")
        link = pg.get_attribute(".eq-list [data-copiar]", "data-copiar")
        checa(f"[{nome}] convite aparece na lista, com o botão de copiar o link", "Convite enviado · esperando criar a senha" in lista and bool(link) and "/convite/" in link, lista)
        pg.wait_for_timeout(500)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-equipe.png"), full_page=True)

        # --- o convidado abre o link em OUTRO navegador ---
        ctx2, pg2, erros2, falhas2 = abrir_pagina(nav, opts, tema)
        pg2.goto(link)
        tela = pg2.inner_text("body")
        checa(f"[{nome}] o convidado vê a academia, o papel e o e-mail travado", "Academia de Marina" in tela and "Instrutor" in tela and email_novo in tela
              and pg2.locator("input[name=email]").count() == 0)
        pg2.fill("#f-nome", "Paulo Reis")
        pg2.fill("#f-senha", SENHA)
        pg2.wait_for_timeout(300)
        pg2.screenshot(path=os.path.join(FOTOS, f"{nome}-3-convite.png"), full_page=True)
        enviar("button[type=submit]", pg2)
        checa(f"[{nome}] o convidado cria a senha e entra (instrutor ainda não tem painel próprio)", pg2.url == BASE + "/" and "Em construção" in pg2.inner_text("body"))
        ctx3, pg3, _, falhas3 = abrir_pagina(nav, opts, tema)
        resposta = pg3.goto(link)
        checa(f"[{nome}] o mesmo link não vale duas vezes", resposta.status == 404 and "Este convite não vale mais" in pg3.inner_text("body"))
        ctx3.close()
        ctx2.close()

        # --- o dono troca o papel e depois remove a pessoa ---
        pg.goto(BASE + "/configuracoes?aba=equipe")
        checa(f"[{nome}] a pessoa passa a aparecer na equipe, como Instrutor", "Paulo Reis" in pg.inner_text(".eq-list") and "Instrutor" in pg.inner_text(".eq-list li:has-text('Paulo Reis')"))
        acionar(".eq-list li:has-text('Paulo Reis') button[data-open^='dlg-membro-']")
        pg.wait_for_selector("dialog[open] [name=papel]", timeout=3000)
        pg.select_option("dialog[open] [name=papel]", "recepcao")
        enviar("dialog[open] button[value='papel']")
        checa(f"[{nome}] trocar o papel", "Recepção" in pg.inner_text(".eq-list li:has-text('Paulo Reis')"))
        acionar(".eq-list li:has-text('Paulo Reis') button[data-open^='dlg-membro-']")
        pg.wait_for_selector("dialog[open] [name=papel]", timeout=3000)
        enviar("dialog[open] button[value='remover']")
        checa(f"[{nome}] remover da equipe tira a pessoa da lista", "Paulo Reis" not in pg.inner_text(".eq-list"))
        ctx4, pg4, _, _ = abrir_pagina(nav, opts, tema)
        entrou = True
        try:
            entrar(pg4, BASE, email_novo, SENHA, celular)
        except Exception:
            entrou = False
        checa(f"[{nome}] quem foi removido não consegue mais entrar", not entrou and "/login" in pg4.url)
        ctx4.close()

        # --- esqueci a senha ---
        ctx5, pg5, erros5, falhas5 = abrir_pagina(nav, opts, tema)
        pg5.goto(BASE + "/esqueci-senha")
        pg5.fill("#f-email", email_dono)
        with pg5.expect_navigation(wait_until="load", timeout=10000):
            (pg5.tap if celular else pg5.click)("button[type=submit]")
        checa(f"[{nome}] pedir o link: sem e-mail configurado a tela não diz que enviou", "Pedido registrado" in pg5.inner_text("body") and "Link enviado" not in pg5.inner_text("body"))
        with app.test_request_context(base_url=BASE):      # o link que iria por e-mail (ou que o suporte gera pelo comando)
            link_senha = acesso_service.pedir_troca_de_senha(email_dono, enviar=False)
        pg5.goto(link_senha)
        pg5.fill("#f-senha", SENHA_NOVA)
        pg5.wait_for_timeout(300)
        pg5.screenshot(path=os.path.join(FOTOS, f"{nome}-4-senha-nova.png"), full_page=True)
        with pg5.expect_navigation(wait_until="load", timeout=10000):
            (pg5.tap if celular else pg5.click)("button[type=submit]")
        checa(f"[{nome}] trocar a senha leva ao login", pg5.url.endswith("/login"))
        entrar(pg5, BASE, email_dono, SENHA_NOVA, celular)
        checa(f"[{nome}] entra com a senha nova", pg5.url == BASE + "/")
        resposta = pg5.goto(link_senha)
        checa(f"[{nome}] o link de senha também não vale duas vezes", resposta.status == 404 and "Este link não vale mais" in pg5.inner_text("body"))
        ctx5.close()

        # os 404 de propósito (links já usados) não contam como arquivo faltando
        de_proposito = ("/convite/", "/nova-senha/")
        conferir_console_e_rede(checa, nome, [e for e in erros + erros2 + erros5 if "404" not in e],
                                [f for f in falhas_rede + falhas2 + falhas5 if not any(t in f for t in de_proposito)])
        ctx.close()
    nav.close()

srv.shutdown()
ok = sum(1 for r in resultados if r[1])
print(f"\n{ok}/{len(resultados)} passaram")
print("fotos em:", FOTOS)
for n, passou, d in resultados:
    if not passou:
        print(" -", n, "|", d)
