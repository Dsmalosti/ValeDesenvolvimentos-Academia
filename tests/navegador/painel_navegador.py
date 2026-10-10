"""
Teste do PAINEL novo num navegador de verdade (Playwright + Chromium).

Entra pela tela de login e confere o painel no celular (390 px, com toque) e no desktop
(1440 px), nos temas claro e escuro: layout novo, números, popups, menu, pontes para as
telas antigas, telas "em construção" e sair. Salva uma foto de cada cenário.

Sobe o app do repositório com SQLite descartável e uma academia de exemplo; nunca toca o
banco do .env. Não roda junto com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/painel_navegador.py [pasta-das-fotos]
"""
import os
import sys
import tempfile
import threading
from datetime import date, datetime, timedelta

sys.dont_write_bytecode = True  # o repositório versiona .pyc; não gerar novos ao testar
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

_PASTA = tempfile.mkdtemp(prefix="vt-navegador-")
os.environ["DATABASE_URI"] = "sqlite:///" + os.path.join(_PASTA, "navegador.db").replace("\\", "/")
os.environ["SECRET_KEY"] = "chave-so-de-teste"
os.environ["FLASK_CONFIG"] = "testing"
FOTOS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_PASTA, "fotos")
os.makedirs(FOTOS, exist_ok=True)

from playwright.sync_api import sync_playwright  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions.database import db  # noqa: E402
from app.extensions.security import bcrypt  # noqa: E402
from app.models import Aluno, Pagamento, Plano, User  # noqa: E402

EMAIL, SENHA = "marina@valetec.com", "Senha-de-teste-123"
resultados = []


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """App do repositório com uma academia de exemplo: gente em dia, em atraso, vencendo e aniversariante."""
    app = create_app()
    assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
    hoje = date.today()
    with app.app_context():
        db.create_all()
        dona = User(nome="Marina", sobrenome="Albuquerque dos Santos", email=EMAIL, ativo=True,
                    senha=bcrypt.generate_password_hash(SENHA).decode("utf-8"))
        db.session.add(dona)
        db.session.flush()
        planos = [Plano(nome=n, valor=v, duracao_dias=d, descricao="", ativo=True, instrutor_id=dona.id)
                  for n, v, d in [("Mensal", 149.90, 30), ("Trimestral", 399, 90), ("Anual", 1290, 365)]]
        db.session.add_all(planos)
        db.session.flush()
        # (nome, plano, dias desde o cadastro, dias desde o último pagamento ou None, ativo, aniversário hoje)
        pessoas = [("Camila Duarte dos Santos Albuquerque", 0, 3, 3, True, True), ("Larissa Alves", 0, 200, 44, True, False),
                   ("Thiago Nunes", 1, 150, 20, True, False), ("Bruna Lima", 0, 95, 25, True, False),
                   ("Eduardo Prado", 0, 400, 38, True, False), ("Rodrigo Prado", 2, 20, 20, True, False),
                   ("Julia Ferreira", 1, 60, None, True, False), ("Marcos Costa", 0, 500, 90, False, False)]
        for i, (nome, p, dias_cad, dias_pag, ativo, niver) in enumerate(pessoas):
            nasc = date(1992, hoje.month, hoje.day) if niver else date(1990, 1, 1 + i)
            aluno = Aluno(nome=nome, email=f"aluno{i}@exemplo.com", cpf=f"cpf-{i}", telefone="(12) 98211-44%02d" % i,
                          ativo=ativo, data_nascimento=nasc, plano_id=planos[p].id, instrutor_id=dona.id,
                          data_cadastro=datetime.combine(hoje - timedelta(days=dias_cad), datetime.min.time()))
            db.session.add(aluno)
            db.session.flush()
            if dias_pag is not None:
                pago = hoje - timedelta(days=dias_pag)
                db.session.add(Pagamento(aluno_id=aluno.id, instrutor_id=dona.id, valor=planos[p].valor, forma_pagamento="pix",
                                         data_pagamento=pago, data_vencimento=pago + timedelta(days=planos[p].duracao_dias)))
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5093, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5093"

CENARIOS = [
    ("celular-390-claro", dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2), "light"),
    ("celular-390-escuro", dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2), "dark"),
    ("desktop-1440-claro", dict(viewport={"width": 1440, "height": 900}), "light"),
    ("desktop-1440-escuro", dict(viewport={"width": 1440, "height": 900}), "dark"),
]

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        ctx = nav.new_context(color_scheme=tema, **opts)
        pg = ctx.new_page()
        acionar = pg.tap if celular else pg.click
        # o painel tem os cards duas vezes no HTML (celular e desktop); só um conjunto fica visível
        CARD = ".m-only .kpi" if celular else ".d-only .kpi"
        erros, falhas_rede = [], []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and erros.append(m.text))
        pg.on("response", lambda r: r.status >= 400 and falhas_rede.append(f"{r.status} {r.url}"))

        # --- entra pela tela de login ---
        pg.goto(BASE + "/")
        pg.wait_for_selector("#dlg-perfil[open]", timeout=5000)
        acionar('#dlg-perfil [data-valor="recepcao"]')
        pg.wait_for_timeout(400)
        pg.fill("#f-identificador", EMAIL)
        pg.fill("#f-senha", SENHA)
        acionar("button[type=submit]")
        pg.wait_for_url(BASE + "/", timeout=8000)
        pg.wait_for_selector(CARD, timeout=5000)
        checa(f"[{nome}] depois do login abre o painel NOVO", pg.locator(".app .main").count() == 1 and "Vale Tec" in pg.title())

        # --- popup automático de avisos (abre sozinho depois de um instante) ---
        try:
            pg.wait_for_selector("#pop-avisos[open]", timeout=4000)
            abriu = True
        except Exception:
            abriu = False
        checa(f"[{nome}] popup de avisos abre sozinho com alunos em risco", abriu and pg.locator("#pop-avisos .pop-item").count() >= 1)
        if abriu:
            pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-avisos.png"))
            acionar("#pop-avisos [data-close]")
            pg.wait_for_timeout(500)
        checa(f"[{nome}] popup de avisos fecha", pg.locator("#pop-avisos[open]").count() == 0)

        # --- números e conteúdo ---
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] nenhum 'None' na tela", "None" not in texto, [l for l in texto.splitlines() if "None" in l][:3])
        checa(f"[{nome}] mostra os indicadores com dado do banco", "Alunos ativos" in texto and "Inadimplência" in texto)
        checa(f"[{nome}] saúda a pessoa pelo nome", ("Olá, Marina" in texto) if celular else ("Marina" in texto))
        larg = pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        checa(f"[{nome}] sem rolagem lateral", larg[0] <= larg[1], larg)
        checa(f"[{nome}] gráfico de alunos ativos foi desenhado", pg.locator('[data-chart="linha"] svg').count() == 1)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-painel.png"), full_page=True)

        # --- card abre o popup com a lista ---
        card = ".m-only .kpi[data-open='dlg-vencem']" if celular else ".d-only .kpi[data-open='dlg-vencem']"
        pg.locator(card).scroll_into_view_if_needed()
        acionar(card)
        pg.wait_for_timeout(500)
        checa(f"[{nome}] card 'Vencem este mês' abre o popup", pg.locator("#dlg-vencem[open]").count() == 1)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(400)

        # --- menu ---
        if celular:
            checa(f"[{nome}] barra de abas embaixo e sem rail lateral", pg.is_visible(".tabbar") and not pg.is_visible(".rail"))
            pg.tap("[data-open='gaveta']")
            pg.wait_for_timeout(500)
            checa(f"[{nome}] gaveta do menu abre", pg.locator("#gaveta[open]").count() == 1 and pg.locator("#gaveta .dlink").count() >= 5)
            pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-gaveta.png"))
            pg.tap("#gaveta .dlink:has-text('Configurações')")
        else:
            checa(f"[{nome}] rail lateral visível e sem barra de abas", pg.is_visible(".rail") and not pg.is_visible(".tabbar"))
            pg.click(".rail .navicon[aria-label='Configurações']")
        pg.wait_for_url("**/configuracoes", timeout=6000)
        checa(f"[{nome}] seção sem backend mostra 'Em construção' no layout novo",
              "Em construção" in pg.inner_text("#conteudo") and pg.locator(".app .main").count() == 1)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-4-em-construcao.png"))

        # --- ponte para a tela antiga de alunos ---
        pg.goto(BASE + "/")
        pg.wait_for_selector(CARD)
        if celular:
            pg.tap(".tabbar__item:has-text('Alunos')")
        else:
            pg.click(".rail .navicon[aria-label='Alunos']")
        pg.wait_for_url("**/alunos/listar/", timeout=6000)
        checa(f"[{nome}] menu 'Alunos' leva à tela antiga de alunos", "Camila" in pg.content())

        # --- sair ---
        pg.goto(BASE + "/")
        pg.wait_for_selector(CARD)
        if celular:
            pg.tap("[data-open='gaveta']")
            pg.wait_for_timeout(500)
            pg.tap("#gaveta button.dlink:has-text('Sair')")
        else:
            pg.click(".rail button[aria-label='Sair']")
        pg.wait_for_url("**/login", timeout=6000)
        checa(f"[{nome}] sair volta para a tela de login", "/login" in pg.url)
        pg.goto(BASE + "/")
        checa(f"[{nome}] depois de sair, o painel pede login de novo", "/login" in pg.url)

        esperadas = [f for f in falhas_rede if not f.endswith("/favicon.ico")]
        checa(f"[{nome}] nenhum arquivo 404/500", not esperadas, esperadas[:5])
        # Conhecido e esperado enquanto houver tela antiga: ao sair de uma tela nova (que anima a troca de
        # página) para uma antiga (que não anima), o Chromium cancela a animação e registra isso no console.
        # Também cancela quando a foto de página inteira muda o tamanho da janela. Não é erro do sistema.
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
