"""
Testes da branch back-20-producao: banco novo, /saude, configuração de produção, proxy e fuso.
No fim, a varredura da checklist final de segurança: a conta B pedindo TODAS as rotas com os ids da conta A.
"""
import os
import re
import tempfile
import time
from datetime import date, datetime, timedelta

import pytest

from app import create_app
from app.extensions.database import db
from app.extensions.protecao import limiter
from app.models import Exercicio
from tests.conftest import (_PASTA, conta_de, criar_agendamento, criar_aluno, criar_avaliacao, criar_cobranca_em_aberto, criar_custo,
                            criar_entrada, criar_exercicio, criar_ficha, criar_pagamento, criar_plano, criar_treino, criar_usuario, logar)

HOJE = date.today()


@pytest.fixture()
def ambiente():
    """Deixa o teste mexer nas variáveis de ambiente e devolve tudo como estava no fim."""
    antes = dict(os.environ)
    yield os.environ
    os.environ.clear()
    os.environ.update(antes)
    limiter.enabled = False
    limiter.reset()


# ------------------------------------------------------------------ /saude
def test_saude_responde_sem_login_e_sem_mostrar_nada(app):
    resposta = app.test_client().get("/saude")
    assert resposta.status_code == 200 and resposta.get_data(as_text=True) == "ok"
    assert resposta.headers["Content-Type"].startswith("text/plain") and resposta.headers["Cache-Control"] == "no-store"


def test_saude_avisa_quando_o_banco_cai(app, monkeypatch):
    def banco_fora(*args, **kwargs):
        raise RuntimeError("conexão recusada em 10.0.0.5:5432 usuario=vale")
    monkeypatch.setattr(db.session, "execute", banco_fora)
    resposta = app.test_client().get("/saude")
    assert resposta.status_code == 503 and resposta.get_data(as_text=True) == "banco fora do ar"      # sem o detalhe do erro


def test_em_producao_o_monitor_chama_a_saude_sem_https_e_o_resto_continua_exigindo(app, ambiente):
    ambiente["FLASK_CONFIG"] = "production"
    producao = create_app()
    cliente = producao.test_client()
    saude = cliente.get("/saude")                                                              # por dentro da rede da hospedagem, sem HTTPS
    assert saude.status_code == 200 and saude.get_data(as_text=True) == "ok"
    login = cliente.get("/login")
    assert login.status_code == 302 and login.headers["Location"].startswith("https://")      # todas as outras continuam indo para o HTTPS


# ------------------------------------------------------------------ banco novo
def test_banco_novo_cria_tudo_marca_a_versao_e_recusa_banco_que_ja_tem_tabela(app, ambiente):
    arquivo = os.path.join(tempfile.mkdtemp(prefix="vt-testes-", dir=_PASTA), "novo.db").replace("\\", "/")
    ambiente["DATABASE_URL"] = "sqlite:///" + arquivo
    novo = create_app()
    assert "vt-testes-" in novo.config["SQLALCHEMY_DATABASE_URI"] and "novo.db" in novo.config["SQLALCHEMY_DATABASE_URI"]

    primeira = novo.test_cli_runner().invoke(args=["banco-novo"])
    assert primeira.exit_code == 0, primeira.output
    assert "64 exercícios no catálogo padrão" in primeira.output
    with novo.app_context():
        from sqlalchemy import inspect, text
        tabelas = set(inspect(db.engine).get_table_names())
        assert {"contas", "instrutores", "alunos", "planos", "cobrancas", "pagamentos", "sessoes", "avaliacoes_fisicas", "mensagens_enviadas",
                "alembic_version"} <= tabelas
        versao = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert Exercicio.query.filter(Exercicio.conta_id.is_(None)).count() == 64
    migrations = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations", "versions")
    assert any(nome.startswith(versao) for nome in os.listdir(migrations))                    # marcado numa versão que existe...
    textos = [open(os.path.join(migrations, n), encoding="utf-8").read() for n in os.listdir(migrations) if n.endswith(".py")]
    assert not any(f"down_revision = '{versao}'" in t for t in textos)                         # ... e que é a última (ninguém vem depois dela)

    segunda = novo.test_cli_runner().invoke(args=["banco-novo"])
    assert segunda.exit_code != 0 and "só vale para banco vazio" in segunda.output             # nunca passa por cima de um banco em uso
    with novo.app_context():
        db.session.remove()
        db.engine.dispose()


# ------------------------------------------------------------------ configuração
def test_endereco_de_banco_no_formato_das_hospedagens_e_aceito(app, ambiente):
    ambiente["DATABASE_URL"] = "postgres://usuario:senha@localhost:5432/vale"
    assert create_app().config["SQLALCHEMY_DATABASE_URI"] == "postgresql://usuario:senha@localhost:5432/vale"


def test_producao_exige_o_nome_oficial_da_variavel_do_banco(app, ambiente):
    endereco = ambiente.pop("DATABASE_URL")
    ambiente["DATABASE_URI"] = endereco
    assert create_app().config["SQLALCHEMY_DATABASE_URI"] == endereco                          # no computador de quem desenvolve o nome antigo ainda serve
    ambiente["FLASK_CONFIG"] = "production"
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app()


def test_producao_sem_chave_secreta_nao_sobe(app, ambiente):
    ambiente["FLASK_CONFIG"] = "production"
    del ambiente["SECRET_KEY"]
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def test_fuso_no_servidor_e_o_de_brasilia_e_no_windows_ninguem_mexe(app, ambiente):
    ambiente.pop("TZ", None)
    if not hasattr(time, "tzset"):
        # Windows: definir TZ ali adianta o relógio do Python em 3 horas. O app não pode criar a variável.
        agora = datetime.now()
        create_app()
        assert "TZ" not in os.environ
        assert abs((datetime.now() - agora).total_seconds()) < 60
        return
    try:
        create_app()
        assert os.environ["TZ"] == "America/Sao_Paulo"
        assert time.localtime().tm_gmtoff == -3 * 3600                                         # Brasília, sem horário de verão
        ambiente["TZ"] = "America/Manaus"
        create_app()
        assert os.environ["TZ"] == "America/Manaus" and time.localtime().tm_gmtoff == -4 * 3600    # quem definiu outro fuso continua com o dele
    finally:
        os.environ.pop("TZ", None)
        time.tzset()


def _tentativas(aplicacao, quantas, ip_no_cabecalho):
    aplicacao.config.update(TESTING=True, WTF_CSRF_ENABLED=False)      # igual ao app dos outros testes: sem o código do formulário
    cliente = aplicacao.test_client()
    return [cliente.post("/login", data={"identificador": f"alvo{i}@teste.local", "senha": "errada"},
                         headers={"X-Forwarded-For": ip_no_cabecalho}).status_code for i in range(quantas)]


def test_atras_do_proxy_o_limite_de_tentativas_enxerga_o_ip_de_verdade(app, ambiente):
    """Com PROXIES_NA_FRENTE=1, cada visitante é contado pelo próprio IP. Sem a variável, o cabeçalho não é levado em conta."""
    ambiente["PROXIES_NA_FRENTE"] = "1"
    com_proxy = create_app()
    limiter.enabled = True
    limiter.reset()
    assert _tentativas(com_proxy, 11, "200.1.1.1")[-1] == 429                                  # o visitante 200.1.1.1 estourou o limite dele
    assert _tentativas(com_proxy, 1, "200.2.2.2") == [200]                                     # ... e o 200.2.2.2 continua entrando

    ambiente.pop("PROXIES_NA_FRENTE")
    sem_proxy = create_app()
    limiter.enabled = True
    limiter.reset()
    assert _tentativas(sem_proxy, 10, "200.1.1.1")[-1] == 200
    assert _tentativas(sem_proxy, 1, "200.9.9.9") == [429]                                     # sem proxy declarado, inventar o cabeçalho não zera a contagem


# ------------------------------------------------------------------ checklist final: conta A x conta B em todas as rotas
MARCA = "ZZSEGREDO"


def test_a_conta_b_nao_ve_nada_da_conta_a_em_nenhuma_rota(app):
    """
    A conta A tem um registro de cada tipo, todos com o id 1 e com a MARCA no texto. A conta B (vazia) pede TODAS as
    rotas GET do sistema com os parâmetros trocados por 1. Nenhuma resposta pode trazer a marca, e nenhuma pode quebrar
    (fora a tela antiga /instrutores/painel/, que já quebra na main para qualquer conta).
    """
    a = criar_usuario("a@teste.local", nome=f"{MARCA}DONA")
    plano = criar_plano(a, nome=f"{MARCA}PLANO")
    aluno = criar_aluno(a, plano, f"{MARCA}ALUNO", "zz@exemplo.com", "111.222.333-96", nascimento=date(1990, HOJE.month, min(HOJE.day, 28)))
    criar_pagamento(a, aluno, 100, HOJE - timedelta(days=40), HOJE - timedelta(days=10))
    criar_cobranca_em_aberto(a, aluno, 100, HOJE - timedelta(days=9), HOJE + timedelta(days=21))
    criar_entrada(a, aluno, datetime.now() - timedelta(hours=1))
    criar_exercicio(f"{MARCA}EXERCICIO", a)
    criar_treino(criar_ficha(aluno, nome=f"{MARCA}FICHA"))
    criar_avaliacao(a, aluno, HOJE, anotacao=f"{MARCA}ANOTACAO")
    criar_agendamento(a, aluno, HOJE)
    criar_custo(a, f"{MARCA}CUSTO", 500)
    from app.models import Conta
    with app.app_context():
        db.session.get(Conta, conta_de(a)).nome = f"{MARCA}ACADEMIA"
        db.session.commit()

    b = criar_usuario("b@teste.local", nome="Beto")

    def varrer(usuario):
        """Pede todas as rotas GET logado como `usuario`. Devolve (rotas que mostraram a marca, rotas que quebraram, quantas respondeu)."""
        cliente = app.test_client()
        logar(cliente, usuario)
        com_marca, quebras, conferidas = [], [], 0
        for regra in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
            if "GET" not in regra.methods or regra.endpoint == "static" or "sair" in regra.rule or "logout" in regra.rule:
                continue
            url = re.sub(r"<[^>]+>", "1", regra.rule)
            try:
                resposta = cliente.get(url)
            except Exception as erro:                # tela antiga que já quebrava antes (anotada no roadmap)
                quebras.append(f"{url}: {type(erro).__name__}")
                continue
            conferidas += 1
            if MARCA in resposta.get_data(as_text=True) or MARCA in (resposta.headers.get("Location") or ""):
                com_marca.append(f"{url} ({resposta.status_code})")
        return com_marca, quebras, conferidas

    # prova de que a varredura enxerga: a própria conta A vê a marca em muitas telas
    da_dona, _, _ = varrer(a)
    assert len(da_dona) >= 20, da_dona

    vazamentos, quebras, conferidas = varrer(b)
    assert vazamentos == [], "a conta B viu dado da conta A em: " + ", ".join(vazamentos)
    assert conferidas >= 70
    # a única quebra aceita é a da tela antiga /instrutores/painel/, que já quebra na main (anotada no roadmap)
    assert {q.split(":")[0] for q in quebras} <= {"/instrutores/painel/"}, quebras
