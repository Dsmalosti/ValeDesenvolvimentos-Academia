"""
[back-24-assinatura] Teste da assinatura do Vale Tec num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro):
  - conta com o teste grátis acabando: o aviso amarelo no painel, o link "Ver como pagar", a tela /assinatura com o
    "PIX copia e cola" e o botão de copiar;
  - conta bloqueada: o login cai direto na tela de conta bloqueada (sem o menu), qualquer outro endereço volta para
    ela, e o "Sair" funciona.
Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/assinatura_navegador.py [pasta-das-fotos]
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
from app.models import Conta, Plano, User  # noqa: E402
from tests.navegador._base import CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, sem_none_nem_rolagem  # noqa: E402

SENHA = "Senha-de-teste-123"
QUASE, ATRASADA = "carla@valetec.com", "bruno@valetec.com"
HOJE = date.today()
resultados = []


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """Duas academias: uma com o teste grátis acabando em 3 dias e outra vencida há 10 dias (bloqueada)."""
    app = create_app()
    assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
    app.config.update(VALE_TEC_PIX_CHAVE="60499733000144", VALE_TEC_SUPORTE_WHATSAPP="5512999990000")
    with app.app_context():
        db.create_all()
        for nome, email, fim in (("Academia Quase no Fim", QUASE, HOJE + timedelta(days=3)), ("Academia Atrasada", ATRASADA, HOJE - timedelta(days=10))):
            conta = Conta(nome=nome, teste_ate=fim)
            db.session.add(conta)
            db.session.flush()
            dono = User(nome=email.split("@")[0].capitalize(), sobrenome="Dono", email=email, ativo=True, conta_id=conta.id,
                        senha=bcrypt.generate_password_hash(SENHA).decode("utf-8"))
            db.session.add(dono)
            db.session.flush()
            db.session.add(Plano(nome="Mensal", valor=120, duracao_dias=30, descricao="", ativo=True, instrutor_id=dono.id, conta_id=conta.id))
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5106, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5106"

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)

        # ------------------------------------------------------------ teste grátis acabando: aviso e tela de pagamento
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)     # no navegador de verdade, o toque já dá a permissão
        acionar = pg.tap if celular else pg.click
        entrar(pg, BASE, QUASE, SENHA, celular)
        aviso = pg.locator(".note--yellow:has-text('Seu teste grátis termina')")
        checa(f"[{nome}] o painel avisa que o teste grátis termina em 3 dias", aviso.count() == 1 and "termina em 3 dias" in aviso.inner_text()
              and "R$ 59,99 por mês" in aviso.inner_text(), aviso.count())
        checa(f"[{nome}] painel com o aviso: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-aviso-no-painel.png"))
        aviso.locator("a[href='/assinatura']").scroll_into_view_if_needed()
        acionar(".note--yellow a[href='/assinatura']")
        pg.wait_for_url(BASE + "/assinatura", timeout=8000)
        texto = pg.inner_text("#conteudo")
        codigo = pg.locator("#pix-codigo")
        checa(f"[{nome}] a tela de assinatura mostra o teste, o preço e o PIX copia e cola", "Teste grátis até" in texto and "R$ 59,99 por mês" in texto
              and codigo.count() == 1 and codigo.input_value().startswith("000201") and "60499733000144" in codigo.input_value())
        acionar("button[data-copiar]")
        try:
            pg.wait_for_selector("text=Código PIX copiado", timeout=3000)
            copiou = True
        except Exception:
            copiou = False
        copiado = pg.evaluate("navigator.clipboard.readText()") if copiou else ""
        checa(f"[{nome}] o botão copia o código e avisa", copiou and copiado == codigo.input_value(), copiado[:30])
        botao = pg.locator("button[data-copiar]").bounding_box()
        checa(f"[{nome}] o botão de copiar tem tamanho de toque", botao and botao["height"] >= 44, botao)
        checa(f"[{nome}] tela de assinatura: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-assinatura.png"), full_page=True)
        conferir_console_e_rede(checa, nome + " teste", erros, falhas_rede)
        ctx.close()

        # ------------------------------------------------------------ [back-28-precos-e-promocao] preço de lançamento (50% de desconto para todos)
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)
        acionar = pg.tap if celular else pg.click
        pg.goto(BASE + "/criar-conta")
        promo = pg.locator(".note--green:has-text('Preço de lançamento')")
        checa(f"[{nome}] a tela de criar conta mostra o preço de lançamento", promo.count() == 1
              and "R$ 59,99 por mês para academia" in promo.inner_text().replace(chr(160), " ") and pg.locator(".note--green s:has-text('R$ 119,98')").count() == 1, promo.count())
        checa(f"[{nome}] criar conta com o preço: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2b-criar-conta-promocao.png"), full_page=True)
        pg.fill("#f-nome", "Marina Albuquerque")
        pg.fill("#f-email", f"marina.{nome}@valetec.com".replace(" ", ""))
        pg.fill("#f-senha", SENHA)
        acionar("button[type=submit]")
        pg.wait_for_url(BASE + "/", timeout=8000)
        pg.goto(BASE + "/assinatura")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] a conta nova vê R$ 59,99 com o preço de tabela riscado", "Preço de lançamento: 50% de desconto" in texto
              and "R$ 59,99 por mês" in texto and pg.locator("s:has-text('R$ 119,98')").count() == 1)
        checa(f"[{nome}] assinatura com o preço: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2c-assinatura-promocao.png"), full_page=True)
        conferir_console_e_rede(checa, nome + " preço", erros, falhas_rede)
        ctx.close()

        # ------------------------------------------------------------ conta bloqueada
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)
        acionar = pg.tap if celular else pg.click
        pg.goto(BASE + "/login")
        pg.fill("#f-identificador", ATRASADA)
        pg.fill("#f-senha", SENHA)
        acionar("button[type=submit]")
        pg.wait_for_url(BASE + "/assinatura", timeout=8000)
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] o login da conta bloqueada cai na tela de bloqueio, sem o menu", "Sua conta está bloqueada" in texto
              and pg.locator("#gaveta, .rail").count() == 0 and pg.locator("#pix-codigo").count() == 1)
        checa(f"[{nome}] a tela diz até quando os dados ficam guardados e mostra o WhatsApp do suporte", "guardados até" in texto
              and pg.locator("a[href='https://wa.me/5512999990000']").count() == 1)
        checa(f"[{nome}] tela de bloqueio: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-bloqueada.png"), full_page=True)
        pg.goto(BASE + "/alunos")
        checa(f"[{nome}] outro endereço volta para a tela de bloqueio", pg.url == BASE + "/assinatura")
        sair = pg.locator("form[action='/sair'] button")
        sair.scroll_into_view_if_needed()
        with pg.expect_navigation(wait_until="load", timeout=10000):
            acionar("form[action='/sair'] button")
        checa(f"[{nome}] o botão Sair funciona na tela de bloqueio", "/login" in pg.url, pg.url)
        conferir_console_e_rede(checa, nome + " bloqueada", erros, falhas_rede)
        ctx.close()
    nav.close()

srv.shutdown()
ok = sum(1 for r in resultados if r[1])
print(f"\n{ok}/{len(resultados)} passaram")
print("fotos em:", FOTOS)
for n, passou, d in resultados:
    if not passou:
        print(" -", n, "|", d)
