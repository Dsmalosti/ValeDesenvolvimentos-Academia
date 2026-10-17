"""
[back-30-meu-perfil] Teste do MEU PERFIL num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro):
  - o link "Meu perfil" no menu (gaveta no celular, barra lateral no desktop) abre /perfil;
  - trocar o nome: o menu passa a mostrar o nome novo;
  - senha atual errada: a tela mostra o erro no campo certo e não troca;
  - trocar a senha (com o botão de mostrar a senha e o medidor de força): continua logado e entra com a senha nova.
Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/perfil_navegador.py [pasta-das-fotos]
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
from app.extensions.security import bcrypt  # noqa: E402
from app.models import Conta, User  # noqa: E402
from tests.navegador._base import CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, sem_none_nem_rolagem  # noqa: E402

SENHA, SENHA_NOVA = "Senha-de-teste-123", "uma frase nova e comprida"
resultados = []


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


app = create_app()
assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
with app.app_context():
    db.create_all()
    for nome, _, _ in CENARIOS:
        conta = Conta(nome="Academia Perfil")
        db.session.add(conta)
        db.session.flush()
        db.session.add(User(nome="Carla", sobrenome="Dona", email=f"carla-{nome}@valetec.com", ativo=True, conta_id=conta.id,
                            senha=bcrypt.generate_password_hash(SENHA).decode("utf-8")))
    db.session.commit()
srv = make_server("127.0.0.1", 5110, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5110"

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        email = f"carla-{nome}@valetec.com"
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)

        def acionar(seletor):
            pg.locator(seletor).first.scroll_into_view_if_needed()
            (pg.tap if celular else pg.click)(seletor)

        def enviar(seletor):
            with pg.expect_navigation(wait_until="load", timeout=10000):
                acionar(seletor)

        entrar(pg, BASE, email, SENHA, celular)

        # ------------------------------------------------------------ o caminho pelo menu
        if celular:
            acionar("button[data-open='gaveta']")
            pg.wait_for_selector("#gaveta[open]", timeout=3000)
            pg.wait_for_timeout(400)
            link = "#gaveta a[href='/perfil']"
        else:
            link = ".rail a[href='/perfil']"
        checa(f"[{nome}] o menu tem o link Meu perfil", pg.locator(link).count() == 1)
        with pg.expect_navigation(wait_until="load", timeout=10000):
            (pg.tap if celular else pg.click)(link)
        checa(f"[{nome}] o link abre /perfil", pg.url == BASE + "/perfil", pg.url)
        checa(f"[{nome}] os campos vêm preenchidos", pg.input_value("#f-nome") == "Carla" and pg.input_value("#f-email") == email)
        checa(f"[{nome}] perfil: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        botoes = [b.bounding_box() for b in pg.locator("#conteudo button[type=submit]").all()]
        checa(f"[{nome}] os botões têm tamanho de toque", all(b and b["height"] >= 44 for b in botoes), botoes)
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-perfil.png"), full_page=True)

        # ------------------------------------------------------------ trocar o nome
        pg.fill("#f-nome", "Carla Maria")
        pg.fill("#f-sobrenome", "Souza")
        enviar("form[action='/perfil/dados'] button[type=submit]")
        pg.wait_for_selector("text=Dados salvos", timeout=4000)
        checa(f"[{nome}] trocar o nome salva e o perfil mostra o nome novo", "Carla Maria Souza" in pg.inner_text("#conteudo"))

        # ------------------------------------------------------------ senha atual errada
        pg.fill("#f-senha-atual", "não é a senha")
        pg.fill("#f-senha-nova", SENHA_NOVA)
        enviar("form[action='/perfil/senha'] button[type=submit]")
        erro = pg.locator("#f-senha-atual-erro")
        checa(f"[{nome}] senha atual errada: o erro aparece no campo certo", erro.count() == 1 and "não confere" in erro.inner_text()
              and pg.locator("#f-dados-senha-erro").count() == 0)
        pg.locator("#senha").scroll_into_view_if_needed()
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-senha-errada.png"))

        # ------------------------------------------------------------ trocar a senha
        pg.fill("#f-senha-atual", SENHA)
        acionar("[data-toggle-senha='f-senha-nova']")
        checa(f"[{nome}] o botão do olho mostra a senha", pg.get_attribute("#f-senha-nova", "type") == "text")
        pg.fill("#f-senha-nova", "")
        pg.type("#f-senha-nova", SENHA_NOVA)
        checa(f"[{nome}] o medidor de força reage", pg.inner_text("[data-forca-txt]") != "Pelo menos 8 caracteres. Uma frase curta é mais forte que uma senha difícil.",
              pg.inner_text("[data-forca-txt]"))
        enviar("form[action='/perfil/senha'] button[type=submit]")
        pg.wait_for_selector("text=Senha trocada", timeout=4000)
        checa(f"[{nome}] trocar a senha mantém este aparelho logado", pg.url == BASE + "/perfil")
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-senha-trocada.png"))
        # o 400 da senha errada é de propósito: não conta como erro
        conferir_console_e_rede(checa, nome, [e for e in erros if "400 (BAD REQUEST)" not in e], [f for f in falhas_rede if not f.startswith("400 ")])
        ctx.close()

        # ------------------------------------------------------------ entrar de novo com a senha nova
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)
        entrar(pg, BASE, email, SENHA_NOVA, celular)
        checa(f"[{nome}] entra com a senha nova", pg.url == BASE + "/")
        ctx.close()
    nav.close()

srv.shutdown()
ok = sum(1 for r in resultados if r[1])
print(f"\n{ok}/{len(resultados)} passaram")
print("fotos em:", FOTOS)
for n, passou, d in resultados:
    if not passou:
        print(" -", n, "|", d)
