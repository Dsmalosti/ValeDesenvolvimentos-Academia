"""
Testes da branch back-34-auditoria-front: o que os buscadores leem (robots.txt, sitemap.xml, llms.txt, metadados das telas
públicas, noindex nas internas), o cache com carimbo de versão dos estáticos e o foco nas tabelas dos textos legais.
"""
import json
import re

from app import create_app
from tests.conftest import criar_usuario, logar


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


# ------------------------------------------------------------------ robots, sitemap e llms
def test_robots_aponta_o_sitemap_e_fecha_as_areas_privadas(app):
    r = app.test_client().get("/robots.txt")
    texto = r.get_data(as_text=True)
    assert r.status_code == 200 and r.mimetype == "text/plain"
    assert "User-agent: *" in texto and "Disallow: /admin" in texto and "Disallow: /convite/" in texto and "Disallow: /nova-senha/" in texto
    assert "Sitemap: http://localhost/sitemap.xml" in texto
    assert "X-Robots-Tag" not in r.headers


def test_sitemap_tem_so_as_paginas_publicas_e_todas_respondem(app):
    r = app.test_client().get("/sitemap.xml")
    enderecos = re.findall(r"<loc>(.*?)</loc>", r.get_data(as_text=True))
    assert r.mimetype == "application/xml"
    assert [e.replace("http://localhost", "") for e in enderecos] == ["/login", "/criar-conta", "/termos", "/privacidade"]
    for endereco in enderecos:
        assert app.test_client().get(endereco.replace("http://localhost", "")).status_code == 200


def test_llms_txt_traz_os_fatos_do_produto(app):
    texto = app.test_client().get("/llms.txt").get_data(as_text=True)
    for trecho in ("# Vale Tec", "academias, estúdios e personal trainers", "R$ 59,99", "R$ 29,99", "2 meses",
                   "60.499.733/0001-44", "Tremembé/SP", "suporte@valesolucoestec.com.br", "http://localhost/termos"):
        assert trecho in texto, trecho


# ------------------------------------------------------------------ telas públicas
def test_login_tem_titulo_descricao_canonical_open_graph_e_dados_estruturados(app):
    html = app.test_client().get("/login").get_data(as_text=True)
    titulo = re.search(r"<title>(.*?)</title>", html).group(1)
    descricao = re.search(r'<meta name="description" content="([^"]+)"', html).group(1)
    assert 50 <= len(titulo) <= 65 and "Vale Tec" in titulo
    assert 120 <= len(descricao) <= 160
    assert '<link rel="canonical" href="http://localhost/login">' in html and 'property="og:description"' in html
    dados = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
    tipos = {item["@type"] for item in dados["@graph"]}
    assert tipos == {"Organization", "SoftwareApplication"}
    app_ = next(i for i in dados["@graph"] if i["@type"] == "SoftwareApplication")
    assert {o["price"] for o in app_["offers"]} == {"59.99", "29.99"} and all(o["priceCurrency"] == "BRL" for o in app_["offers"])


def test_descricoes_das_paginas_publicas_tem_o_tamanho_certo_e_sao_diferentes(app):
    vistas = set()
    for url in ("/login", "/criar-conta", "/termos", "/privacidade"):
        resposta = app.test_client().get(url)
        descricao = re.search(r'<meta name="description" content="([^"]+)"', resposta.get_data(as_text=True)).group(1)
        assert 120 <= len(descricao) <= 160, (url, len(descricao))
        assert "X-Robots-Tag" not in resposta.headers
        vistas.add(descricao)
    assert len(vistas) == 4


# ------------------------------------------------------------------ telas internas e links privados
def test_telas_internas_e_links_de_senha_nao_entram_no_google(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    cliente = como(app, dono)
    for url in ("/", "/alunos", "/perfil", "/configuracoes"):
        resposta = cliente.get(url)
        assert resposta.headers.get("X-Robots-Tag") == "noindex, nofollow", url
        assert 'name="description"' not in resposta.get_data(as_text=True)
    anonimo = app.test_client()
    assert anonimo.get("/esqueci-senha").headers.get("X-Robots-Tag") == "noindex, nofollow"
    assert anonimo.get("/nova-senha/qualquer-coisa").headers.get("X-Robots-Tag") == "noindex, nofollow"


# ------------------------------------------------------------------ cache dos estáticos
def test_estaticos_com_carimbo_de_versao_e_cache_de_um_ano(app):
    html = app.test_client().get("/login").get_data(as_text=True)
    css = re.search(r'href="(/static/css/app\.css\?v=[0-9a-f]{10})"', html)
    assert css, "o app.css saiu sem carimbo"
    resposta = app.test_client().get(css.group(1))
    assert resposta.status_code == 200 and "max-age=31536000" in resposta.headers["Cache-Control"]
    js = re.findall(r'src="(/static/js/[^"]+)"', html)
    assert js and all("?v=" in s for s in js)


def test_fontes_ficam_sem_carimbo_para_o_preload_bater_com_o_css(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    html = como(app, dono).get("/").get_data(as_text=True)
    preload = re.findall(r'<link rel="preload" href="([^"]+)" as="font"', html)
    assert preload and all("?v=" not in p and p.startswith("/static/fonts/") for p in preload)


def test_no_modo_de_desenvolvimento_o_cache_fica_desligado(monkeypatch):
    monkeypatch.setenv("FLASK_CONFIG", "development")
    app_dev = create_app()
    assert app_dev.debug and not app_dev.config.get("SEND_FILE_MAX_AGE_DEFAULT")


# ------------------------------------------------------------------ acessibilidade das tabelas legais
def test_tabelas_dos_textos_legais_recebem_foco_pelo_teclado(app):
    html = app.test_client().get("/privacidade").get_data(as_text=True)
    assert html.count('class="legal-tabela" tabindex="0" role="region" aria-label=') >= 3
    assert 'class="legal-tabela">' not in html
    nomes = re.findall(r'class="legal-tabela" tabindex="0" role="region" aria-label="([^"]+)"', html)
    assert len(nomes) == len(set(nomes)) and nomes[0].startswith("Tabela 1: ")      # cada área com um nome diferente


# ------------------------------------------------------------------ política à vista onde se digita e-mail e senha
def test_telas_de_acesso_mostram_os_links_dos_termos_e_da_privacidade(app):
    for url in ("/login", "/esqueci-senha", "/criar-conta"):
        html = app.test_client().get(url).get_data(as_text=True)
        assert 'href="/privacidade"' in html and 'href="/termos"' in html, url
