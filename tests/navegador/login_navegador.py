"""
Teste da tela de login num navegador de verdade (Playwright + Chromium).

Celular de 360 e 390 px com TOQUE de verdade, desktop de 1440 px, tema claro e escuro, e o
uso só pelo teclado. Sobe o app do repositório com SQLite descartável e dois usuários de
teste; nunca toca o banco do .env.

Não roda junto com o pytest (o nome do arquivo não começa com "test_"), porque depende do
Playwright, que não está no requirements.txt. Para rodar:

    .venv/Scripts/python.exe -m pip install playwright
    .venv/Scripts/python.exe -m playwright install chromium
    .venv/Scripts/python.exe -B tests/navegador/login_navegador.py

Termina com "N/N passaram". Qualquer "FALHOU" é para investigar antes de dar push.
"""
import os
import sys
import tempfile
import threading

sys.dont_write_bytecode = True  # o repositório versiona .pyc; não gerar novos ao testar
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

# Banco descartável: definido ANTES de importar o app (o load_dotenv não sobrescreve).
_PASTA = tempfile.mkdtemp(prefix="vt-navegador-")
os.environ["DATABASE_URL"] = os.environ["DATABASE_URI"] = "sqlite:///" + os.path.join(_PASTA, "navegador.db").replace("\\", "/")
os.environ["SECRET_KEY"] = "chave-so-de-teste"
os.environ["FLASK_CONFIG"] = "testing"

from playwright.sync_api import sync_playwright  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions.database import db  # noqa: E402
from app.extensions.security import bcrypt  # noqa: E402
from app.models import Conta, User  # noqa: E402

EMAIL_ATIVO, SENHA = "ana@valetec.com", "Senha-de-teste-123"


def montar_app():
    """App do repositório, sem remendo nenhum, com um usuário ativo e um inativo."""
    app = create_app()
    assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
    with app.app_context():
        db.create_all()
        senha = bcrypt.generate_password_hash(SENHA).decode("utf-8")
        conta = Conta(nome="Academia de teste")
        db.session.add(conta)
        db.session.flush()
        db.session.add_all([
            User(nome="Ana", sobrenome="Recepção", email=EMAIL_ATIVO, senha=senha, ativo=True, conta_id=conta.id),
            User(nome="Bruno", sobrenome="Inativo", email="bruno@valetec.com", senha=senha, ativo=False, conta_id=conta.id),
        ])
        db.session.commit()
    return app

resultados = []


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


app = montar_app()
srv = make_server("127.0.0.1", 5091, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5091"

CENARIOS = [
    ("celular-360-claro", dict(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True, device_scale_factor=2), "light"),
    ("celular-390-escuro", dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2), "dark"),
    ("desktop-1440-claro", dict(viewport={"width": 1440, "height": 900}), "light"),
    ("desktop-1440-escuro", dict(viewport={"width": 1440, "height": 900}), "dark"),
]

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        toque = opts.get("has_touch", False)
        ctx = nav.new_context(color_scheme=tema, **opts)
        pg = ctx.new_page()
        acionar = pg.tap if toque else pg.click   # no celular, toque de verdade (touchstart/touchend)
        erros, falhas_rede = [], []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and erros.append(m.text))
        pg.on("response", lambda r: r.status >= 400 and falhas_rede.append(f"{r.status} {r.url}"))

        # chega pedindo uma página protegida, como um usuário de verdade
        pg.goto(BASE + "/planos/listar/")
        pg.wait_for_selector("#dlg-perfil[open]", timeout=4000)
        checa(f"[{nome}] sem login cai na tela nova com o popup de perfil", "/login" in pg.url and pg.is_visible("#dlg-perfil"))
        checa(f"[{nome}] correção do iPhone carregada e a página de trás não rola com popup aberto",
              pg.evaluate("getComputedStyle(document.documentElement).overflow") == "hidden"
              and pg.evaluate("!!document.querySelector('script[src*=\"ajustes-iphone.js\"]')"))
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(300)
        checa(f"[{nome}] popup obrigatório não fecha com Esc antes de escolher", pg.locator("#dlg-perfil[open]").count() == 1,
              "fechou com Esc logo ao abrir (sem nenhum toque antes)")
        if pg.locator("#dlg-perfil[open]").count() == 0:
            pg.reload()
            pg.wait_for_selector("#dlg-perfil[open]", timeout=4000)

        acionar('#dlg-perfil [data-valor="recepcao"]')
        pg.wait_for_timeout(500)
        checa(f"[{nome}] escolher perfil fecha o popup", pg.locator("#dlg-perfil[open]").count() == 0)
        checa(f"[{nome}] chip mostra Recepção e o campo escondido recebe o perfil",
              pg.inner_text("[data-perfil-nome]") == "Recepção" and pg.input_value("#h-perfil") == "recepcao")
        acionar('[data-perfil-chip] [data-open="dlg-perfil"]')
        try:   # espera o popup abrir de verdade; com tempo fixo o teste falhava de vez em quando
            pg.wait_for_selector("#dlg-perfil[open]", timeout=3000)
        except Exception:
            pass
        checa(f'[{nome}] "Trocar" reabre o popup', pg.locator("#dlg-perfil[open]").count() == 1)
        acionar('#dlg-perfil [data-valor="instrutor"]')
        pg.wait_for_timeout(500)
        checa(f"[{nome}] trocar perfil atualiza o chip", pg.inner_text("[data-perfil-nome]") == "Instrutor")

        acionar("button[type=submit]")
        pg.wait_for_timeout(400)
        checa(f"[{nome}] enviar vazio não sai da tela e mostra a mensagem do campo",
              "/login" in pg.url and "Digite seu e-mail ou usuário." in pg.inner_text("form"))

        pg.fill("#f-senha", "abc")
        acionar("[data-toggle-senha]")
        mostrou = pg.get_attribute("#f-senha", "type") == "text"
        acionar("[data-toggle-senha]")
        checa(f"[{nome}] olho mostra e esconde a senha", mostrou and pg.get_attribute("#f-senha", "type") == "password")

        pg.fill("#f-identificador", "Ana@ValeTec.com")
        pg.fill("#f-senha", "senha-errada")
        acionar("button[type=submit]")
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(800)
        checa(f"[{nome}] senha errada: aviso vermelho, e-mail mantido, popup não reabre",
              pg.is_visible(".note--red") and pg.input_value("#f-identificador") == "Ana@ValeTec.com"
              and pg.locator("#dlg-perfil[open]").count() == 0)
        larg = pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        checa(f"[{nome}] sem rolagem lateral", larg[0] <= larg[1], larg)
        alvos = pg.evaluate("""[...document.querySelectorAll('main a, main button')].filter(e => e.offsetParent)
                               .map(e => [e.textContent.trim().slice(0, 20), Math.round(e.getBoundingClientRect().height)])""")
        if toque:
            pequenos = [a for a in alvos if a[1] < 44]
            checa(f"[{nome}] alvos de toque com 44 px ou mais", not pequenos, pequenos)
        checa(f"[{nome}] console sem erro na tela de login", not erros, erros[:3])

        pg.fill("#f-senha", SENHA)
        acionar("button[type=submit]")
        # espera a navegação de verdade: no toque, o envio começa alguns milissegundos depois do
        # dedo sair, e wait_for_load_state voltaria antes de a página mudar
        try:
            pg.wait_for_url(lambda u: "/login" not in u, timeout=6000)
        except Exception:
            pass
        checa(f"[{nome}] login certo volta para a página pedida (/planos/listar/)", pg.url == BASE + "/planos/listar/", pg.url)
        rede = [f for f in falhas_rede if not f.endswith("/favicon.ico")]
        checa(f"[{nome}] nenhum arquivo 404/500", not rede, rede[:5])
        ctx.close()

    # teclado: dá pra entrar sem mouse (acessibilidade)
    ctx = nav.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    pg.goto(BASE + "/login")
    pg.wait_for_selector("#dlg-perfil[open]")
    pg.keyboard.press("Tab")
    checa("[teclado] foco fica preso dentro do popup", pg.evaluate('document.activeElement.closest("#dlg-perfil") !== null'))
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(500)
    pg.fill("#f-identificador", EMAIL_ATIVO)
    pg.fill("#f-senha", SENHA)
    pg.press("#f-senha", "Enter")
    pg.wait_for_load_state("networkidle")
    checa("[teclado] Enter na senha envia e entra", pg.url.rstrip("/") == BASE, pg.url)
    ctx.close()
    nav.close()

srv.shutdown()
ok = sum(1 for r in resultados if r[1])
print(f"\n{ok}/{len(resultados)} passaram")
for n, passou, d in resultados:
    if not passou:
        print(" -", n, "|", d)
