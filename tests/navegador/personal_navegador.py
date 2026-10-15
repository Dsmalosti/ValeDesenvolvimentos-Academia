"""
Teste da VARIANTE PERSONAL TRAINER do front novo num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro), com uma conta de personal:
painel próprio, menu com Pacotes e Agenda, criar pacote, marcar sessão, marcar presença (abate do
saldo), lembrete da véspera na fila de mensagens, cancelar (não abate), renovar pacote (o que sobrou
soma), cobrança com o texto de pacote, perfil do profissional e locais de atendimento. Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/personal_navegador.py [pasta-das-fotos]
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
from app.models import Aluno, Cobranca, Conta, Pagamento, Plano, User  # noqa: E402
from tests.navegador._base import CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, sem_none_nem_rolagem  # noqa: E402

EMAIL, SENHA = "paulo@valetec.com", "Senha-de-teste-123"
HOJE = date.today()
AMANHA = HOJE + timedelta(days=1)
resultados = []
ids = {}


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """Paulo, personal. Pacotes de 8 e de 4 sessões. Uma Ana por cenário, com o Pacote 8 pago; Bia comprou o Pacote 4 e não pagou."""
    app = create_app()
    assert "vt-navegador-" in app.config["SQLALCHEMY_DATABASE_URI"], "o teste só roda em banco descartável"
    with app.app_context():
        db.create_all()
        conta = Conta(nome="Paulo Rocha", modelo="personal")
        db.session.add(conta)
        db.session.flush()
        paulo = User(nome="Paulo", sobrenome="Rocha", email=EMAIL, ativo=True, conta_id=conta.id, senha=bcrypt.generate_password_hash(SENHA).decode("utf-8"))
        db.session.add(paulo)
        db.session.flush()
        pacotes = {}
        for nome, sessoes, valor in (("Pacote 8", 8, 960), ("Pacote 4", 4, 520)):
            pacotes[nome] = Plano(nome=nome, valor=valor, duracao_dias=90, quantidade_sessoes=sessoes, descricao="", ativo=True, instrutor_id=paulo.id, conta_id=conta.id)
            db.session.add(pacotes[nome])
        db.session.flush()
        ids["Pacote 4"] = pacotes["Pacote 4"].id
        for i, (nome, pacote, pago) in enumerate([("Ana Celular", "Pacote 8", True), ("Ana Desktop", "Pacote 8", True), ("Bia Lima", "Pacote 4", False)]):
            aluno = Aluno(nome=nome, email=f"aluno{i}@exemplo.com", cpf=f"111.222.333-0{i}", telefone="(12) 98211-4400", ativo=True,
                          plano_id=pacotes[pacote].id, instrutor_id=paulo.id, conta_id=conta.id,
                          aceita_whatsapp=True)     # [back-22-ajustes-de-produto] só quem autorizou entra na fila de Mensagens
            db.session.add(aluno)
            db.session.flush()
            ids[nome] = aluno.id
            quando = datetime.utcnow() - timedelta(days=10)
            compra = Cobranca(conta_id=conta.id, aluno_id=aluno.id, plano_id=pacotes[pacote].id, tipo="matricula", valor=pacotes[pacote].valor,
                              data_inicio=quando.date(), data_vencimento=quando.date() + timedelta(days=90), status="paga" if pago else "pendente",
                              instrutor_id=paulo.id, quantidade_sessoes=pacotes[pacote].quantidade_sessoes, data_geracao=quando)
            db.session.add(compra)
            db.session.flush()
            if pago:
                db.session.add(Pagamento(conta_id=conta.id, cobranca_id=compra.id, forma="pix", valor_pago=compra.valor, data_pagamento=quando,
                                         origem_confirmacao="manual", confirmado_por_instrutor_id=paulo.id))
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5104, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5104"

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        ana = "Ana Celular" if celular else "Ana Desktop"
        hora_hoje, hora_amanha = ("07:30", "09:00") if celular else ("08:30", "10:00")      # o mesmo profissional não tem dois alunos no mesmo horário
        pacote_novo = "Pacote 12 celular" if celular else "Pacote 12 desktop"
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)

        def acionar(seletor):
            pg.locator(seletor).first.scroll_into_view_if_needed()
            (pg.tap if celular else pg.click)(seletor)

        def enviar(seletor):
            """Aciona um botão ou link que troca de página e espera a página nova terminar de carregar."""
            with pg.expect_navigation(wait_until="load", timeout=10000):
                acionar(seletor)

        def marcar_sessao(dia, hora):
            """Marca uma sessão para a Ana deste cenário pela tela e volta para a agenda."""
            pg.goto(BASE + f"/agenda/nova?aluno={ids[ana]}")
            pg.fill("#f-data", dia.strftime("%d/%m/%Y"))
            acionar(f".opcoes[data-alvo='h-horario'] button[data-valor='{hora}']")
            acionar(".opcoes[data-alvo='h-local'] button[data-valor='parque']")
            enviar("button[name=acao][value=marcar]")

        entrar(pg, BASE, EMAIL, SENHA, celular)

        # ------------------------------------------------------------ painel e menu do personal
        texto = pg.inner_text("body").lower()
        checa(f"[{nome}] o painel é o do personal", "pacotes acabando" in texto and "vencimentos no mês" not in texto and pg.locator(".app .main").count() == 1)
        if celular:
            abas = pg.locator(".tabbar .tabbar__item").all_inner_texts()
            checa(f"[{nome}] barra de baixo: Painel, Alunos, Pacotes e Agenda", [a.strip() for a in abas] == ["Painel", "Alunos", "Pacotes", "Agenda"], abas)
        else:
            checa(f"[{nome}] menu lateral tem a Agenda e mostra as sessões de hoje", pg.locator(".rail .navicon[aria-label='Agenda']").count() == 1 and "sessões hoje" in texto)
        checa(f"[{nome}] painel: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(900)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-1-painel.png"), full_page=True)

        # ------------------------------------------------------------ pacotes
        if celular:
            enviar(".tabbar .tabbar__item:has-text('Pacotes')")
        else:
            pg.goto(BASE + "/planos")
        cartao = ".plano-m" if celular else "article.plano"
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] a tela de planos virou Pacotes, com sessões no lugar de dias", "pacotes" in pg.inner_text("body").lower() and "8 sessões" in texto
              and "dias" not in texto.lower() and pg.locator(f"{cartao} >> visible=true").count() >= 2)
        checa(f"[{nome}] pacotes: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-2-pacotes.png"), full_page=True)
        if celular:
            enviar("a:has-text('Criar novo pacote')")
        formulario = "#conteudo form[data-validate]"
        pg.fill(f"{formulario} #f-nome", pacote_novo)
        pg.fill(f"{formulario} #f-valor", "1.440,00")
        pg.fill(f"{formulario} #f-quantidade_sessoes", "12")
        enviar(f"{formulario} button[type=submit]:has-text('pacote')")
        checa(f"[{nome}] criar pacote grava as sessões e o valor de cada uma", pg.url.endswith("/planos") and pacote_novo in pg.inner_text("#conteudo")
              and "12 sessões" in pg.inner_text(f"{cartao}:has-text('{pacote_novo}') >> visible=true"))

        # ------------------------------------------------------------ agenda: marcar
        if celular:
            enviar(".tabbar .tabbar__item:has-text('Agenda')")
        else:
            enviar(".rail .navicon[aria-label='Agenda']")
        checa(f"[{nome}] o menu abre a agenda", pg.url.endswith("/agenda") and ana not in pg.inner_text("#conteudo"))
        enviar("a:has-text('Marcar sessão') >> visible=true")
        pg.fill("input[name=q]", ana.lower())
        with pg.expect_navigation(wait_until="load", timeout=10000):
            pg.press("input[name=q]", "Enter")
        checa(f"[{nome}] escolher com quem: a busca mostra o saldo do pacote", pg.locator(".mlist .mrow").count() == 1 and "sobram 8 sessões" in pg.inner_text(".mlist"))
        enviar(f".mlist .mrow:has-text('{ana}')")
        checa(f"[{nome}] formulário da sessão com o pacote da aluna e os locais", "Pacote de 8 · sobram 8 sessões" in pg.inner_text("#conteudo")
              and pg.locator(".opcoes[data-alvo='h-local'] button").count() == 4 and sem_none_nem_rolagem(pg))
        pg.fill("#f-data", HOJE.strftime("%d/%m/%Y"))
        acionar(f".opcoes[data-alvo='h-horario'] button[data-valor='{hora_hoje}']")
        acionar(".opcoes[data-alvo='h-local'] button[data-valor='parque']")
        checa(f"[{nome}] tocar no horário e no local grava a escolha", pg.input_value("#h-horario") == hora_hoje and pg.input_value("#h-local") == "parque")
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-marcar-sessao.png"), full_page=True)
        enviar("button[name=acao][value=marcar]")
        linha = pg.inner_text(f".ag-lista li:has-text('{ana}')")
        checa(f"[{nome}] a sessão aparece na agenda de hoje", pg.url.endswith("/agenda") and hora_hoje in linha and "Parque" in linha and "Agendada" in linha, linha)
        checa(f"[{nome}] agenda: sem 'None' e sem rolagem lateral", sem_none_nem_rolagem(pg))
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-4-agenda.png"), full_page=True)

        # ------------------------------------------------------------ sessão: marcar presença abate do saldo
        enviar(f".ag-lista a.ag-item:has-text('{ana}')")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] a sessão mostra o pacote e não inventa lembrete", "0 de 8 usadas" in texto and "Parque · treino ao ar livre" in texto
              and "confirmou" not in texto.lower() and sem_none_nem_rolagem(pg), texto[:200])
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-5-sessao.png"), full_page=True)
        sessao_url = pg.url
        enviar("button:has-text('Marcar presença e fechar sessão')")
        checa(f"[{nome}] marcar presença volta para a agenda, com a sessão concluída", pg.url.endswith("/agenda") and "Concluída" in pg.inner_text(f".ag-lista li:has-text('{ana}')"))
        pg.goto(sessao_url)
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] a presença abateu 1 do saldo e a sessão ficou fechada", "1 de 8 usada" in texto and "Sessão fechada" in texto
              and "7 sessões" in texto and pg.locator("button:has-text('Marcar presença')").count() == 0, texto[:200])

        # ------------------------------------------------------------ véspera na fila de mensagens e cancelar
        marcar_sessao(AMANHA, hora_amanha)
        pg.goto(BASE + "/mensagens")
        fila = pg.inner_text("#conteudo")
        checa(f"[{nome}] a sessão de amanhã entra na fila de mensagens, com o texto do personal", f"Sessão amanhã às {hora_amanha} · parque" in fila
              and "Confirmando nosso treino amanhã" in fila and "Sessões de amanhã" in fila and "Avaliações de amanhã" not in fila)
        checa(f"[{nome}] a cobrança da fila fala em pacote", "Pacote em aberto · R$ 520,00" in fila and "Seu pacote (Pacote 4)" in fila)
        pg.goto(BASE + "/agenda")
        enviar(f".ag-lista a.ag-item:has-text('{ana}'):has-text('{hora_amanha}')")
        acionar("button[data-open='dlg-cancelar']")
        pg.wait_for_selector("#dlg-cancelar[open]", timeout=3000)
        pg.wait_for_timeout(300)
        checa(f"[{nome}] cancelar pede confirmação e diz que não abate", "não abate do saldo" in pg.inner_text("#dlg-cancelar"))
        enviar("#dlg-cancelar button[type=submit]")
        checa(f"[{nome}] a sessão cancelada sai da agenda", pg.url.endswith("/agenda") and pg.locator(f".ag-lista a.ag-item:has-text('{ana}'):has-text('{hora_amanha}')").count() == 0)

        # ------------------------------------------------------------ renovar: o que sobrou soma
        pg.goto(BASE + f"/alunos/{ids[ana]}/renovar")
        texto = pg.inner_text("#conteudo")
        checa(f"[{nome}] renovar mostra o saldo de hoje (o cancelamento não abateu) e o novo saldo", "Pacote 8 · sobram 7 sessões" in texto
              and pg.inner_text("[data-e='novo']").strip() == "15 sessões" and "somam no saldo novo" in texto, texto[:300])
        acionar(f".opcoes[data-alvo='h-plano-id'] button[data-valor='{ids['Pacote 4']}']")
        pg.wait_for_timeout(200)
        checa(f"[{nome}] trocar de pacote recalcula o novo saldo e o valor na tela", pg.inner_text("[data-e='novo']").strip() == "11 sessões"
              and "520,00" in pg.inner_text("[data-e='valor']"))
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-6-renovar.png"), full_page=True)
        enviar("button[name=acao][value=sem_cobrar]")
        perfil = pg.inner_text("#conteudo")
        checa(f"[{nome}] renovado: o perfil mostra o saldo somado e a aluna fica pendente", pg.url.endswith(f"/alunos/{ids[ana]}") and "Sobram 11 sessões" in perfil
              and sem_none_nem_rolagem(pg), perfil[:200])

        # ------------------------------------------------------------ cobrança de pacote
        pg.goto(BASE + f"/alunos/{ids['Bia Lima']}/renovar")
        enviar("button[name=acao][value=receber]")
        texto = pg.inner_text("#conteudo").lower()
        checa(f"[{nome}] a tela de cobrança fala em pacote, sem dias nem vencimento", "/cobrancas/" in pg.url and "pacote" in texto and "mensalidade" not in texto
              and sem_none_nem_rolagem(pg), texto[:200])
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-7-cobranca-de-pacote.png"), full_page=True)

        # ------------------------------------------------------------ configurações do personal
        pg.goto(BASE + "/configuracoes?aba=perfil")
        checa(f"[{nome}] configurações do personal: perfil, sem equipe nem horário", "dados e contato" in pg.inner_text("#conteudo").lower()
              and "equipe" not in pg.inner_text("#conteudo").lower() and sem_none_nem_rolagem(pg))
        pg.fill("#f-cpf", "111.444.777-35")
        pg.fill("#f-cref", "012345-G/SP")
        pg.fill("#f-cidade", "Tremembé / SP")
        enviar("#conteudo form[action$='/configuracoes/academia'] button[type=submit]")
        checa(f"[{nome}] salvar o perfil guarda CPF e CREF", pg.input_value("#f-cpf") == "111.444.777-35" and pg.input_value("#f-cref") == "012345-G/SP")
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-8-configuracoes.png"), full_page=True)
        if not celular:      # desligar um local muda o formulário de marcar sessão (feito no fim, para não afetar o outro cenário)
            pg.goto(BASE + "/configuracoes?aba=locais")
            pg.click("label.switch:has(input[value='online'])")
            enviar("#conteudo form[action$='/configuracoes/locais'] button[type=submit]")
            pg.goto(BASE + f"/agenda/nova?aluno={ids[ana]}")
            checa(f"[{nome}] local desligado some de 'Marcar sessão'", pg.locator(".opcoes[data-alvo='h-local'] button").count() == 3
                  and pg.locator(".opcoes[data-alvo='h-local'] button[data-valor='online']").count() == 0)

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
