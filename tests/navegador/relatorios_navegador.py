"""
Teste do PAINEL ADMINISTRATIVO do front novo num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro): a tela com dados,
trocar o período, cadastrar, editar e remover custo fixo (o ponto de equilíbrio muda), filtrar
os lançamentos e baixar o CSV. Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/relatorios_navegador.py [pasta-das-fotos]
"""
import os
import sys
import tempfile
import threading
from datetime import date, datetime, timedelta

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
from app.models import Aluno, Cobranca, Conta, Custo, Frequencia, Plano, User  # noqa: E402
from tests.navegador._base import (CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, pagamento_recebido,  # noqa: E402
                                   sem_none_nem_rolagem)

EMAIL, SENHA = "marina@valetec.com", "Senha-de-teste-123"
HOJE = date.today()
resultados = []


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """Academia com check-in ligado, um custo fixo, pagamentos em três formas, uma cobrança em atraso e histórico de alunos."""
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
        plano = Plano(nome="Mensal", valor=150, duracao_dias=30, descricao="", ativo=True, instrutor_id=dona.id, conta_id=conta.id)
        db.session.add(plano)
        db.session.add(Custo(conta_id=conta.id, descricao="Aluguel", valor=200))
        db.session.flush()
        alunos = {}
        for i, nome in enumerate(["Camila Duarte", "Bruno Dias", "Paula Reis", "Larissa Atrasada", "Diego Saiu"]):
            alunos[nome] = Aluno(nome=nome, email=f"aluno{i}@exemplo.com", cpf=f"111.222.333-0{i}", telefone="(12) 98211-4400", ativo=True,
                                 data_cadastro=datetime.now() - timedelta(days=200), plano_id=plano.id, instrutor_id=dona.id, conta_id=conta.id)
            db.session.add(alunos[nome])
        db.session.flush()
        alunos["Diego Saiu"].ativo = False                                   # ficou 120 dias e saiu
        alunos["Diego Saiu"].data_inativacao = datetime.now() - timedelta(days=80)
        pagamento_recebido(db, alunos["Camila Duarte"], dona, 150, HOJE, HOJE + timedelta(days=30), forma="pix")
        pagamento_recebido(db, alunos["Bruno Dias"], dona, 150, HOJE, HOJE + timedelta(days=30), forma="credito")
        pagamento_recebido(db, alunos["Paula Reis"], dona, 100, HOJE, HOJE + timedelta(days=30), forma="dinheiro")
        pagamento_recebido(db, alunos["Camila Duarte"], dona, 150, HOJE - timedelta(days=45), HOJE - timedelta(days=15), forma="pix")
        pagamento_recebido(db, alunos["Larissa Atrasada"], dona, 150, HOJE - timedelta(days=60), HOJE - timedelta(days=30))   # venceu há 30 dias
        db.session.add(Cobranca(conta_id=conta.id, aluno_id=alunos["Larissa Atrasada"].id, plano_id=plano.id, tipo="renovacao", valor=150,
                                data_inicio=HOJE - timedelta(days=30), data_vencimento=HOJE, status="pendente", instrutor_id=dona.id))
        for dias in (1, 3, 8):
            db.session.add(Frequencia(conta_id=conta.id, aluno_id=alunos["Camila Duarte"].id, origem="recepcao", instrutor_id=dona.id,
                                      data_hora_entrada=datetime(HOJE.year, HOJE.month, HOJE.day, 18, 20) - timedelta(days=dias)))
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5098, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5098"

with sync_playwright() as p:
    nav = p.chromium.launch()
    for n_cenario, (nome, opts, tema) in enumerate(CENARIOS):
        celular = opts.get("has_touch", False)
        custo_novo = "Energia Celular" if celular else "Energia Desktop"
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)

        def acionar(seletor):
            pg.locator(seletor).first.scroll_into_view_if_needed()
            (pg.tap if celular else pg.click)(seletor)

        entrar(pg, BASE, EMAIL, SENHA, celular)

        # --- a tela ---
        if celular:
            pg.goto(BASE + "/relatorios/painel")
        else:
            pg.click(".rail .navicon[aria-label='Administrativo']")
            pg.wait_for_url("**/relatorios/painel", timeout=6000)
        pg.wait_for_selector("[data-chart='barras'] svg", timeout=5000)
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] painel administrativo novo, com o faturamento do mês por forma", pg.locator(".app .main").count() == 1
              and "R$ 400 recebidos em" in texto and "PIX" in texto and "Cartão" in texto and "Dinheiro" in texto)
        checa(f"[{nome}] ponto de equilíbrio contra o custo cadastrado", "R$ 200 acima do mínimo" in texto and "Aluguel" in texto)
        checa(f"[{nome}] gráficos desenhados (receita e retenção) e mapa de movimento", pg.locator("[data-chart='barras'] svg").count() == 1
              and pg.locator("[data-chart='linha'] svg").count() == 1 and pg.locator(".heat .heat__c").count() == 42)
        checa(f"[{nome}] aluno em atraso aparece em 'quem está mais perto de cancelar'", "Larissa Atrasada" in pg.inner_text(".risco"))
        checa(f"[{nome}] lançamentos mostram pagos e em atraso", pg.locator("text=Em atraso >> visible=true").count() >= 1 and pg.locator("text=Pago >> visible=true").count() >= 3)
        checa(f"[{nome}] sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(900)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-painel.png"), full_page=True)

        # --- trocar o período ---
        acionar(".pills a.pill:has-text('3 meses')" if celular else ".seg a.seg__btn:has-text('Últimos 3 meses')")
        pg.wait_for_url("**/relatorios/painel?periodo=3m", timeout=6000)
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] período de 3 meses soma o pagamento antigo e triplica o custo",
              "R$ 700 recebidos nos últimos 3 meses" in texto and "R$ 100 acima do mínimo" in texto, texto[:300])
        pg.goto(BASE + "/relatorios/painel")

        # --- custos: criar, ver o ponto de equilíbrio mudar, editar e remover ---
        acionar("button[data-open='dlg-custo-novo']")
        pg.wait_for_selector("#dlg-custo-novo[open]", timeout=3000)
        pg.fill("#dlg-custo-novo [name=descricao]", custo_novo)
        pg.fill("#dlg-custo-novo [name=valor]", "30000")                     # a máscara transforma em 300,00
        acionar("#dlg-custo-novo button[type=submit]:has-text('Salvar')")
        pg.wait_for_url("**/relatorios/painel#custos", timeout=8000)
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] custo novo entra na lista e o ponto de equilíbrio passa a faltar", custo_novo in texto and "R$ 100 abaixo do mínimo" in texto, texto[:200])
        acionar(f".custos li:has-text('{custo_novo}') button")
        pg.wait_for_selector("dialog[open] [name=descricao]", timeout=3000)
        aberto = "dialog[open]"
        checa(f"[{nome}] editar custo vem preenchido", pg.input_value(f"{aberto} [name=descricao]") == custo_novo and pg.input_value(f"{aberto} [name=valor]") == "300,00")
        acionar(f"{aberto} button:has-text('Remover')")
        # o endereço não muda (já era ...#custos): espera o custo sumir da lista
        pg.wait_for_selector(f".custos li:has-text('{custo_novo}')", state="detached", timeout=8000)
        pg.wait_for_load_state("load")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] remover custo devolve o ponto de equilíbrio", custo_novo not in texto and "R$ 200 acima do mínimo" in texto)

        # --- filtrar os lançamentos ---
        acionar("button[data-open='dlg-filtro']")
        pg.wait_for_selector("#dlg-filtro[open]", timeout=3000)
        pg.select_option("#dlg-filtro [name=forma]", "PIX")
        acionar("#dlg-filtro button[type=submit]")
        pg.wait_for_url("**forma=PIX**", timeout=8000)
        lanc = pg.inner_text("section[aria-labelledby='h-lanc']")
        checa(f"[{nome}] filtro por forma deixa só os lançamentos em PIX", "Camila Duarte" in lanc and "Bruno Dias" not in lanc and "Paula Reis" not in lanc)

        planilha = ctx.request.get(BASE + "/relatorios/exportar?formato=csv&forma=PIX")
        checa(f"[{nome}] exportar devolve a planilha com o mesmo filtro", planilha.status == 200 and "Camila Duarte" in planilha.text() and "Bruno Dias" not in planilha.text())
        pg.wait_for_timeout(500)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-filtrado.png"), full_page=True)

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
