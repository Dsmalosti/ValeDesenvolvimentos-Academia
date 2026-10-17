"""
Auditoria automática de páginas web (parte medível da skill auditoria-qualidade-web).

Mede, para cada página e cada largura de tela:
  - requisições e peso (total, por tipo), requisições a outros domínios, conteúdo misto (http numa página https);
  - imagens: formato, tamanho (limite 300 KB), sem alt; vídeos: formato;
  - texto sem compressão (Content-Encoding) e cache dos estáticos (Cache-Control);
  - metadados: <title>, meta description, canonical, robots, Open Graph, JSON-LD, lang, viewport, quantos <h1>;
  - layout: rolagem lateral, alvos de toque menores que 44 px (só nas larguras de celular), texto menor que 12 px;
  - erros no console e falhas de rede (4xx/5xx);
  - acessibilidade com o axe-core (opcional, --axe), por gravidade;
  - tempos: TTFB, DOMContentLoaded, load e LCP (em local servem só de referência).
E, uma vez por site: robots.txt, sitemap.xml e, se a base for https, redirecionamento http->https, HSTS e validade do certificado.

Uso:
    python auditar_paginas.py --base http://127.0.0.1:5000 --paginas / /login --saida relatorio
    opcionais: --internas /alunos /planos --login-url /login --email E --senha S
               [--campo-email "#f-identificador"] [--campo-senha "#f-senha"] [--axe] [--larguras 360 390 768 1440]

Precisa: Python 3.9+ e Playwright com o Chromium (pip install playwright && python -m playwright install chromium).
O axe-core é carregado do CDN só dentro do navegador de teste; nada é instalado no projeto.
"""
import argparse
import datetime
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

from playwright.sync_api import sync_playwright

AXE_URL = "https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js"
LIMITE_IMAGEM = 300 * 1024
FORMATOS_BONS = ("image/webp", "image/avif", "image/svg+xml")
EXCECOES_DE_IMAGEM = ("favicon", "apple-touch", "icon-", "favicon-")   # PNG/ICO exigidos por aparelhos e manifesto
TIPOS_TEXTO = ("text/html", "text/css", "javascript", "application/json", "image/svg+xml", "text/plain", "application/xml")

COLETA_DO_DOM = r"""
() => {
  const q = s => document.querySelector(s);
  const meta = n => (q(`meta[name="${n}"]`) || {}).content || null;
  const og = p => (q(`meta[property="${p}"]`) || {}).content || null;
  const visiveis = [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, [role=button]')]
      .filter(e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
                     return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; });
  const pequenos = visiveis.map(e => { const r = e.getBoundingClientRect();
      return {tag: e.tagName.toLowerCase(), texto: (e.innerText || e.getAttribute('aria-label') || e.name || '').trim().slice(0, 40),
              w: Math.round(r.width), h: Math.round(r.height)}; })
      .filter(x => x.w < 44 || x.h < 44);
  const fontes = new Set();
  for (const el of document.querySelectorAll('body *')) {
    if (!el.childNodes.length || ![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const t = parseFloat(getComputedStyle(el).fontSize); if (t < 12) fontes.add(Math.round(t * 10) / 10);
  }
  return {
    titulo: document.title, descricao: meta('description'), robots: meta('robots'), viewport: meta('viewport'),
    canonical: (q('link[rel=canonical]') || {}).href || null, lang: document.documentElement.lang || null,
    og: {titulo: og('og:title'), descricao: og('og:description'), imagem: og('og:image')},
    jsonld: [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => { try { const d = JSON.parse(s.textContent); const itens = d['@graph'] || [d]; return itens.map(i => i['@type'] || 'sem @type').join('+'); } catch (e) { return 'JSON inválido'; } }),
    h1: [...document.querySelectorAll('h1')].filter(h => h.getClientRects().length && getComputedStyle(h).visibility !== 'hidden').length,
    h1_no_html: document.querySelectorAll('h1').length,
    titulos: [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => +h.tagName[1]),
    imagens_sem_alt: [...document.querySelectorAll('img:not([alt])')].map(i => i.currentSrc || i.src).slice(0, 10),
    videos: [...document.querySelectorAll('video source, video[src]')].map(v => v.type || v.src),
    rolagem_lateral: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    alvos_pequenos: pequenos.slice(0, 15), total_alvos_pequenos: pequenos.length,
    fontes_pequenas: [...fontes].sort(),
  };
}
"""

TEMPOS = r"""
() => new Promise(resolve => {
  const n = performance.getEntriesByType('navigation')[0] || {};
  let lcp = null;
  try { new PerformanceObserver(l => { const e = l.getEntries(); lcp = e[e.length - 1].startTime; })
        .observe({type: 'largest-contentful-paint', buffered: true}); } catch (e) {}
  setTimeout(() => resolve({ttfb: n.responseStart ? Math.round(n.responseStart) : null,
                            dom: n.domContentLoadedEventEnd ? Math.round(n.domContentLoadedEventEnd) : null,
                            load: n.loadEventEnd ? Math.round(n.loadEventEnd) : null,
                            lcp: lcp ? Math.round(lcp) : null}), 300);
})
"""


def kb(n):
    return f"{(n or 0) / 1024:.1f} KB"


def auditar_pagina(contexto, url, largura, pasta, usar_axe):
    """Abre a página e mede tudo. Devolve um dicionário."""
    pagina = contexto.new_page()
    respostas, erros, falhas = [], [], []
    pagina.on("console", lambda m: m.type == "error" and erros.append(m.text[:200]))
    pagina.on("pageerror", lambda e: erros.append(str(e)[:200]))
    pagina.on("requestfailed", lambda r: falhas.append(f"falhou {r.url[:120]}"))

    def ao_responder(r):
        try:
            corpo = r.body()
            tamanho = len(corpo)
        except Exception:
            tamanho = int(r.headers.get("content-length") or 0)
        respostas.append({"url": r.url, "status": r.status, "tipo": (r.headers.get("content-type") or "").split(";")[0],
                          "bytes": tamanho, "encoding": r.headers.get("content-encoding"), "cache": r.headers.get("cache-control"),
                          "x_robots": r.headers.get("x-robots-tag")})
    pagina.on("response", ao_responder)

    principal = pagina.goto(url, wait_until="load", timeout=30000)
    pagina.wait_for_timeout(800)
    dom = pagina.evaluate(COLETA_DO_DOM)
    tempos = pagina.evaluate(TEMPOS)
    da_pagina = list(respostas)        # fotografia do que a PÁGINA baixou: o axe-core, injetado abaixo, não entra na conta
    axe = None
    if usar_axe:
        try:
            pagina.add_script_tag(url=AXE_URL)
            resultado = pagina.evaluate("async () => (await axe.run(document, {resultTypes: ['violations']})).violations"
                                        ".map(v => ({id: v.id, impacto: v.impact, ajuda: v.help, nos: v.nodes.length,"
                                        " exemplo: (v.nodes[0] || {}).target}))")
            axe = resultado
        except Exception as erro:              # CSP da página pode bloquear script de fora: fica "não verificado"
            axe = {"erro": str(erro)[:200]}
    nome = urllib.parse.urlparse(url).path.strip("/").replace("/", "_") or "inicio"
    foto = os.path.join(pasta, f"{nome}-{largura}.png")
    pagina.screenshot(path=foto, full_page=True)
    pagina.close()

    host = urllib.parse.urlparse(url).hostname
    https = url.startswith("https://")
    imagens = [r for r in da_pagina if r["tipo"].startswith("image/")]
    return {
        "url": url, "largura": largura, "status": principal.status if principal else None,
        "x_robots_tag": principal.headers.get("x-robots-tag") if principal else None,
        "requisicoes": len(da_pagina), "bytes_total": sum(r["bytes"] for r in da_pagina),
        "bytes_por_tipo": _somar_por_tipo(da_pagina),
        "terceiros": sorted({urllib.parse.urlparse(r["url"]).hostname for r in da_pagina
                             if urllib.parse.urlparse(r["url"]).hostname not in (host, None)}),
        "conteudo_misto": [r["url"] for r in da_pagina if https and r["url"].startswith("http://")],
        "imagens_formato_ruim": [f"{r['url'].split('?')[0].rsplit('/', 1)[-1]} ({r['tipo']}, {kb(r['bytes'])})" for r in imagens
                                 if r["tipo"] not in FORMATOS_BONS and not any(x in r["url"].lower() for x in EXCECOES_DE_IMAGEM)],
        "imagens_acima_de_300kb": [f"{r['url'].split('?')[0].rsplit('/', 1)[-1]} ({kb(r['bytes'])})" for r in imagens if r["bytes"] > LIMITE_IMAGEM],
        "sem_compressao": [f"{r['url'].split('?')[0].rsplit('/', 1)[-1]} ({kb(r['bytes'])})" for r in da_pagina
                           if any(t in r["tipo"] for t in TIPOS_TEXTO) and r["bytes"] > 1024 and not r["encoding"]],
        "estaticos_sem_cache": [r["url"].split("?")[0].rsplit("/", 1)[-1] for r in da_pagina
                                if "/static/" in r["url"] and not (r["cache"] and "max-age" in r["cache"] and "max-age=0" not in r["cache"])],
        "falhas_de_rede": [f"{r['status']} {r['url'][:120]}" for r in da_pagina if r["status"] >= 400] + falhas,
        "erros_console": erros, "dom": dom, "tempos": tempos, "axe": axe, "foto": foto,
    }


def _somar_por_tipo(respostas):
    grupos = {}
    for r in respostas:
        t = r["tipo"]
        chave = ("html" if "html" in t else "css" if "css" in t else "js" if "javascript" in t else
                 "fonte" if "font" in t or r["url"].endswith((".woff2", ".woff")) else "imagem" if t.startswith("image/") else "outro")
        grupos[chave] = grupos.get(chave, 0) + r["bytes"]
    return grupos


def conferir_site(base):
    """robots.txt, sitemap.xml, http->https, HSTS e certificado."""
    site = {}
    for caminho in ("/robots.txt", "/sitemap.xml", "/llms.txt"):
        try:
            with urllib.request.urlopen(base.rstrip("/") + caminho, timeout=10) as r:
                site[caminho] = {"status": r.status, "tipo": r.headers.get("content-type"), "inicio": r.read(300).decode("utf-8", "replace")}
        except urllib.error.HTTPError as e:
            site[caminho] = {"status": e.code}
        except Exception as e:
            site[caminho] = {"erro": str(e)[:120]}
    partes = urllib.parse.urlparse(base)
    if partes.scheme == "https":
        host = partes.hostname
        try:
            pedido = urllib.request.Request("http://" + host + "/", method="HEAD")
            opener = urllib.request.build_opener(_SemRedirecionar())
            try:
                opener.open(pedido, timeout=10)
                site["http_para_https"] = "não redireciona"
            except urllib.error.HTTPError as e:
                site["http_para_https"] = f"{e.code} -> {e.headers.get('location')}"
        except Exception as e:
            site["http_para_https"] = f"erro: {str(e)[:100]}"
        try:
            with urllib.request.urlopen(base, timeout=10) as r:
                site["hsts"] = r.headers.get("strict-transport-security")
                site["csp"] = bool(r.headers.get("content-security-policy"))
        except Exception as e:
            site["hsts"] = f"erro: {str(e)[:100]}"
        try:
            with socket.create_connection((host, 443), timeout=10) as s:
                with ssl.create_default_context().wrap_socket(s, server_hostname=host) as c:
                    cert = c.getpeercert()
            vence = datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
            site["certificado"] = {"vence_em": vence.date().isoformat(), "dias": (vence - datetime.datetime.utcnow()).days}
        except Exception as e:
            site["certificado"] = {"erro": str(e)[:150]}
    else:
        site["https"] = "não verificado: a base não é https (ambiente local?)"
    return site


class _SemRedirecionar(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def entrar(contexto, base, args):
    pagina = contexto.new_page()
    pagina.goto(base.rstrip("/") + args.login_url, wait_until="load")
    pagina.fill(args.campo_email, args.email)
    pagina.fill(args.campo_senha, args.senha)
    with pagina.expect_navigation(wait_until="load", timeout=15000):
        pagina.click("button[type=submit]")
    pagina.close()


def markdown(resultado):
    linhas = [f"# Auditoria automática — {resultado['base']} — {resultado['quando']}", "",
              "Medido pelo script da skill auditoria-qualidade-web. Em ambiente local, tempos, compressão e cache não refletem a produção.", "",
              "## Site", "", "```json", json.dumps(resultado["site"], ensure_ascii=False, indent=2), "```", "",
              "## Páginas", "",
              "| Página | Largura | Req. | Peso | HTML | CSS | JS | Fontes | Imagens | Rolagem lateral | Alvos < 44px | Console | axe (crít./sérias) | LCP local |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in resultado["paginas"]:
        t = p["bytes_por_tipo"]
        axe = p["axe"]
        if isinstance(axe, list):
            axe_txt = f"{sum(1 for v in axe if v['impacto'] == 'critical')}/{sum(1 for v in axe if v['impacto'] == 'serious')}"
        else:
            axe_txt = "—" if axe is None else "não rodou"
        linhas.append(f"| {urllib.parse.urlparse(p['url']).path} | {p['largura']} | {p['requisicoes']} | {kb(p['bytes_total'])} | {kb(t.get('html'))} | "
                      f"{kb(t.get('css'))} | {kb(t.get('js'))} | {kb(t.get('fonte'))} | {kb(t.get('imagem'))} | "
                      f"{'SIM' if p['dom']['rolagem_lateral'] else 'não'} | {p['dom']['total_alvos_pequenos'] if p['largura'] < 768 else '—'} | "
                      f"{len(p['erros_console'])} | {axe_txt} | {p['tempos'].get('lcp')} ms |")
    linhas += ["", "## Metadados (largura maior de cada página)", "",
               "| Página | title (car.) | description (car.) | canonical | robots / X-Robots-Tag | og:image | JSON-LD | lang | h1 |", "|---|---|---|---|---|---|---|---|---|"]
    vistas = {}
    for p in resultado["paginas"]:
        vistas[p["url"]] = p
    for url, p in vistas.items():
        d = p["dom"]
        # tela com noindex (interna) não aparece no Google: descrição, canonical, og e JSON-LD não se aplicam
        fora = "noindex" in ((d['robots'] or '') + (p['x_robots_tag'] or ''))
        falta = "n/a (noindex)" if fora else "FALTA"
        linhas.append(f"| {urllib.parse.urlparse(url).path} | {len(d['titulo'] or '')} | {len(d['descricao'] or '') or falta} | {'sim' if d['canonical'] else falta} | "
                      f"{d['robots'] or '—'} / {p['x_robots_tag'] or '—'} | {'sim' if d['og']['imagem'] else falta} | {', '.join(d['jsonld']) or ('—' if fora else 'não tem')} | {d['lang'] or 'FALTA'} | {d['h1']} |")
    linhas += ["", "## Achados por página", ""]
    for p in resultado["paginas"]:
        achados = {k: p[k] for k in ("terceiros", "conteudo_misto", "imagens_formato_ruim", "imagens_acima_de_300kb", "sem_compressao",
                                     "estaticos_sem_cache", "falhas_de_rede", "erros_console") if p[k]}
        if p["dom"]["imagens_sem_alt"]:
            achados["imagens_sem_alt"] = p["dom"]["imagens_sem_alt"]
        if p["dom"]["fontes_pequenas"]:
            achados["fontes_menores_que_12px"] = p["dom"]["fontes_pequenas"]
        if p["largura"] < 768 and p["dom"]["alvos_pequenos"]:
            achados["alvos_de_toque_pequenos"] = p["dom"]["alvos_pequenos"]
        if isinstance(p["axe"], list) and p["axe"]:
            achados["axe"] = p["axe"]
        if achados:
            linhas += [f"### {urllib.parse.urlparse(p['url']).path} — {p['largura']} px", "", "```json",
                       json.dumps(achados, ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(linhas)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--paginas", nargs="*", default=["/"])
    ap.add_argument("--internas", nargs="*", default=[])
    ap.add_argument("--login-url", default="/login")
    ap.add_argument("--email")
    ap.add_argument("--senha")
    ap.add_argument("--campo-email", default="input[type=email], input[name=email], #f-identificador")
    ap.add_argument("--campo-senha", default="input[type=password]")
    ap.add_argument("--larguras", nargs="*", type=int, default=[360, 390, 768, 1440])
    ap.add_argument("--axe", action="store_true")
    ap.add_argument("--saida", default="auditoria")
    args = ap.parse_args()
    os.makedirs(args.saida, exist_ok=True)
    base = args.base.rstrip("/")
    resultado = {"base": base, "quando": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "site": conferir_site(base), "paginas": []}

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        for largura in args.larguras:
            celular = largura < 768
            opcoes = dict(viewport={"width": largura, "height": 844 if celular else 900}, is_mobile=celular, has_touch=celular,
                          device_scale_factor=2 if celular else 1,
                          # o axe-core vem do CDN: a regra de conteúdo (CSP) da página bloquearia. Só com --axe a regra é ignorada
                          # no navegador de teste (o resto da medição não depende dela)
                          bypass_csp=args.axe)
            publico = navegador.new_context(**opcoes)
            for caminho in args.paginas:
                resultado["paginas"].append(auditar_pagina(publico, base + caminho, largura, args.saida, args.axe))
            publico.close()
            if args.internas and args.email and args.senha:
                logado = navegador.new_context(**opcoes)
                entrar(logado, base, args)
                for caminho in args.internas:
                    resultado["paginas"].append(auditar_pagina(logado, base + caminho, largura, args.saida, args.axe))
                logado.close()
            print(f"largura {largura}: ok", flush=True)
        navegador.close()

    with open(os.path.join(args.saida, "auditoria.json"), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.saida, "auditoria.md"), "w", encoding="utf-8") as f:
        f.write(markdown(resultado))
    print("relatório:", os.path.join(args.saida, "auditoria.md"))


if __name__ == "__main__":
    sys.exit(main())
