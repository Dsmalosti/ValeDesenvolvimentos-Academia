"""
[back-25-admin] Teste do painel de administração num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro): o admin entra, vê a lista de contas
(sem a página estourar a largura), abre uma conta, entra nela como o dono (aviso azul no topo), vê os alunos do
cliente e volta ao painel. Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/admin_navegador.py [pasta-das-fotos]
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
from app.models import Aluno, Conta, Plano, User  # noqa: E402
from tests.navegador._base import CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, sem_none_nem_rolagem  # noqa: E402

SENHA = "Senha-de-teste-123"
ADMIN, CLIENTE = "adauto@valetec.com", "diana@academia.com"
HOJE = date.today()
resultados = []
ids = {}


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """O admin (com a própria conta) e uma academia cliente com uma aluna."""
    app = create_app()
    assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
    with app.app_context():
        db.create_all()
        for nome, email, admin in (("Vale Tec (interno)", ADMIN, True), ("Academia Corpo em Movimento", CLIENTE, False)):
            conta = Conta(nome=nome)
            db.session.add(conta)
            db.session.flush()
            dono = User(nome=email.split("@")[0].capitalize(), sobrenome="Teste", email=email, ativo=True, conta_id=conta.id, admin_sistema=admin,
                        senha=bcrypt.generate_password_hash(SENHA).decode("utf-8"))
            db.session.add(dono)
            db.session.flush()
            plano = Plano(nome="Mensal", valor=120, duracao_dias=30, descricao="", ativo=True, instrutor_id=dono.id, conta_id=conta.id)
            db.session.add(plano)
            db.session.flush()
            ids[nome] = conta.id
            if not admin:
                db.session.add(Aluno(nome="Camila Rocha", email="camila@exemplo.com", cpf="529.982.247-25", telefone="(12) 98211-4400", ativo=True,
                                     plano_id=plano.id, instrutor_id=dono.id, conta_id=conta.id, aceita_whatsapp=True))
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5107, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5107"
CLIENTE_ID = ids["Academia Corpo em Movimento"]

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)
        acionar = pg.tap if celular else pg.click
        entrar(pg, BASE, ADMIN, SENHA, celular)

        pg.goto(BASE + "/admin")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] a lista de contas abre, com os números", "Administração" in pg.inner_text("body") and "Academia Corpo em Movimento" in texto
              and "Em teste grátis" in texto and "Receita por mês" in texto)
        checa(f"[{nome}] lista: sem 'None' e sem a página estourar a largura (a tabela rola dentro do cartão)", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(700)     # espera a animação de troca de página acabar antes da foto
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-lista.png"), full_page=True)

        link = f"a[href='/admin/contas/{CLIENTE_ID}']"
        pg.locator(link).first.scroll_into_view_if_needed()
        acionar(link)
        pg.wait_for_url(BASE + f"/admin/contas/{CLIENTE_ID}", timeout=8000)
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] a página da conta mostra uso, assinatura e as ações", "Como a conta usa o sistema" in texto and "Assinatura" in texto
              and "Confirmar pagamento" in texto and "Apagar a conta" in texto)
        checa(f"[{nome}] página da conta: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(700)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-conta.png"), full_page=True)

        botao = pg.locator("form[action$='/entrar'] button >> visible=true").first
        botao.scroll_into_view_if_needed()
        with pg.expect_navigation(wait_until="load", timeout=10000):
            botao.tap() if celular else botao.click()
        aviso = pg.locator(".note--blue:has-text('como administrador')")
        checa(f"[{nome}] dentro da conta do cliente, o aviso azul aparece no topo", pg.url == BASE + "/" and aviso.count() == 1
              and "Academia Corpo em Movimento" in aviso.inner_text(), pg.url)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-dentro-da-conta.png"))
        pg.goto(BASE + "/alunos")
        checa(f"[{nome}] vê os alunos do cliente", "Camila Rocha" in pg.inner_text("#conteudo"))
        voltar = pg.locator("form[action='/admin/voltar'] button").first
        voltar.scroll_into_view_if_needed()
        with pg.expect_navigation(wait_until="load", timeout=10000):
            voltar.tap() if celular else voltar.click()
        checa(f"[{nome}] 'Voltar ao painel de administração' volta à página da conta", pg.url == BASE + f"/admin/contas/{CLIENTE_ID}"
              and pg.locator(".note--blue:has-text('como administrador')").count() == 0, pg.url)
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
