"""
Teste da COBRANÇA do front novo num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro): tela de receber com
PIX manual, trocar a forma de pagamento, confirmar, perfil em dia, renovar (trocando de plano e
sem cobrar), extrato e, no desktop, diária avulsa pelo painel. Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/cobranca_navegador.py [pasta-das-fotos]
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
from app.models import Aluno, Cobranca, Conta, Plano, User  # noqa: E402
from tests.navegador._base import pagamento_recebido  # noqa: E402

EMAIL, SENHA = "marina@valetec.com", "Senha-de-teste-123"
HOJE = date.today()
DMY = "%d/%m/%Y"
resultados = []
ids = {}


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """Uma academia com dois planos e, para cada cenário, uma aluna recém-matriculada (cobrança em aberto) e um aluno vencido."""
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
        mensal = Plano(nome="Mensal", valor=149.90, duracao_dias=30, descricao="", ativo=True, instrutor_id=dona.id, conta_id=conta.id)
        anual = Plano(nome="Anual", valor=1290, duracao_dias=365, descricao="", ativo=True, instrutor_id=dona.id, conta_id=conta.id)
        db.session.add_all([mensal, anual])
        db.session.flush()
        for i, cenario in enumerate(("celular", "desktop")):
            nova = Aluno(nome=f"Camila Nova {cenario.title()}", email=f"nova{i}@exemplo.com", cpf=f"111.222.333-0{i}", telefone="(12) 98211-4400",
                         ativo=True, data_inicio=HOJE, forma_pagamento="pix", plano_id=mensal.id, instrutor_id=dona.id, conta_id=conta.id)
            vencido = Aluno(nome=f"Eduardo Vencido {cenario.title()}", email=f"venc{i}@exemplo.com", cpf=f"111.222.444-0{i}", telefone="(12) 98211-4401",
                            ativo=True, forma_pagamento="debito", plano_id=mensal.id, instrutor_id=dona.id, conta_id=conta.id)
            db.session.add_all([nova, vencido])
            db.session.flush()
            aberta = Cobranca(conta_id=conta.id, aluno_id=nova.id, plano_id=mensal.id, tipo="matricula", valor=149.90, data_inicio=HOJE,
                              data_vencimento=HOJE + timedelta(days=30), status="pendente", instrutor_id=dona.id)
            db.session.add(aberta)
            pagamento_recebido(db, vencido, dona, 149.90, HOJE - timedelta(days=40), HOJE - timedelta(days=10))
            db.session.flush()
            ids[cenario] = {"nova": nova.id, "vencido": vencido.id, "cobranca": aberta.id}
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5096, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5096"

CENARIOS = [
    ("celular-390-claro", dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2), "light"),
    ("desktop-1440-escuro", dict(viewport={"width": 1440, "height": 900}), "dark"),
]

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        meu = ids["celular" if celular else "desktop"]
        ctx = nav.new_context(color_scheme=tema, **opts)
        pg = ctx.new_page()
        erros, falhas_rede = [], []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and erros.append(m.text))
        pg.on("response", lambda r: r.status >= 400 and falhas_rede.append(f"{r.status} {r.url}"))

        def acionar(seletor):
            """Toca (celular) ou clica (desktop), rolando até o elemento antes."""
            pg.locator(seletor).first.scroll_into_view_if_needed()
            (pg.tap if celular else pg.click)(seletor)

        visivel = lambda seletor: pg.locator(seletor).first.is_visible()

        def fechar_popup_de_sucesso():
            """Depois de confirmar, abre sozinho o popup "Pagamento confirmado!". Confere e fecha, para ver a tela atrás."""
            pg.wait_for_selector("#pop-pagamento-ok[open]", timeout=4000)
            ok = "Pagamento confirmado!" in pg.inner_text("#pop-pagamento-ok")
            (pg.tap if celular else pg.click)("#pop-pagamento-ok [data-close]")
            pg.wait_for_timeout(500)
            return ok

        # --- entra e fecha o popup de avisos do painel ---
        pg.goto(BASE + "/")
        pg.wait_for_selector("#dlg-perfil[open]", timeout=5000)
        acionar('#dlg-perfil [data-valor="recepcao"]')
        pg.wait_for_timeout(400)
        pg.fill("#f-identificador", EMAIL)
        pg.fill("#f-senha", SENHA)
        acionar("button[type=submit]")
        pg.wait_for_url(BASE + "/", timeout=8000)
        try:
            pg.wait_for_selector("#pop-avisos[open]", timeout=3500)
            acionar("#pop-avisos [data-close]")
            pg.wait_for_timeout(400)
        except Exception:
            pass

        # --- tela de receber: a cobrança em aberto da aluna nova ---
        pg.goto(BASE + f"/cobrancas/matricula/{meu['nova']}")
        pg.wait_for_url("**/cobrancas/*/receber*", timeout=6000)
        texto = pg.inner_text("body")
        checa(f"[{nome}] abre a tela de receber com o nome, o plano e o valor", "Camila Nova" in texto and "Mensal" in texto and "R$ 149,90" in texto)
        checa(f"[{nome}] PIX vem escolhido e habilitado, com 'Você confirma' (sem QR Code)",
              pg.get_attribute(".formas .opcao[data-valor='pix']", "aria-pressed") == "true"
              and pg.get_attribute(".formas .opcao[data-valor='pix']", "disabled") is None
              and "Você confirma" in pg.inner_text(".formas .opcao[data-valor='pix']") and visivel("button:has-text('Já recebi o PIX')")
              and "Não configurado" not in texto and "Gerar cobrança PIX" not in texto)
        checa(f"[{nome}] sem 'None' e sem rolagem lateral", "None" not in texto
              and pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        pg.wait_for_timeout(700)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-receber.png"), full_page=True)

        # --- trocar a forma mostra só o que é daquela forma ---
        acionar(".formas .opcao[data-valor='dinheiro']")
        pg.wait_for_timeout(300)
        checa(f"[{nome}] escolher Dinheiro troca o botão e esconde o do PIX",
              visivel("button:has-text('Já recebi em dinheiro')") and not visivel("button:has-text('Já recebi o PIX')"))
        acionar(".formas .opcao[data-valor='pix']")
        pg.wait_for_timeout(300)

        # --- confirmar o PIX ---
        acionar("button:has-text('Já recebi o PIX')")
        pg.wait_for_url("**/receber?ok=1", timeout=8000)
        checa(f"[{nome}] abre o popup 'Pagamento confirmado!' e ele fecha", fechar_popup_de_sucesso())
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] a tela mostra 'Pagamento confirmado' e QUEM confirmou", "Pagamento confirmado" in texto
              and "Confirmado manualmente por Marina" in texto and "PIX" in texto
              and (HOJE + timedelta(days=30)).strftime(DMY) in texto)
        pg.wait_for_timeout(700)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-confirmado.png"), full_page=True)
        acionar("a:has-text('Ver o perfil do aluno')")
        pg.wait_for_url(f"**/alunos/{meu['nova']}", timeout=6000)
        perfil = pg.inner_text("#conteudo")
        checa(f"[{nome}] o perfil passa a mostrar a aluna em dia, com o pagamento no histórico", "Em dia" in perfil and "R$ 149,90" in perfil and "None" not in perfil)

        # --- renovar o aluno vencido, trocando de plano ---
        pg.goto(BASE + f"/alunos/{meu['vencido']}")
        checa(f"[{nome}] aluno vencido aparece como pendente no perfil", "Pendente" in pg.inner_text("#conteudo") or "Atrasad" in pg.inner_text("#conteudo"))
        acionar("a:has-text('Renovar') >> visible=true")
        pg.wait_for_url("**/renovar", timeout=6000)
        acionar(".opcao:has-text('Anual')")
        pg.wait_for_timeout(300)
        como_fica = pg.inner_text("#conteudo")
        checa(f"[{nome}] escolher o Anual atualiza o valor e o novo vencimento na tela",
              "R$ 1.290,00" in pg.inner_text("[data-e='valor']") and (HOJE + timedelta(days=365)).strftime(DMY) in pg.inner_text("[data-e='novo']"), como_fica[-200:])
        pg.wait_for_timeout(500)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-renovar.png"), full_page=True)
        acionar("button:has-text('Renovar e receber')")
        pg.wait_for_url("**/cobrancas/*/receber*", timeout=8000)
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] 'Renovar e receber' abre a cobrança do plano novo, com a forma preferida do aluno (débito)",
              "Anual" in texto and "R$ 1.290,00" in texto and pg.get_attribute(".formas .opcao[data-valor='debito']", "aria-pressed") == "true")
        acionar("button:has-text('Confirmar recebimento')")
        pg.wait_for_url("**/receber?ok=1", timeout=8000)
        fechar_popup_de_sucesso()
        checa(f"[{nome}] renovação confirmada no débito", "Pagamento confirmado" in pg.inner_text("#conteudo") and "Débito" in pg.inner_text("#conteudo"))

        # --- extrato do aluno ---
        pg.goto(BASE + f"/alunos/{meu['vencido']}/pagamentos")
        extrato = pg.inner_text("#conteudo")
        checa(f"[{nome}] extrato mostra os dois pagamentos, com a forma e quem confirmou",
              "R$ 1.290,00" in extrato and "R$ 149,90" in extrato and "Débito" in extrato and "Marina confirmou" in extrato and "None" not in extrato)
        pg.wait_for_timeout(500)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-4-extrato.png"), full_page=True)

        # --- renovar sem cobrar: a cobrança fica em aberto e a tela de receber continua acessível ---
        pg.goto(BASE + f"/alunos/{meu['nova']}/renovar")
        acionar("button:has-text('Renovar sem cobrar agora')")
        pg.wait_for_url(f"**/alunos/{meu['nova']}", timeout=8000)
        pg.goto(BASE + f"/cobrancas/matricula/{meu['nova']}")
        pg.wait_for_url("**/cobrancas/*/receber*", timeout=6000)
        checa(f"[{nome}] renovar sem cobrar deixa uma cobrança em aberto para receber depois", "Renovação" in pg.inner_text("body") and "Camila Nova" in pg.inner_text("body"))
        acionar("a:has-text('Cobrar depois')")
        pg.wait_for_url(f"**/alunos/{meu['nova']}", timeout=8000)

        # --- diária avulsa (o atalho do painel só existe no desktop) ---
        if not celular:
            pg.goto(BASE + "/")
            pg.wait_for_selector("[data-open='receber-diaria']")
            pg.click("[data-open='receber-diaria']")
            pg.wait_for_selector("#receber-diaria[open]", timeout=3000)
            pg.fill("#receber-diaria #f-nome_visitante", "João Visitante")
            pg.click("#receber-diaria .opcao[data-valor='dinheiro']")
            pg.click("#receber-diaria button[type=submit]")
            pg.wait_for_url("**/cobrancas/*/receber*", timeout=8000)
            texto = pg.inner_text("#conteudo")
            checa(f"[{nome}] diária avulsa abre a mesma tela de receber, sem aluno", "Receber de João Visitante" in texto and "Diária avulsa" in texto
                  and "R$ 25,00" in texto and pg.get_attribute(".formas .opcao[data-valor='dinheiro']", "aria-pressed") == "true")
            pg.click("button:has-text('Já recebi em dinheiro')")
            pg.wait_for_url("**/receber?ok=1", timeout=8000)
            fechar_popup_de_sucesso()
            checa(f"[{nome}] diária confirmada", "Pagamento confirmado" in pg.inner_text("#conteudo") and "None" not in pg.inner_text("#conteudo"))
            pg.goto(BASE + "/")
            pg.wait_for_timeout(800)
            checa(f"[{nome}] o painel mostra as diárias numa linha 'Avulsos' do faturamento", "Avulsos" in pg.inner_text("#conteudo"))

        esperadas = [f for f in falhas_rede if not f.endswith("/favicon.ico")]
        checa(f"[{nome}] nenhum arquivo 404/500", not esperadas, esperadas[:5])
        de_verdade = [e for e in erros if "Transition was aborted" not in e and "Transition was skipped" not in e]
        checa(f"[{nome}] console sem erro", not de_verdade, de_verdade[:3])
        ctx.close()
    nav.close()

srv.shutdown()
ok = sum(1 for r in resultados if r[1])
print(f"\n{ok}/{len(resultados)} passaram")
print("fotos em:", FOTOS)
for n, passou, d in resultados:
    if not passou:
        print(" -", n, "|", d)
