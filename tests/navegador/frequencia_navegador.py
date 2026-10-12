"""
Teste da FREQUÊNCIA do front novo num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro): tela de check-in,
busca ao vivo, registrar entrada, toque repetido, aluno inativo, cartão de frequência no perfil,
"sem dado", card de ausentes no painel e, no desktop, bloquear e liberar acesso. Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/frequencia_navegador.py [pasta-das-fotos]
"""
import os
import sys
import tempfile
import threading
from datetime import datetime, timedelta

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
from app.models import Aluno, Conta, Frequencia, Plano, User  # noqa: E402
from tests.navegador._base import CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, sem_none_nem_rolagem  # noqa: E402

EMAIL, SENHA = "marina@valetec.com", "Senha-de-teste-123"
AGORA = datetime.now()
resultados = []
ids = {}


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """Academia com o check-in ligado. Bruno e Paula já entraram hoje; Sumido veio pela última vez há 20 dias."""
    app = create_app()
    assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
    with app.app_context():
        db.create_all()
        conta = Conta(nome="Academia Corpo em Movimento", checkin_ativo=True)
        db.session.add(conta)
        db.session.flush()
        dona = User(nome="Marina", sobrenome="Albuquerque", email=EMAIL, ativo=True, conta_id=conta.id,
                    senha=bcrypt.generate_password_hash(SENHA).decode("utf-8"))
        db.session.add(dona)
        db.session.flush()
        plano = Plano(nome="Mensal", valor=149.90, duracao_dias=30, descricao="", ativo=True, instrutor_id=dona.id, conta_id=conta.id)
        db.session.add(plano)
        db.session.flush()
        nomes = ["Camila Celular", "Camila Desktop", "Bruno Dias", "Paula Reis", "Sumido Silva", "Nunca Veio", "Caio Inativo"]
        for i, nome in enumerate(nomes):
            aluno = Aluno(nome=nome, email=f"aluno{i}@exemplo.com", cpf=f"111.222.333-0{i}", telefone="(12) 98211-4400", ativo=nome != "Caio Inativo",
                          plano_id=plano.id, instrutor_id=dona.id, conta_id=conta.id)
            db.session.add(aluno)
            db.session.flush()
            ids[nome] = aluno.id
        entradas = [("Bruno Dias", AGORA - timedelta(minutes=20)), ("Paula Reis", AGORA - timedelta(minutes=40)),
                    ("Bruno Dias", AGORA - timedelta(days=2)), ("Sumido Silva", AGORA - timedelta(days=20))]
        for nome, quando in entradas:
            db.session.add(Frequencia(conta_id=conta.id, aluno_id=ids[nome], data_hora_entrada=quando, origem="recepcao", instrutor_id=dona.id))
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5097, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5097"

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        camila = "Camila Celular" if celular else "Camila Desktop"
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)

        def acionar(seletor):
            pg.locator(seletor).first.scroll_into_view_if_needed()
            (pg.tap if celular else pg.click)(seletor)

        def buscar(texto):
            """Digita na busca do check-in e espera o pedaço de sugestões chegar do servidor."""
            pg.fill("#f-busca-checkin", texto)
            pg.wait_for_function("t => document.querySelector('#sugestoes-checkin').innerText.toLowerCase().includes(t)", arg=texto.lower(), timeout=5000)

        def numeros():
            """Os três números do topo da tela. Eles sobem animados: espera a contagem terminar antes de ler."""
            pg.wait_for_selector("[data-chart='barras'] svg", timeout=5000)
            pg.wait_for_timeout(1500)
            return pg.locator(".freq-stats .stat__val").all_inner_texts()

        entrar(pg, BASE, EMAIL, SENHA, celular)

        # --- o painel mostra quem sumiu ---
        pg.goto(BASE + "/")
        pg.wait_for_selector(".m-only .kpi" if celular else ".d-only .kpi")
        painel = pg.inner_text("#conteudo")
        checa(f"[{nome}] o painel tem o card de ausentes (check-in ligado)", "Ausentes" in painel)
        if not celular:
            pg.click(".kpi[data-open='dlg-ausentes'] >> visible=true")
            pg.wait_for_selector("#dlg-ausentes[open]", timeout=3000)
            ausentes = pg.inner_text("#dlg-ausentes")
            checa(f"[{nome}] o popup de ausentes lista só quem tem entrada e sumiu", "Sumido Silva" in ausentes and "20 dias sem vir" in ausentes
                  and "Nunca Veio" not in ausentes and "Caio" not in ausentes)
            pg.click("#dlg-ausentes [data-close]")
            pg.wait_for_timeout(300)

        # --- tela de frequência ---
        if celular:
            checa(f"[{nome}] a gaveta do menu tem o atalho de check-in", pg.locator("#gaveta a[href='/frequencia']").count() == 1)
            pg.goto(BASE + "/frequencia")
        else:
            pg.click(".rail .navicon[aria-label='Frequência']")
            pg.wait_for_url("**/frequencia", timeout=6000)
        pg.wait_for_selector("[data-chart='barras'] svg", timeout=5000)
        texto = pg.inner_text("#conteudo")
        ja = 2 if celular else 3       # o cenário do desktop roda depois do celular, que já registrou uma entrada
        antes = numeros()
        checa(f"[{nome}] tela nova de frequência com os números do dia", pg.locator(".app .main").count() == 1 and antes[:2] == [str(ja), str(ja)], antes)
        checa(f"[{nome}] mostra quem está na academia agora", "Bruno Dias" in texto and "Paula Reis" in texto)
        checa(f"[{nome}] sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(700)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-frequencia.png"), full_page=True)

        # --- busca ao vivo e entrada em um toque ---
        buscar(camila.lower()[:10])
        checa(f"[{nome}] busca ao vivo acha o aluno sem recarregar a página", camila in pg.inner_text("#sugestoes-checkin") and pg.url.endswith("/frequencia"))
        acionar(f"#sugestoes-checkin .sug-item:has-text('{camila}') button[type=submit]")
        pg.wait_for_url("**/frequencia", timeout=8000)
        pg.wait_for_selector("[data-chart='barras'] svg", timeout=5000)
        depois = numeros()
        checa(f"[{nome}] um toque registra a entrada e os números sobem", depois[:2] == [str(ja + 1), str(ja + 1)] and camila in pg.inner_text(".freq-agora"), depois)

        # --- toque repetido não conta de novo ---
        buscar(camila.lower()[:10])
        acionar(f"#sugestoes-checkin .sug-item:has-text('{camila}') button[type=submit]")
        pg.wait_for_url("**/frequencia", timeout=8000)
        pg.wait_for_selector("[data-chart='barras'] svg", timeout=5000)
        checa(f"[{nome}] registrar o mesmo aluno de novo não cria outra entrada", numeros()[:2] == [str(ja + 1), str(ja + 1)])

        # --- aluno inativo é recusado ---
        buscar("caio")
        acionar("#sugestoes-checkin .sug-item:has-text('Caio Inativo') button[type=submit]")
        pg.wait_for_url("**/frequencia", timeout=8000)
        pg.wait_for_selector("[data-chart='barras'] svg", timeout=5000)
        checa(f"[{nome}] aluno inativo não entra", numeros()[0] == str(ja + 1) and "Caio" not in pg.inner_text(".freq-agora"))
        if not celular:
            checa(f"[{nome}] a tabela 'Check-ins de hoje' lista as entradas", pg.locator(".freq-tabela tbody tr").count() == ja + 1)
            planilha = ctx.request.get(BASE + "/frequencia/exportar")
            checa(f"[{nome}] exportar devolve a planilha do dia", planilha.status == 200 and camila in planilha.text() and "Horário" in planilha.text())
        pg.wait_for_timeout(600)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-depois-do-checkin.png"), full_page=True)

        # --- perfil: cartão de frequência, e "sem dado" para quem nunca veio ---
        pg.goto(BASE + f"/alunos/{ids['Bruno Dias']}")
        perfil = pg.inner_text("#conteudo")
        checa(f"[{nome}] perfil mostra a assiduidade de quem tem entradas", "de assiduidade nos últimos 30 dias" in perfil and "7%" in perfil and "None" not in perfil)
        pg.wait_for_timeout(500)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-perfil.png"), full_page=True)
        pg.goto(BASE + f"/alunos/{ids['Nunca Veio']}")
        perfil = pg.inner_text("#conteudo")
        checa(f"[{nome}] quem nunca teve entrada aparece como 'sem dado', não como 0%", "Sem dado: nenhuma entrada registrada ainda." in perfil and "0%" not in perfil)

        # --- bloquear e liberar acesso (os botões ficam no desktop) ---
        if not celular:
            pg.goto(BASE + f"/alunos/{ids['Paula Reis']}")
            pg.click("button[data-open='dlg-acesso'] >> visible=true")
            pg.wait_for_selector("#dlg-acesso[open]", timeout=3000)
            pg.click("#dlg-acesso button[type=submit]")
            pg.wait_for_url(f"**/alunos/{ids['Paula Reis']}", timeout=8000)
            pg.wait_for_timeout(400)
            checa(f"[{nome}] bloquear acesso: o perfil passa a oferecer 'Liberar'", pg.locator("button[data-open='dlg-acesso']:has-text('Liberar') >> visible=true").count() == 1)
            pg.goto(BASE + "/")
            pg.wait_for_selector("[data-open='bloquear-acesso']")
            pg.click("[data-open='bloquear-acesso']")
            pg.wait_for_selector("#bloquear-acesso[open]", timeout=3000)
            pg.fill("#bloquear-acesso input[type=search]", "paula")
            pg.wait_for_function("() => document.querySelector('#resultado-acesso').innerText.includes('Paula Reis')", timeout=5000)
            checa(f"[{nome}] o popup do painel acha o aluno e mostra que está bloqueado", "Acesso bloqueado" in pg.inner_text("#resultado-acesso"))
            pg.click("#resultado-acesso button[type=submit]")
            pg.wait_for_url(f"**/alunos/{ids['Paula Reis']}", timeout=8000)
            pg.wait_for_timeout(400)
            checa(f"[{nome}] liberar pelo popup devolve o acesso", pg.locator("button[data-open='dlg-acesso']:has-text('Bloquear') >> visible=true").count() == 1)

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
