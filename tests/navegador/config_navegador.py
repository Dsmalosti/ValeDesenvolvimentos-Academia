"""
Teste das CONFIGURAÇÕES do front novo num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro): menu de seções, dados da academia, ligar o check-in pelo
interruptor, modelo de mensagem e metas. Desktop (1440 px, tema escuro): abas, dados, horário,
mensagem, prazo de inatividade, metas (com erro e certas) e a tela de recebimento. Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/config_navegador.py [pasta-das-fotos]
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
from tests.navegador._base import (CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, pagamento_recebido,  # noqa: E402
                                   sem_none_nem_rolagem)

SENHA = "Senha-de-teste-123"
HOJE = date.today()
resultados = []


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """Duas academias iguais (uma para cada cenário), cada uma com a dona, uma recepcionista, um aluno e um pagamento."""
    app = create_app()
    assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
    with app.app_context():
        db.create_all()
        for cenario in ("celular", "desktop"):
            conta = Conta(nome=f"Academia do {cenario.title()}")
            db.session.add(conta)
            db.session.flush()
            dona = User(nome="Marina", sobrenome="Albuquerque", email=f"marina-{cenario}@valetec.com", ativo=True, conta_id=conta.id,
                        senha=bcrypt.generate_password_hash(SENHA).decode("utf-8"))
            db.session.add_all([dona, User(nome="Juliana", sobrenome="Castro", email=f"juliana-{cenario}@valetec.com", ativo=True, conta_id=conta.id,
                                           papel="recepcao", senha=bcrypt.generate_password_hash(SENHA).decode("utf-8"))])
            db.session.flush()
            plano = Plano(nome="Mensal", valor=150, duracao_dias=30, descricao="", ativo=True, instrutor_id=dona.id, conta_id=conta.id)
            db.session.add(plano)
            db.session.flush()
            aluno = Aluno(nome="Camila Duarte", email=f"camila-{cenario}@exemplo.com", cpf="111.222.333-00", telefone="(12) 98211-4400", ativo=True,
                          plano_id=plano.id, instrutor_id=dona.id, conta_id=conta.id)
            db.session.add(aluno)
            db.session.flush()
            pagamento_recebido(db, aluno, dona, 150, HOJE, HOJE + timedelta(days=30), forma="pix")
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5099, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5099"

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        cenario = "celular" if celular else "desktop"
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)

        def acionar(seletor):
            pg.locator(seletor).first.scroll_into_view_if_needed()
            (pg.tap if celular else pg.click)(seletor)

        def enviar(seletor):
            """Aciona um botão que envia formulário e espera a página nova terminar de carregar.
            (Várias telas voltam para o MESMO endereço depois de salvar: esperar pela URL não basta.)"""
            with pg.expect_navigation(wait_until="load", timeout=10000):
                acionar(seletor)

        entrar(pg, BASE, f"marina-{cenario}@valetec.com", SENHA, celular)

        # --- abrir ---
        if celular:
            pg.goto(BASE + "/configuracoes")
            texto = pg.inner_text("#conteudo")
            checa(f"[{nome}] no celular abre o menu de seções", "Dados e endereço" in texto and "Serviço de check-in" in texto and "Modelos de WhatsApp" in texto)
            pg.wait_for_timeout(500)
            pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-menu.png"), full_page=True)
            pg.tap("a.set-row:has-text('Dados e endereço')")
            pg.wait_for_url("**/configuracoes?aba=academia", timeout=6000)
        else:
            pg.click(".rail .navicon[aria-label='Configurações']")
            pg.wait_for_url("**/configuracoes", timeout=6000)
            checa(f"[{nome}] no desktop abre a aba Academia, com a equipe e os modelos de mensagem",
                  pg.locator(".cfg-tabs a[aria-current='true']").inner_text() == "Academia"
                  and "Juliana Castro" in pg.inner_text("#conteudo") and "Cobrança de mensalidade" in pg.inner_text("#conteudo"))
            pg.wait_for_timeout(500)
            pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-academia.png"), full_page=True)
        checa(f"[{nome}] sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg) and pg.input_value("#form-academia [name=cnpj]") == "")

        # --- dados da academia ---
        novo_nome = f"Corpo em Movimento {cenario.title()}"
        pg.fill("#form-academia [name=nome]", novo_nome)
        pg.fill("#form-academia [name=cidade]", "Tremembé / SP")
        enviar("#form-academia button[type=submit]" if celular else "button[form='form-academia']")
        checa(f"[{nome}] dados salvos voltam preenchidos", pg.url.endswith("/configuracoes?aba=academia")
              and pg.input_value("#form-academia [name=nome]") == novo_nome and pg.input_value("#form-academia [name=cidade]") == "Tremembé / SP")

        if celular:
            # --- interruptor do check-in, no menu ---
            pg.goto(BASE + "/configuracoes")
            checa(f"[{nome}] o menu passa a mostrar o nome novo da academia", novo_nome in pg.inner_text("#conteudo"))
            checa(f"[{nome}] antes de ligar, a gaveta não tem o atalho de check-in", pg.locator("#gaveta a[href='/frequencia']").count() == 0)
            pg.locator("form.set-row:has-text('Serviço de check-in') label.switch").scroll_into_view_if_needed()
            with pg.expect_navigation(wait_until="load", timeout=10000):
                pg.tap("form.set-row:has-text('Serviço de check-in') label.switch")
            checa(f"[{nome}] ligar o check-in pelo interruptor persiste e o atalho aparece", pg.locator("#gaveta a[href='/frequencia']").count() == 1
                  and pg.locator("form.set-row:has-text('Serviço de check-in') input[type=checkbox]").first.is_checked())
        else:
            # --- horário ---
            pg.click("button[data-open='dlg-horario']")
            pg.wait_for_selector("#dlg-horario[open]", timeout=3000)
            for campo, valor in (("semana", "06h - 22h"), ("sabado", "08h - 14h"), ("domingo", "Fechado")):
                pg.fill(f"#dlg-horario [name={campo}]", valor)
            enviar("#dlg-horario button[type=submit]")
            checa(f"[{nome}] horário salvo aparece na tela", "06h - 22h" in pg.inner_text("#horario") and "Não informado" not in pg.inner_text("#horario"))

            # --- cobrança: prazo da inatividade ---
            pg.click(".cfg-tabs a:has-text('Cobrança')")
            pg.wait_for_url("**/configuracoes?aba=cobranca", timeout=6000)
            pg.fill("form.set-row [name=dias]", "45")
            enviar("form.set-row:has([name=dias]) button[type=submit]")
            checa(f"[{nome}] prazo da inatividade automática salvo", pg.input_value("form.set-row [name=dias]") == "45")
            pg.click(".cfg-tabs a:has-text('Integrações')")
            pg.wait_for_url("**/configuracoes?aba=integracoes", timeout=6000)
            checa(f"[{nome}] aba Integrações mostra o PIX automático como desligado", "Desligado" in pg.inner_text("#conteudo"))

        # --- modelo de mensagem ---
        pg.goto(BASE + "/configuracoes?aba=mensagens")
        acionar("button[data-open='dlg-msg-sumido']")
        pg.wait_for_selector("#dlg-msg-sumido[open]", timeout=3000)
        pg.fill("#dlg-msg-sumido textarea", f"Oi [nome], faz [dias] dias! Volta pra gente ({cenario}).")
        enviar("#dlg-msg-sumido button[type=submit]")
        checa(f"[{nome}] modelo de mensagem alterado aparece; os outros continuam no padrão",
              f"Volta pra gente ({cenario})." in pg.inner_text("#conteudo") and "Parabéns, [nome]!" in pg.inner_text("#conteudo"))

        # --- metas ---
        pg.goto(BASE + "/configuracoes?aba=metas")
        checa(f"[{nome}] metas vazias não mostram 'None'", pg.input_value("#f-alunos_ativos") == "" and pg.input_value("#f-faturamento") == "")
        if not celular:
            pg.evaluate("document.querySelector('form[action$=\"/configuracoes/metas\"]').setAttribute('novalidate', '')")
            pg.fill("#f-alunos_ativos", "250")
            pg.fill("#f-faturamento", "100000")
            pg.evaluate("document.querySelector('#f-retencao').value = '150'; document.querySelector('form[action$=\"/configuracoes/metas\"]').removeAttribute('data-validate')")
            with pg.expect_navigation(wait_until="load", timeout=10000):
                pg.evaluate("document.querySelector('form[action$=\"/configuracoes/metas\"]').submit()")   # passa por cima da conferência do navegador
            checa(f"[{nome}] meta inválida: o SERVIDOR recusa e devolve o que foi digitado",
                  "A retenção vai de 1% a 100%." in pg.inner_text("#conteudo") and pg.input_value("#f-alunos_ativos") == "250")
        pg.fill("#f-alunos_ativos", "250")
        pg.fill("#f-faturamento", "60000")                                     # a máscara transforma em 600,00
        pg.fill("#f-retencao", "70")
        enviar("form[action$='/configuracoes/metas'] button[type=submit]")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] metas salvas voltam preenchidas, com quanto falta", pg.input_value("#f-faturamento") == "600,00" and "25% da meta" in texto, texto[:200])
        pg.wait_for_timeout(500)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-metas.png"), full_page=True)
        pg.goto(BASE + "/")
        pg.wait_for_selector(".m-only .kpi" if celular else ".d-only .kpi")
        checa(f"[{nome}] o painel passa a mostrar a meta de faturamento", "meta" in pg.inner_text("#conteudo").lower() and "None" not in pg.inner_text("#conteudo"))

        # --- recebimento ---
        pg.goto(BASE + "/configuracoes/recebimento")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] recebimento mostra de onde veio cada confirmação do mês", "1 pagamentos recebidos" in texto and "PIX, na mão" in texto and "None" not in texto)
        enviar("button:has-text('Ligar PIX')")
        checa(f"[{nome}] 'Ligar PIX' avisa que ainda não existe e não liga", pg.locator("button:has-text('Ligar PIX')").count() == 1)

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
