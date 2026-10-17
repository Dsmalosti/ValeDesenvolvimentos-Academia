"""
Teste dos EXERCÍCIOS e das FICHAS DE TREINO do front novo num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro): catálogo de exercícios
(lista, carregar mais, busca, filtro por grupo, detalhe, novo, editar), modelos prontos, usar um
modelo com um aluno, editor da ficha (ajustar, adicionar pelo catálogo, tirar, criar treino,
salvar, excluir) e a tela de enviar pelo WhatsApp. Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/treinos_navegador.py [pasta-das-fotos]
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
from app.models import Aluno, Conta, Exercicio, Plano, User  # noqa: E402
from app.services import treino_service  # noqa: E402
from tests.navegador._base import CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, sem_none_nem_rolagem  # noqa: E402

EMAIL, SENHA = "marina@valetec.com", "Senha-de-teste-123"
resultados = []
ids = {}


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """Academia com o catálogo padrão no banco e quatro alunos: um por cenário, um sem ficha e um inativo."""
    app = create_app()
    assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
    with app.app_context():
        db.create_all()
        treino_service.semear_catalogo_padrao()
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
        for i, nome in enumerate(["Camila Celular", "Camila Desktop", "Sem Ficha", "Caio Inativo"]):
            aluno = Aluno(nome=nome, email=f"aluno{i}@exemplo.com", cpf=f"111.222.333-0{i}", telefone="(12) 98211-4400", ativo=nome != "Caio Inativo",
                          plano_id=plano.id, instrutor_id=dona.id, conta_id=conta.id)
            db.session.add(aluno)
            db.session.flush()
            ids[nome] = aluno.id
        db.session.commit()
        ids["Supino reto"] = Exercicio.query.filter_by(nome="Supino reto").one().id
        ids["total"] = Exercicio.query.count()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5101, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5101"

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        camila = "Camila Celular" if celular else "Camila Desktop"
        meu = "Remada na fita celular" if celular else "Remada na fita desktop"
        ja = 0 if celular else 1        # o cenário do desktop roda depois do celular, que já criou um exercício
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)

        def acionar(seletor):
            pg.locator(seletor).first.scroll_into_view_if_needed()
            (pg.tap if celular else pg.click)(seletor)

        def enviar(seletor):
            """Aciona um botão ou link que troca de página e espera a página nova terminar de carregar."""
            with pg.expect_navigation(wait_until="load", timeout=10000):
                acionar(seletor)

        def cartoes():
            """Quantos exercícios a lista do catálogo mostra (lista no celular, grade de vídeos no desktop)."""
            return pg.locator(".m-only .mlist .mrow" if celular else ".ex-grid .ex-card").count()

        def linhas():
            """Os exercícios do treino aberto no editor da ficha (cartões no celular, tabela no desktop)."""
            return pg.locator(".m-only .fx-card" if celular else ".dtable tbody tr").all_inner_texts()

        entrar(pg, BASE, EMAIL, SENHA, celular)

        # ------------------------------------------------------------ catálogo de exercícios
        pg.goto(BASE + "/exercicios")
        checa(f"[{nome}] /exercicios abre a tela nova, com 8 exercícios", pg.locator(".app .main").count() == 1 and cartoes() == 8, cartoes())
        checa(f"[{nome}] catálogo: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        checa(f"[{nome}] mostra o total do catálogo", f"de {ids['total'] + ja} exercícios" in pg.inner_text("#conteudo"))
        pg.wait_for_timeout(500)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-exercicios.png"), full_page=True)
        enviar(".ex-mais a:has-text('Carregar mais')")
        checa(f"[{nome}] 'Carregar mais' traz mais 8", cartoes() == 16 and "limite=16" in pg.url, cartoes())

        pg.fill("input[name=q] >> visible=true", "supino")
        with pg.expect_navigation(wait_until="load", timeout=10000):
            pg.press("input[name=q] >> visible=true", "Enter")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] a busca acha pelo nome", "Supino reto" in texto and "Rosca direta" not in texto and 0 < cartoes() < 8, cartoes())
        pg.goto(BASE + "/exercicios")
        enviar("nav.pills a.pill:has-text('Bíceps')")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] o filtro por grupo mostra só o grupo", "Rosca direta" in texto and "Supino reto" not in texto
              and pg.locator("nav.pills a.pill[aria-current='true']").inner_text().strip() == "Bíceps")

        pg.goto(BASE + "/exercicios?q=supino+reto")
        enviar((".m-only .mlist .mrow" if celular else ".ex-grid .ex-card") + ":has-text('Supino reto')")
        texto = pg.inner_text("#conteudo").lower()
        checa(f"[{nome}] detalhe do exercício", pg.url.endswith(f"/exercicios/{ids['Supino reto']}") and "como executar" in texto
              and "músculos trabalhados" in texto and "sem vídeo ainda" in texto and sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-exercicio.png"), full_page=True)
        enviar("a:has-text('Editar exercício') >> visible=true")
        checa(f"[{nome}] exercício do catálogo padrão não abre para edição", pg.url.endswith(f"/exercicios/{ids['Supino reto']}"))

        # --- novo exercício da academia ---
        pg.goto(BASE + "/exercicios/novo")
        acionar("#conteudo form[data-validate] button[type=submit]")
        pg.wait_for_timeout(500)
        checa(f"[{nome}] formulário vazio não é enviado (validação na tela)", pg.url.endswith("/exercicios/novo") and pg.locator(".is-invalid, .field-error").count() >= 1)
        pg.fill("#f-nome", meu)
        pg.select_option("#f-grupo_muscular", "Costas")
        pg.fill("#f-equipamento", "Fita")
        pg.fill("#f-video_url", "https://youtu.be/abc123")
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-novo-exercicio.png"), full_page=True)
        enviar("#conteudo form[data-validate] button[type=submit]")
        checa(f"[{nome}] salvar leva de volta ao catálogo", pg.url.endswith("/exercicios"))
        pg.goto(BASE + "/exercicios?q=remada+na+fita")
        checa(f"[{nome}] o exercício novo aparece no catálogo da academia", meu in pg.inner_text("#conteudo") and cartoes() == 1 + ja, cartoes())
        enviar((".m-only .mlist .mrow" if celular else ".ex-grid .ex-card") + f":has-text('{meu}')")
        checa(f"[{nome}] o detalhe dele tem o link do vídeo", pg.locator("a.ex-video[href='https://youtu.be/abc123']").count() == 1)
        enviar("a:has-text('Editar exercício') >> visible=true")
        checa(f"[{nome}] o exercício da academia abre para edição, já preenchido", pg.url.endswith("/editar") and pg.input_value("#f-nome") == meu
              and pg.input_value("#f-grupo_muscular") == "Costas" and pg.input_value("#f-equipamento") == "Fita")

        # ------------------------------------------------------------ modelos prontos
        pg.goto(BASE + "/treinos")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] biblioteca com os 5 modelos prontos", pg.locator(".modelos-grid .mrow-card").count() == 5 and "Hipertrofia" in texto and "Iniciante" in texto)
        checa(f"[{nome}] biblioteca: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-4-biblioteca.png"), full_page=True)
        enviar(".modelos-grid .mrow-card:has-text('Hipertrofia')")
        checa(f"[{nome}] tela do modelo com o Treino A", "Supino reto" in pg.inner_text("#conteudo") and pg.locator(".tab-treino").count() == 3)
        enviar(".tab-treino:has-text('Treino B')")
        checa(f"[{nome}] a aba troca de treino", "Agachamento livre" in pg.inner_text("#conteudo") and pg.locator(".tab-treino[aria-current='true']").inner_text().strip() == "Treino B")
        enviar("a:has-text('Usar com um aluno')")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] escolher aluno: só os ativos", camila in texto and "Sem Ficha" in texto and "Caio Inativo" not in texto and sem_none_nem_rolagem(pg))
        acionar(f"label.mrow.check:has-text('{camila}')")
        checa(f"[{nome}] tocar na linha marca o aluno", pg.locator(f"input[name=aluno_id][value='{ids[camila]}']").is_checked())
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-5-atribuir.png"), full_page=True)
        enviar("button[name=acao][value=ajustar]")

        # ------------------------------------------------------------ editor da ficha
        checa(f"[{nome}] 'Ajustar antes de enviar' abre a ficha do aluno", pg.url.endswith(f"/alunos/{ids[camila]}/ficha"))
        antes = linhas()
        checa(f"[{nome}] a ficha nasce com os 6 exercícios do Treino A do modelo", len(antes) == 6 and "Supino reto" in antes[0], antes[:2])
        checa(f"[{nome}] ficha: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-6-ficha.png"), full_page=True)

        # ajustar séries e carga
        acionar("button[aria-label='Ajustar Supino reto'] >> visible=true")
        pg.wait_for_selector("#dlg-ex-0[open]", timeout=3000)
        pg.wait_for_timeout(400)
        pg.fill("#dlg-ex-0 input[name=series]", "5")
        pg.fill("#dlg-ex-0 input[name=carga]", "40 kg")
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-7-ajustar-exercicio.png"))
        enviar("#dlg-ex-0 button[type=submit]")
        primeira = linhas()[0]
        checa(f"[{nome}] ajustar o exercício grava séries e carga", "40 kg" in primeira and ("5 séries" in primeira if celular else "\t5\t" in primeira), primeira)

        # adicionar pelo catálogo (popup no celular, coluna ao lado no desktop)
        sufixo = "m" if celular else "d"
        if celular:
            acionar("button[data-open='dlg-catalogo']")
            pg.wait_for_selector("#dlg-catalogo[open]", timeout=3000)
            pg.wait_for_timeout(400)
        pg.fill(f"#f-cat-busca-{sufixo}", "prancha")
        pg.wait_for_timeout(500)
        visiveis = pg.locator(f"#lista-cat-{sufixo} .cat-item >> visible=true").all_inner_texts()
        checa(f"[{nome}] a busca do catálogo filtra na hora", 0 < len(visiveis) <= 3 and all("prancha" in v.lower() for v in visiveis), visiveis[:4])
        if celular:
            pg.screenshot(path=os.path.join(FOTOS, f"{nome}-8-catalogo.png"))
        enviar(f"#lista-cat-{sufixo} .cat-item[data-nome='Prancha'] button[type=submit]")
        depois = linhas()
        checa(f"[{nome}] o + joga o exercício no fim do treino aberto", len(depois) == 7 and "Prancha" in depois[-1], depois[-1:])

        # tirar um exercício
        enviar("button[aria-label='Tirar Crucifixo inclinado do treino'] >> visible=true")
        depois = linhas()
        checa(f"[{nome}] tirar um exercício remove só ele", len(depois) == 6 and not any("Crucifixo inclinado" in l for l in depois) and "Supino reto" in depois[0])

        # criar o Treino D
        enviar("button[aria-label='Criar Treino D']")
        checa(f"[{nome}] o + das abas cria o Treino D, vazio", pg.url.endswith("?t=D") and pg.locator(".tab-treino:not(.tab-treino--add)").count() == 4 and linhas() == [])

        # salvar tira do rascunho (o botão "Salvar ficha" só existe no celular)
        pg.goto(BASE + "/treinos")
        checa(f"[{nome}] a ficha aparece na biblioteca como rascunho", f"{camila}" in pg.inner_text(".mlist") and "rascunho" in pg.inner_text(f".mlist li:has-text('{camila}')"))
        if celular:
            pg.goto(BASE + f"/alunos/{ids[camila]}/ficha")
            enviar("button:has-text('Salvar ficha')")
            pg.goto(BASE + "/treinos")
            checa(f"[{nome}] 'Salvar ficha' tira do rascunho", "rascunho" not in pg.inner_text(f".mlist li:has-text('{camila}')"))

        # o perfil do aluno mostra a ficha
        pg.goto(BASE + f"/alunos/{ids[camila]}")
        checa(f"[{nome}] o perfil do aluno mostra os treinos da ficha", "Treino A" in pg.content() and "Treino D" in pg.content())

        # ------------------------------------------------------------ enviar pelo WhatsApp
        pg.goto(BASE + f"/alunos/{ids[camila]}/ficha/enviar")
        link = pg.get_attribute("a:has-text('Abrir no WhatsApp')", "href") or ""
        bolha = pg.inner_text(".wa-bolha")
        checa(f"[{nome}] o botão abre o WhatsApp do aluno com o texto pronto", link.startswith("https://wa.me/5512982114400?text=Oi%20Camila"), link[:70])
        checa(f"[{nome}] a prévia mostra a mensagem com os exercícios", "Oi Camila!" in bolha and "Supino reto: 5 x 10" in bolha and "40 kg" in bolha, bolha[:200])
        # [back-31-pdf-ficha-avaliacao] antes: só o Texto estava disponível. Agora o PDF vem escolhido e a imagem continua desligada
        checa(f"[{nome}] o PDF vem escolhido (imagem desligada)", pg.locator("button[data-valor='imagem']").is_disabled()
              and pg.get_attribute("button[data-valor='pdf']", "aria-pressed") == "true" and pg.locator("a:has-text('Enviar o PDF')").is_visible()
              and not pg.locator("a:has-text('Abrir no WhatsApp')").is_visible() and not pg.locator(".ficha-img").is_visible())
        pdf = ctx.request.get(BASE + f"/alunos/{ids[camila]}/ficha/pdf")
        checa(f"[{nome}] 'Enviar o PDF' aponta para um PDF de verdade", pdf.status == 200 and pdf.headers["content-type"] == "application/pdf"
              and pdf.body().startswith(b"%PDF-1.4"))
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-9a-enviar-pdf.png"), full_page=True)
        acionar("button[data-valor='texto']")
        checa(f"[{nome}] escolhendo Texto, volta o botão do WhatsApp", pg.locator("a:has-text('Abrir no WhatsApp')").is_visible()
              and not pg.locator("a:has-text('Enviar o PDF')").is_visible())
        checa(f"[{nome}] enviar: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        arquivo = ctx.request.get(BASE + f"/alunos/{ids[camila]}/ficha/baixar")
        checa(f"[{nome}] 'Baixar a ficha em texto' devolve o arquivo", arquivo.status == 200 and "TREINO A" in arquivo.text() and camila in arquivo.text())
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-9-enviar.png"), full_page=True)

        # ------------------------------------------------------------ quem não tem ficha, e excluir
        pg.goto(BASE + f"/alunos/{ids['Sem Ficha']}/ficha")
        checa(f"[{nome}] aluno sem ficha: vai para a biblioteca escolher um modelo", pg.url.endswith("/treinos"))

        pg.goto(BASE + f"/alunos/{ids[camila]}/ficha")
        acionar("button[data-open='dlg-excluir-ficha'] >> visible=true")
        pg.wait_for_selector("#dlg-excluir-ficha[open]", timeout=3000)
        pg.wait_for_timeout(400)
        checa(f"[{nome}] excluir pede confirmação e avisa que não tem volta", "não dá para desfazer" in pg.inner_text("#dlg-excluir-ficha").lower())
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-10-excluir.png"))
        enviar("#dlg-excluir-ficha button[type=submit]")
        checa(f"[{nome}] excluir apaga a ficha e volta à biblioteca", pg.url.endswith("/treinos") and camila not in pg.inner_text("section[aria-labelledby='h-fa']"))

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
