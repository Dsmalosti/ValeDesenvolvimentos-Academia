"""
Teste das telas de ALUNOS do front novo num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro): abrir a lista pelo
menu, cadastrar (página inteira no celular, popup no desktop), ver os avisos de validação do
navegador e do servidor, abrir o perfil, editar, buscar ao vivo e desativar. Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/alunos_navegador.py [pasta-das-fotos]
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
CPF_DA_CAMILA = "529.982.247-25"                        # CPF de exemplo com os dígitos finais certos
CPFS_NOVOS = ["987.654.320-29", "987.654.321-00"]       # idem, um para cada cenário
resultados = []


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
        plano = Plano(nome="Mensal", valor=149.90, duracao_dias=30, descricao="", ativo=True, instrutor_id=dona.id, conta_id=conta.id)
        db.session.add(plano)
        db.session.flush()
        for i, nome in enumerate(["Camila Duarte dos Santos Albuquerque", "Larissa Alves", "Thiago Nunes", "Bruna Lima", "Eduardo Prado",
                                  "Rodrigo Prado", "Julia Ferreira", "Marcos Costa", "Paula Reis", "Otavio Melo"]):
            aluno = Aluno(nome=nome, email=f"aluno{i}@exemplo.com", cpf=CPF_DA_CAMILA if i == 0 else "111.222.333-%02d" % i, telefone="(12) 98211-44%02d" % i,
                          ativo=i != 7, data_nascimento=date(1990, 1, 1 + i), plano_id=plano.id, instrutor_id=dona.id, conta_id=conta.id)
            db.session.add(aluno)
            db.session.flush()
            if i in (0, 1):   # Camila em dia, Larissa em atraso
                pago = hoje - timedelta(days=5 if i == 0 else 45)
                db.session.add(Pagamento(aluno_id=aluno.id, instrutor_id=dona.id, conta_id=conta.id, valor=149.90, forma_pagamento="pix",
                                         data_pagamento=pago, data_vencimento=pago + timedelta(days=30)))
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5094, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5094"

CENARIOS = [
    ("celular-390-claro", dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2), "light"),
    ("desktop-1440-escuro", dict(viewport={"width": 1440, "height": 900}), "dark"),
]

with sync_playwright() as p:
    nav = p.chromium.launch()
    for n_cenario, (nome, opts, tema) in enumerate(CENARIOS):
        celular = opts.get("has_touch", False)
        ctx = nav.new_context(color_scheme=tema, **opts)
        pg = ctx.new_page()
        acionar = pg.tap if celular else pg.click
        erros, falhas_rede, envios = [], [], []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and erros.append(m.text))
        pg.on("response", lambda r: r.status >= 400 and falhas_rede.append(f"{r.status} {r.url}"))
        pg.on("request", lambda r: r.method == "POST" and envios.append(r.url))   # o que chegou a ser enviado ao servidor
        cpf_novo = CPFS_NOVOS[n_cenario]
        nome_novo = "Fernanda Teste Celular" if celular else "Gustavo Teste Desktop"

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
        acionar(".tabbar__item:has-text('Alunos')" if celular else ".rail .navicon[aria-label='Alunos']")
        pg.wait_for_url("**/alunos", timeout=6000)
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] menu 'Alunos' abre a lista NOVA", pg.locator(".app .main").count() == 1 and "Otavio Melo" in texto)
        checa(f"[{nome}] lista sem 'None' e sem rolagem lateral", "None" not in texto
              and pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        checa(f"[{nome}] mostra quem está em atraso", "Pendente" in texto)
        pg.wait_for_timeout(700)   # espera a animação de troca de página acabar, para a foto sair limpa
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-lista.png"), full_page=True)

        # --- cadastro: página inteira no celular, popup no desktop ---
        if celular:
            pg.tap("a.btn:has-text('Novo aluno')")
            pg.wait_for_url("**/alunos/novo", timeout=6000)
            F = "#conteudo "
        else:
            pg.click("button[data-open='novo-aluno']")
            pg.wait_for_selector("#novo-aluno[open]", timeout=3000)
            F = "#novo-aluno "
        checa(f"[{nome}] formulário de cadastro abre ({'página' if celular else 'popup'})", pg.is_visible(F + "#f-nome"))
        envios.clear()
        acionar(F + "button[type=submit]")
        pg.wait_for_timeout(500)
        checa(f"[{nome}] enviar vazio: o navegador avisa, não sai da tela e nada vai ao servidor",
              pg.locator(F + ".is-invalid").count() >= 1 and not envios
              and ("/alunos/novo" in pg.url if celular else pg.locator("#novo-aluno[open]").count() == 1), envios)
        pg.fill(F + "#f-nome", nome_novo)
        pg.fill(F + "#f-cpf", "111.222.333-00")                        # 11 números, mas os dois últimos não batem
        pg.fill(F + "#f-telefone", "(12) 99999-0000")
        pg.fill(F + "#f-email", f"novo{n_cenario}@exemplo.com")
        pg.fill(F + "#f-data_nascimento", "25/12/1990")
        pg.select_option(F + "#f-plano_id", index=1)
        pg.select_option(F + "#f-forma_pagamento", "pix")
        pg.fill(F + "#f-dia_vencimento", "10")
        pg.fill(F + "#f-observacoes", "Cadastro feito pelo teste de navegador.")
        acionar(F + "button[type=submit]")
        pg.wait_for_timeout(500)
        checa(f"[{nome}] CPF com dígito errado: o navegador avisa antes de enviar",
              "CPF inválido" in pg.inner_text(F.strip()) and not envios, envios)
        if celular:
            pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-cadastro.png"), full_page=True)
        else:
            pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-cadastro.png"))
        pg.fill(F + "#f-cpf", CPF_DA_CAMILA)                           # CPF certo, mas que já é de outro aluno
        acionar(F + "button[type=submit]")
        pg.wait_for_url("**/alunos/novo", timeout=6000)
        pg.wait_for_timeout(600)
        corpo = pg.inner_text("#conteudo")
        checa(f"[{nome}] CPF repetido: o SERVIDOR recusa, avisa e devolve o que foi digitado",
              "Já existe um aluno com este CPF." in corpo and pg.input_value("#conteudo #f-nome") == nome_novo)
        pg.fill("#conteudo #f-cpf", cpf_novo)
        acionar("#conteudo button[type=submit]")
        pg.wait_for_url(lambda u: u.rstrip("/").rsplit("/", 1)[-1].isdigit(), timeout=8000)

        # --- perfil ---
        perfil = pg.inner_text("#conteudo")
        checa(f"[{nome}] depois de salvar abre o perfil do aluno novo", nome_novo in perfil and "Mensal" in perfil and "PIX" in perfil)
        checa(f"[{nome}] perfil sem 'None'", "None" not in perfil, [l for l in perfil.splitlines() if "None" in l][:3])
        pg.wait_for_timeout(700)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-perfil.png"), full_page=True)
        url_perfil = pg.url

        # --- editar ---
        acionar(".m-header a[aria-label^='Editar']" if celular else ".perfil-head a:has-text('Editar')")
        pg.wait_for_url("**/editar", timeout=6000)
        checa(f"[{nome}] edição vem preenchida", pg.input_value("#f-nome") == nome_novo and pg.input_value("#f-cpf") == cpf_novo)
        pg.fill("#f-telefone", "(12) 98888-7777")
        acionar("#conteudo button[type=submit]")
        pg.wait_for_url(url_perfil, timeout=8000)
        checa(f"[{nome}] alteração salva aparece no perfil", "(12) 98888-7777" in pg.inner_text("#conteudo"))

        # --- busca ao vivo ---
        pg.goto(BASE + "/alunos/buscar")
        pg.fill("#q-busca", "lari")
        try:
            pg.wait_for_selector("#resultado-busca :text('Larissa Alves')", timeout=4000)
            achou = True
        except Exception:
            achou = False
        checa(f"[{nome}] busca ao vivo acha sem recarregar a página", achou and pg.url.endswith("/alunos/buscar"))

        # --- desativar ---
        pg.goto(url_perfil)
        pg.locator("[data-open='dlg-inativar']").scroll_into_view_if_needed()
        acionar("[data-open='dlg-inativar']")
        pg.wait_for_selector("#dlg-inativar[open]", timeout=3000)
        acionar("#dlg-inativar button[type=submit]")
        pg.wait_for_url("**/alunos", timeout=8000)
        pg.goto(BASE + "/alunos?status=inativo&q=" + nome_novo.split()[0])
        checa(f"[{nome}] desativar: o aluno vai para os inativos e não é apagado", nome_novo in pg.inner_text("#conteudo"))

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
