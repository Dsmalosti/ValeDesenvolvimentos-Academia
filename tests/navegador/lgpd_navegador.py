"""
Teste das telas da LGPD num navegador de verdade (Playwright + Chromium).

Celular (390 px, com toque, tema claro) e desktop (1440 px, tema escuro): páginas públicas de termos
e de política (lidas sem login, a partir dos links de "Criar conta"), a opção de WhatsApp no cadastro
do aluno, o botão de baixar os dados do aluno e o "Excluir aluno" que apaga os dados pessoais e tira
o aluno das telas. Salva fotos.

Sobe o app do repositório com SQLite descartável; nunca toca o banco do .env. Não roda junto
com o pytest (depende do Playwright). Para rodar:

    .venv/Scripts/python.exe -B tests/navegador/lgpd_navegador.py [pasta-das-fotos]
"""
import json
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
from tests.navegador._base import (CENARIOS, abrir_pagina, conferir_console_e_rede, entrar, pagamento_recebido,  # noqa: E402
                                   sem_none_nem_rolagem)

EMAIL, SENHA = "marina@valetec.com", "Senha-de-teste-123"
HOJE = date.today()
resultados = []
ids = {}


def checa(nome, ok, detalhe=""):
    resultados.append((nome, bool(ok), detalhe))
    print(("PASSOU " if ok else "FALHOU ") + nome + (f"  -> {detalhe}" if detalhe and not ok else ""))


def montar_app():
    """Uma aluna por cenário, cada uma com pagamento e avaliação física (é o histórico que vai ser apagado)."""
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
        for i, nome in enumerate(["Camila Celular", "Camila Desktop", "Bruno Fica"]):
            # CPF de verdade e todos os campos obrigatórios: o formulário de edição confere tudo antes de enviar
            aluno = Aluno(nome=nome, email=f"aluno{i}@exemplo.com", cpf=["529.982.247-25", "168.995.350-09", "111.444.777-35"][i],
                          telefone="(12) 98211-4400", ativo=True, data_nascimento=date(1990, 5, 20), data_inicio=HOJE - timedelta(days=5),
                          forma_pagamento="pix", dia_vencimento=10, plano_id=plano.id, instrutor_id=dona.id, conta_id=conta.id,
                          aceita_whatsapp=True)     # [back-22-ajustes-de-produto] antes vazio (a caixa vinha marcada); agora começa autorizado
            db.session.add(aluno)
            db.session.flush()
            ids[nome] = aluno.id
            pagamento_recebido(db, aluno, dona, 149.90, HOJE - timedelta(days=5), HOJE + timedelta(days=25))
            db.session.add(AvaliacaoFisica(conta_id=conta.id, aluno_id=aluno.id, data=HOJE - timedelta(days=30), avaliador_id=dona.id, peso_kg=68.4,
                                           altura_cm=167, imc=calcular_imc(68.4, 167)))
        db.session.commit()
    return app


app = montar_app()
srv = make_server("127.0.0.1", 5105, app)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5105"

with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, opts, tema in CENARIOS:
        celular = opts.get("has_touch", False)
        camila = "Camila Celular" if celular else "Camila Desktop"
        ctx, pg, erros, falhas_rede = abrir_pagina(nav, opts, tema)

        def acionar(seletor):
            pg.locator(seletor).first.scroll_into_view_if_needed()
            (pg.tap if celular else pg.click)(seletor)

        def enviar(seletor):
            with pg.expect_navigation(wait_until="load", timeout=10000):
                acionar(seletor)

        # ------------------------------------------------------------ sem login: criar conta -> termos e política
        pg.goto(BASE + "/criar-conta")
        with ctx.expect_page() as aba:
            acionar("a[href='/termos']")
        termos = aba.value
        termos.wait_for_load_state()
        texto = termos.inner_text("#conteudo")
        checa(f"[{nome}] o link de 'Criar conta' abre os termos de uso, sem login", termos.url.endswith("/termos") and "Período de teste e preço" in texto
              and "Versão preliminar 0.3" in texto and "60.499.733/0001-44" in texto and "vale.informatica02@gmail.com" in texto
              and "a definir" not in texto and "PREENCHER" not in texto and "**" not in texto)      # [back-21-textos-legais] antes: versão 0.2, com trechos "a definir"
        checa(f"[{nome}] termos: sem rolagem lateral e sem 'None'", sem_none_nem_rolagem(termos))
        termos.wait_for_timeout(400)
        termos.screenshot(path=os.path.join(FOTOS, f"{nome}-1-termos.png"), full_page=False)
        with termos.expect_navigation(wait_until="load", timeout=10000):
            (termos.tap if celular else termos.click)("a:has-text('Ver Política de Privacidade')")
        texto = termos.inner_text("#conteudo")
        tabelas = termos.evaluate("[...document.querySelectorAll('.legal-tabela')].every(d => d.scrollWidth >= d.clientWidth && d.getBoundingClientRect().right <= innerWidth + 1)")
        checa(f"[{nome}] dos termos chega-se à política de privacidade, com as tabelas dentro da tela", termos.url.endswith("/privacidade")
              and "Seus direitos" in texto and "12 horas sem uso" in texto and termos.locator(".legal-tabela table").count() >= 4 and tabelas)
        checa(f"[{nome}] política: sem rolagem lateral e sem 'None'", sem_none_nem_rolagem(termos))
        termos.screenshot(path=os.path.join(FOTOS, f"{nome}-2-privacidade.png"), full_page=True)
        termos.close()

        entrar(pg, BASE, EMAIL, SENHA, celular)

        # ------------------------------------------------------------ cadastro do aluno: aceita WhatsApp?
        pg.goto(BASE + f"/alunos/{ids['Bruno Fica']}/editar")
        caixa = pg.locator("input[name=aceita_whatsapp]")
        checa(f"[{nome}] o cadastro tem a opção de WhatsApp, no estado em que foi deixado", caixa.count() == 1 and caixa.is_checked() == celular
              and "Aceita receber avisos pelo WhatsApp" in pg.inner_text("#conteudo"), caixa.is_checked())
        altura = pg.evaluate("document.querySelector('input[name=aceita_whatsapp]').closest('label').getBoundingClientRect().height")
        checa(f"[{nome}] o interruptor tem tamanho de toque", altura >= 24 and pg.evaluate("document.querySelector('input[name=aceita_whatsapp]').closest('.switch-row').getBoundingClientRect().height") >= 44, altura)
        acionar("label.switch:has(input[name=aceita_whatsapp])")
        pg.wait_for_timeout(200)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-3-cadastro-whatsapp.png"), full_page=True)
        enviar("#conteudo form[data-validate] button[type=submit]")
        pg.goto(BASE + f"/alunos/{ids['Bruno Fica']}/editar")
        checa(f"[{nome}] a escolha fica gravada", pg.locator("input[name=aceita_whatsapp]").is_checked() == (not celular))      # o celular desmarca; o desktop marca de volta

        # ------------------------------------------------------------ perfil: baixar os dados
        pg.goto(BASE + f"/alunos/{ids[camila]}")
        botao = pg.locator("a:has-text('Baixar os dados deste aluno (LGPD)')")
        checa(f"[{nome}] o perfil tem o botão de baixar os dados (dona da conta)", botao.count() == 1 and botao.is_visible() and sem_none_nem_rolagem(pg))
        arquivo = ctx.request.get(BASE + f"/alunos/{ids[camila]}/dados")
        dados = json.loads(arquivo.text())
        checa(f"[{nome}] o arquivo traz o cadastro, o pagamento e a avaliação", arquivo.status == 200 and dados["cadastro"]["nome"] == camila
              and len(dados["cobrancas"]) == 1 and dados["avaliacoes_fisicas"][0]["peso_kg"] == 68.4)
        botao.scroll_into_view_if_needed()
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-4-zona-de-risco.png"), full_page=True)

        # ------------------------------------------------------------ excluir: apaga os dados e tira das telas
        acionar("button[data-open='dlg-excluir']")
        pg.wait_for_selector("#dlg-excluir[open]", timeout=3000)
        pg.wait_for_timeout(300)
        aviso = pg.inner_text("#dlg-excluir")
        checa(f"[{nome}] o popup diz o que é apagado e que os pagamentos ficam sem o nome", "apaga os dados pessoais" in aviso and "Os pagamentos ficam no financeiro, sem o nome" in aviso)
        pg.screenshot(path=os.path.join(FOTOS, f"{nome}-5-excluir.png"))
        enviar("#dlg-excluir button[type=submit]")
        lista = pg.inner_text("#conteudo")
        checa(f"[{nome}] depois de excluir, a aluna some da lista e não vira 'Aluno removido' na tela", pg.url.endswith("/alunos") and camila not in lista
              and "Aluno removido" not in lista and "Bruno Fica" in lista)
        perfil = pg.goto(BASE + f"/alunos/{ids[camila]}")
        checa(f"[{nome}] o endereço do perfil dela passa a não existir", perfil.status == 404)
        falhas_rede[:] = [f for f in falhas_rede if not f.startswith("404 ") or f"/alunos/{ids[camila]}" not in f]     # esse 404 é o esperado
        erros[:] = [e for e in erros if "status of 404" not in e]                                                      # ... e o aviso dele no console também

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
