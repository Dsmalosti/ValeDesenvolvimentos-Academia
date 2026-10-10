"""
Teste das telas de PLANOS do front novo num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro): lista em linhas, criar e editar em página inteira,
desativar. Desktop (1440 px, tema escuro): cartões com o painel lateral, criar e editar pelo
painel, inativar e reativar pelo cartão, plano em destaque vindo do painel. Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/planos_navegador.py [pasta-das-fotos]
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
from app.models import Aluno, Conta, Pagamento, Plano, User  # noqa: E402

EMAIL, SENHA = "marina@valetec.com", "Senha-de-teste-123"
resultados = []
ids = {}


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    app = create_app()
    assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
    hoje = date.today()
    with app.app_context():
        db.create_all()
        conta = Conta(nome="Academia Corpo em Movimento")
        db.session.add(conta)
        db.session.flush()
        dona = User(nome="Marina", sobrenome="Albuquerque", email=EMAIL, ativo=True, conta_id=conta.id,
                    senha=bcrypt.generate_password_hash(SENHA).decode("utf-8"))
        db.session.add(dona)
        db.session.flush()
        planos = {}
        for nome, valor, dias, ativo in [("Mensal", 149.90, 30, True), ("Anual com um nome bem comprido para testar", 1290, 365, True),
                                         ("Promoção antiga", 99, 30, False)]:
            planos[nome] = Plano(nome=nome, valor=valor, duracao_dias=dias, descricao="", ativo=ativo, instrutor_id=dona.id, conta_id=conta.id)
            db.session.add(planos[nome])
        db.session.flush()
        ids["mensal"] = planos["Mensal"].id
        for i, nome in enumerate(["Camila Duarte", "Larissa Alves", "Thiago Nunes", "Bruna Lima"]):
            aluno = Aluno(nome=nome, email=f"aluno{i}@exemplo.com", cpf="111.222.333-%02d" % i, telefone="(12) 98211-44%02d" % i, ativo=True,
                          data_nascimento=date(1990, 1, 1 + i), instrutor_id=dona.id, conta_id=conta.id,
                          plano_id=planos["Mensal"].id if i < 3 else planos["Anual com um nome bem comprido para testar"].id)
            db.session.add(aluno)
            db.session.flush()
            if i < 2:   # dois pagamentos do Mensal neste mês
                db.session.add(Pagamento(aluno_id=aluno.id, instrutor_id=dona.id, conta_id=conta.id, valor=149.90, forma_pagamento="pix",
                                         data_pagamento=hoje, data_vencimento=hoje + timedelta(days=30)))
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5095, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5095"

CENARIOS = [
    ("celular-390-claro", dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2), "light"),
    ("desktop-1440-escuro", dict(viewport={"width": 1440, "height": 900}), "dark"),
]

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        ctx = nav.new_context(color_scheme=tema, **opts)
        pg = ctx.new_page()
        acionar = pg.tap if celular else pg.click
        erros, falhas_rede, envios = [], [], []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and erros.append(m.text))
        pg.on("response", lambda r: r.status >= 400 and falhas_rede.append(f"{r.status} {r.url}"))
        pg.on("request", lambda r: r.method == "POST" and envios.append(r.url))   # o que chegou a ser enviado ao servidor
        novo = "Trimestral Celular" if celular else "Trimestral Desktop"
        cartao = ".plano-m" if celular else "article.plano"            # cada plano: linha no celular, cartão no desktop

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

        # --- lista, pelo menu ---
        acionar(".tabbar__item:has-text('Planos')" if celular else ".rail .navicon[aria-label='Planos']")
        pg.wait_for_url("**/planos", timeout=6000)
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] menu 'Planos' abre a lista NOVA", pg.locator(".app .main").count() == 1 and "Mensal" in texto and "R$ 149,90" in texto)
        checa(f"[{nome}] mostra alunos e participação no faturamento", "3 alunos" in texto and "100% do faturamento do mês" in texto)
        checa(f"[{nome}] plano pausado aparece marcado como inativo", "inativo" in texto.lower() and "Promoção antiga" in texto)
        checa(f"[{nome}] lista sem 'None' e sem rolagem lateral", "None" not in texto
              and pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        pg.wait_for_timeout(700)   # espera a animação de troca de página acabar, para a foto sair limpa
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-lista.png"), full_page=True)

        # --- criar: página inteira no celular, painel lateral no desktop ---
        if celular:
            pg.tap("a.btn:has-text('Criar novo plano')")
            pg.wait_for_url("**/planos/novo", timeout=6000)
            F = "#conteudo "
        else:
            pg.click("a.btn:has-text('Criar plano')")
            pg.wait_for_timeout(400)
            checa(f"[{nome}] botão 'Criar plano' leva o cursor ao nome, no painel lateral",
                  pg.evaluate("document.activeElement && document.activeElement.id") == "f-nome")
            F = "#painel-plano "
        envios.clear()
        acionar(F + "button[type=submit]:has-text('plano')")
        pg.wait_for_timeout(500)
        checa(f"[{nome}] enviar vazio: o navegador avisa e nada vai ao servidor", pg.locator(F + ".is-invalid").count() >= 1 and not envios, envios)
        pg.fill(F + "#f-nome", "mensal")                                   # nome que já existe (sem diferenciar maiúscula)
        pg.fill(F + "#f-valor", "39900")                                   # a máscara do front transforma em 399,00
        checa(f"[{nome}] o valor digitado vira reais com vírgula", pg.input_value(F + "#f-valor") == "399,00", pg.input_value(F + "#f-valor"))
        pg.fill(F + "#f-duracao_dias", "90")
        pg.fill(F + "#f-descricao", "Três meses com desconto.")
        if celular:
            pg.select_option(F + "#f-avaliacoes_incluidas", "1")
        acionar(F + "button[type=submit]:has-text('plano')")
        pg.wait_for_url("**/planos/novo", timeout=6000)
        pg.wait_for_timeout(600)
        checa(f"[{nome}] nome repetido: o SERVIDOR recusa, avisa e devolve o que foi digitado",
              "Já existe um plano com este nome." in pg.inner_text("#conteudo") and pg.input_value("#conteudo #f-valor") == "399,00")
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-erro.png"), full_page=True)
        pg.fill("#conteudo #f-nome", novo)
        acionar("#conteudo button[type=submit]:has-text('plano')")
        pg.wait_for_url(BASE + "/planos", timeout=8000)
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] plano criado aparece na lista com o valor certo", novo in texto and "R$ 399,00" in texto and "90 dias" in texto)

        # --- editar ---
        if celular:
            pg.tap(f"{cartao}:has-text('{novo}')")
            pg.wait_for_url("**/editar", timeout=6000)
            F = "#conteudo "
            checa(f"[{nome}] edição vem preenchida, com a avaliação escolhida",
                  pg.input_value("#f-nome") == novo and pg.input_value("#f-valor") == "399,00" and pg.input_value("#f-avaliacoes_incluidas") == "1")
        else:
            pg.click(f"{cartao}:has-text('{novo}') a:has-text('Editar')")
            pg.wait_for_url("**/planos?editar=*", timeout=6000)
            F = "#painel-plano "
            checa(f"[{nome}] 'Editar' preenche o painel lateral", pg.input_value(F + "#f-nome") == novo and pg.input_value(F + "#f-valor") == "399,00")
        pg.fill(F + "#f-valor", "42950")
        acionar(F + "button[type=submit]:has-text('Salvar')")
        pg.wait_for_url(BASE + "/planos", timeout=8000)
        checa(f"[{nome}] alteração salva aparece na lista", "R$ 429,50" in pg.inner_text(f"{cartao}:has-text('{novo}')"))
        pg.wait_for_timeout(700)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-depois-de-editar.png"), full_page=True)

        # --- pausar e reativar ---
        if celular:
            pg.tap(f"{cartao}:has-text('{novo}')")
            pg.wait_for_url("**/editar", timeout=6000)
            pg.locator("button:has-text('Desativar plano')").scroll_into_view_if_needed()
            pg.tap("button:has-text('Desativar plano')")
        else:
            pg.click(f"{cartao}:has-text('{novo}') button:has-text('Inativar')")
        pg.wait_for_url(BASE + "/planos", timeout=8000)
        pg.wait_for_timeout(400)
        checa(f"[{nome}] pausar: o plano continua na lista, marcado como inativo", "inativo" in pg.inner_text(f"{cartao}:has-text('{novo}')").lower())
        pg.goto(BASE + "/alunos/novo")
        opcoes = pg.locator("#conteudo #f-plano_id option").all_inner_texts()
        checa(f"[{nome}] plano pausado some do cadastro de aluno", not any(novo in o for o in opcoes) and any("Mensal" in o for o in opcoes), opcoes)
        if not celular:
            pg.goto(BASE + "/planos")
            pg.click(f"{cartao}:has-text('{novo}') button:has-text('Reativar')")
            pg.wait_for_url(BASE + "/planos", timeout=8000)
            pg.wait_for_timeout(400)
            checa(f"[{nome}] reativar pelo cartão", "Inativo" not in pg.inner_text(f"{cartao}:has-text('{novo}')"))
            # veio do gráfico "De onde vem o faturamento" do painel: o plano certo fica em destaque
            pg.goto(BASE + f"/planos?destaque={ids['mensal']}")
            pg.wait_for_timeout(900)
            checa(f"[{nome}] ?destaque= destaca o cartão do plano", pg.locator(f"{cartao}[data-plano='{ids['mensal']}'].is-destaque").count() == 1)

        esperadas = [f for f in falhas_rede if not f.endswith("/favicon.ico")]
        checa(f"[{nome}] nenhum arquivo 404/500", not esperadas, esperadas[:5])
        # ao ir de uma tela nova para uma antiga o Chromium cancela a animação de troca de página e avisa: é esperado
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
