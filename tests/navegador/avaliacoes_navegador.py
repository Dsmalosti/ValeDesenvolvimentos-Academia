"""
Teste da AVALIAÇÃO FÍSICA do front novo num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro): agenda vazia, agendar
(busca do aluno, horário, cobrança, validação da data), aviso e card do painel, o assistente de
quatro etapas (com a prévia de IMC e de cintura/quadril), resultado com a comparação, histórico
com o gráfico e o cartão no perfil do aluno. Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/avaliacoes_navegador.py [pasta-das-fotos]
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
from app.models import Aluno, AvaliacaoFisica, Conta, Plano, User  # noqa: E402
from app.services.avaliacao_service import calcular_imc  # noqa: E402
from tests.navegador._base import CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, sem_none_nem_rolagem  # noqa: E402

EMAIL, SENHA = "marina@valetec.com", "Senha-de-teste-123"
HOJE = date.today()
ANTES = HOJE - timedelta(days=90)
resultados = []
ids = {}


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """Academia sem check-in (o card do painel é o das avaliações). Cada Camila já tem uma avaliação de 90 dias atrás."""
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
        plano = Plano(nome="Mensal", valor=149.90, duracao_dias=30, descricao="", ativo=True, instrutor_id=dona.id, conta_id=conta.id)
        db.session.add(plano)
        db.session.flush()
        for i, nome in enumerate(["Camila Celular", "Camila Desktop", "Nunca Avaliado"]):
            aluno = Aluno(nome=nome, email=f"aluno{i}@exemplo.com", cpf=f"111.222.333-0{i}", telefone="(12) 98211-4400", ativo=True,
                          plano_id=plano.id, instrutor_id=dona.id, conta_id=conta.id)
            db.session.add(aluno)
            db.session.flush()
            ids[nome] = aluno.id
            if nome.startswith("Camila"):
                db.session.add(AvaliacaoFisica(conta_id=conta.id, aluno_id=aluno.id, data=ANTES, avaliador_id=dona.id, peso_kg=71.2, altura_cm=167,
                                               imc=calcular_imc(71.2, 167), cintura_cm=78, braco_d_cm=26.1))
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5102, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5102"

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        camila = "Camila Celular" if celular else "Camila Desktop"
        hora = "14:00" if celular else "15:00"       # a mesma avaliadora não pode ter dois alunos no mesmo horário
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)

        def acionar(seletor):
            pg.locator(seletor).first.scroll_into_view_if_needed()
            (pg.tap if celular else pg.click)(seletor)

        def enviar(seletor):
            """Aciona um botão ou link que troca de página e espera a página nova terminar de carregar."""
            with pg.expect_navigation(wait_until="load", timeout=10000):
                acionar(seletor)

        entrar(pg, BASE, EMAIL, SENHA, celular)

        # ------------------------------------------------------------ agenda (ainda sem nada para hoje)
        pg.goto(BASE + "/avaliacoes")
        texto = pg.inner_text("#conteudo").lower()
        checa(f"[{nome}] agenda nova, sem a aluna deste cenário", pg.locator(".app .main").count() == 1 and camila.lower() not in texto)
        checa(f"[{nome}] agenda: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        if celular:
            checa(f"[{nome}] agenda vazia avisa que não há nada marcado", "nenhuma avaliação agendada" in texto)
            pg.wait_for_timeout(400)
            pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-agenda-vazia.png"), full_page=True)

        # ------------------------------------------------------------ agendar
        enviar("a:has-text('Agendar avaliação') >> visible=true")
        checa(f"[{nome}] agendar começa pela escolha do aluno", "quem vai ser avaliado?" in pg.inner_text("#conteudo").lower() and "Nunca Avaliado" in pg.content())
        pg.fill("input[name=q]", camila.lower())
        with pg.expect_navigation(wait_until="load", timeout=10000):
            pg.press("input[name=q]", "Enter")
        checa(f"[{nome}] a busca acha só a aluna procurada", pg.locator(".mlist .mrow").count() == 1 and camila in pg.inner_text(".mlist"))
        enviar(f".mlist .mrow:has-text('{camila}')")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] formulário com a última avaliação e 'reavaliação' já escolhida", f"Última avaliação: {ANTES.strftime('%d/%m/%Y')}" in texto
              and pg.input_value("#h-tipo-v") == "reavaliacao" and pg.get_attribute("button[data-valor='reavaliacao']", "aria-pressed") == "true")
        checa(f"[{nome}] sem preço cadastrado, a avulsa diz 'cobrada à parte' e a tela não promete lembrete", "cobrada à parte" in texto
              and "R$" not in texto and "Lembretes automáticos" not in texto and pg.inner_text("button[data-e='cta']").strip() == "Agendar avaliação")
        checa(f"[{nome}] agendar: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))

        # data vazia não envia (validação na tela)
        pg.fill("#f-data", "")
        acionar("button[data-e='cta']")
        pg.wait_for_timeout(500)
        checa(f"[{nome}] data vazia não é enviada", "/avaliacoes/agendar" in pg.url and pg.locator(".is-invalid, .field-error").count() >= 1)

        pg.fill("#f-data", HOJE.strftime("%d/%m/%Y"))
        acionar(f"button[data-valor='{hora}']")
        acionar("button[data-valor='inclusa']")
        checa(f"[{nome}] tocar no horário e na cobrança grava a escolha", pg.input_value("#h-horario") == hora and pg.input_value("#h-cobranca") == "inclusa"
              and pg.get_attribute(f"button[data-valor='{hora}']", "aria-pressed") == "true")
        pg.fill("#f-observacao", "Vir em jejum de 3h")
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-agendar.png"), full_page=True)
        enviar("button[data-e='cta']")
        linha = pg.inner_text(f".av-lista li:has-text('{camila}')")
        checa(f"[{nome}] agendada: aparece em 'Hoje', com o botão de iniciar", pg.url.endswith("/avaliacoes") and hora in linha and "Iniciar avaliação" in linha
              and "Reavaliação · 90 dias" in linha, linha)
        checa(f"[{nome}] agenda com item: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-agenda.png"), full_page=True)

        # ------------------------------------------------------------ painel: aviso e card
        # o popup de avisos abre uma vez por sessão do navegador (e já abriu no login): simula uma sessão nova
        pg.evaluate("sessionStorage.removeItem('vt-popup-pop-avisos')")
        pg.goto(BASE + "/")
        pg.wait_for_selector("#pop-avisos[open]", timeout=5000)
        aviso = pg.inner_text("#pop-avisos")
        checa(f"[{nome}] o painel avisa da avaliação de hoje, sem dizer que mandou aviso", camila in aviso and f"Hoje, {hora}" in aviso and "Aviso já enviado" not in aviso, aviso[:200])
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-4-aviso-do-painel.png"))
        acionar("#pop-avisos [data-close]")
        pg.wait_for_timeout(500)
        if celular:
            # no celular o painel não tem os 8 cards de indicador (é do desenho); o caminho é o atalho "Avaliação"
            checa(f"[{nome}] o painel do celular tem o atalho de agendar avaliação", pg.locator("a.qa[href='/avaliacoes/agendar'] >> visible=true").count() == 1)
        else:
            card = pg.locator(".kpi[data-open='dlg-avaliacoes-hoje'] >> visible=true")
            checa(f"[{nome}] card 'Avaliações de hoje' com o número de verdade", card.count() == 1 and card.locator(".kpi__val").inner_text().strip() == "1",
                  card.count())
            acionar(".kpi[data-open='dlg-avaliacoes-hoje'] >> visible=true")
            pg.wait_for_selector("#dlg-avaliacoes-hoje[open]", timeout=3000)
            popup = pg.inner_text("#dlg-avaliacoes-hoje")
            checa(f"[{nome}] o popup lista a avaliação e chama no WhatsApp", camila in popup and f"{hora} · Reavaliação · 90 dias · Confirmada" in popup
                  and pg.locator("#dlg-avaliacoes-hoje a[href='https://wa.me/5512982114400']").count() == 1 and "Camila Duarte" not in popup, popup[:200])
            pg.wait_for_timeout(300)
            pg.screenshot(path=os.path.join(FOTOS, f"{nome}-4b-avaliacoes-de-hoje.png"))
            acionar("#dlg-avaliacoes-hoje [data-close]")
            pg.wait_for_timeout(300)

        # ------------------------------------------------------------ o assistente de quatro etapas
        pg.goto(BASE + "/avaliacoes")
        enviar(f".av-lista li:has-text('{camila}') a:has-text('Iniciar avaliação')")
        checa(f"[{nome}] 'Iniciar avaliação' abre o assistente, na anamnese", "/avaliacoes/nova?ag=" in pg.url and pg.locator("[data-passo]:not([hidden])").count() == 1
              and pg.locator("[data-passo-nome='Anamnese']").is_visible() and not pg.locator(".passos-nav button[type=submit]").is_visible())
        pg.fill("#f-objetivo", "Ganhar força")
        acionar("label.switch")
        pg.wait_for_timeout(200)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-5-anamnese.png"), full_page=True)
        acionar(".passos-nav [data-prox]")
        pg.wait_for_timeout(500)
        checa(f"[{nome}] etapa de medidas: a altura vem da avaliação anterior e o peso não", pg.locator("[data-passo-nome='Medidas']").is_visible()
              and pg.input_value("#f-altura_cm") == "167" and pg.input_value("#f-peso_kg") == "")
        checa(f"[{nome}] a tela não pede fotos (ainda não são guardadas)", pg.locator("input[type=file]").count() == 0 and "Fotos de acompanhamento" not in pg.content())
        acionar(".passos-nav [data-prox]")
        pg.wait_for_timeout(400)
        checa(f"[{nome}] sem peso não passa de etapa", pg.locator("[data-passo-nome='Medidas']").is_visible())
        pg.fill("#f-peso_kg", "68,4")
        pg.fill("#f-cintura_cm", "72")
        pg.fill("#f-quadril_cm", "96,5")
        pg.fill("#f-braco_d_cm", "25")
        pg.wait_for_timeout(300)
        checa(f"[{nome}] prévia do IMC e da relação cintura/quadril", pg.inner_text("[data-imc-previa]").strip() == "24,5" and pg.inner_text("[data-rcq-previa]").strip() == "0,75")
        checa(f"[{nome}] medidas: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-6-medidas.png"), full_page=True)
        acionar(".passos-nav [data-prox]")
        pg.wait_for_timeout(500)
        pg.fill("#f-dobra_triceps", "12,5")
        acionar(".passos-nav [data-prox]")
        pg.wait_for_timeout(500)
        checa(f"[{nome}] na última etapa aparece o 'Salvar avaliação'", pg.locator("[data-passo-nome='Testes']").is_visible()
              and pg.locator(".passos-nav button[type=submit]").is_visible() and not pg.locator(".passos-nav [data-prox]").is_visible())
        pg.fill("#f-teste_flexao", "22")
        pg.fill("textarea[name=anotacao]", "Boa aderência ao treino.")
        pg.wait_for_timeout(200)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-7-testes.png"), full_page=True)
        enviar(".passos-nav button[type=submit]")

        # ------------------------------------------------------------ resultado
        texto = pg.inner_text("#conteudo")
        baixo = texto.lower()
        checa(f"[{nome}] resultado com a comparação de 90 dias", "avaliação registrada" in baixo and "o que mudou em 90 dias" in baixo
              and f"comparado com {ANTES.strftime('%d/%m/%Y')}" in baixo and "boa aderência ao treino." in baixo, texto[:300])
        tabela = pg.inner_text("table.cmp")
        checa(f"[{nome}] a tabela mostra antes, agora e a variação", "71,2" in tabela and "68,4" in tabela and "-2,8" in tabela and "-6,0" in tabela and "-1,1" in tabela, tabela)
        checa(f"[{nome}] variação pintada: peso e cintura a favor, braço contra", pg.locator("table.cmp td.tone-txt-teal").count() == 3
              and pg.locator("table.cmp td.tone-txt-red").count() == 1)
        link = pg.get_attribute("a:has-text('Enviar')", "href") or ""
        checa(f"[{nome}] 'Enviar' abre o WhatsApp da aluna com o resultado escrito", link.startswith("https://wa.me/5512982114400?text=Oi%20Camila%21") and "68%2C4%20kg" in link, link[:80])
        checa(f"[{nome}] resultado: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-8-resultado.png"), full_page=True)

        # ------------------------------------------------------------ histórico, perfil e agenda depois
        pg.goto(BASE + f"/alunos/{ids[camila]}/avaliacoes")
        pg.wait_for_selector("[data-chart='linha'] svg", timeout=5000)
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] histórico com o gráfico do peso e as duas avaliações", pg.locator(".mlist .mrow").count() == 2 and "2 avaliações · −2,8 kg no período" in texto
              and "68,4 kg" in texto and "IMC 24,5" in texto, texto[:200])
        checa(f"[{nome}] histórico: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(700)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-9-historico.png"), full_page=True)

        pg.goto(BASE + f"/alunos/{ids[camila]}")
        cartao = pg.inner_text(".card--aval")
        checa(f"[{nome}] o perfil da aluna mostra a última avaliação, em dia", f"Última: {HOJE.strftime('%d/%m/%Y')}" in cartao and "68,4 kg · IMC 24,5" in cartao
              and "em dia" in cartao.lower(), cartao)
        pg.goto(BASE + f"/alunos/{ids['Nunca Avaliado']}")
        checa(f"[{nome}] quem nunca foi avaliado não tem o cartão", pg.locator(".card--aval").count() == 0)
        pg.goto(BASE + f"/alunos/{ids['Nunca Avaliado']}/avaliacoes")
        checa(f"[{nome}] histórico vazio convida a agendar", "ainda sem avaliações" in pg.inner_text("#conteudo").lower())

        pg.goto(BASE + "/avaliacoes")
        checa(f"[{nome}] depois de feita, a avaliação sai da agenda", camila not in pg.inner_text("#conteudo"))

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
