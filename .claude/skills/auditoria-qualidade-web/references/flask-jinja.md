# Correções comuns em projetos Flask + Jinja

Receitas para os achados mais frequentes da auditoria num projeto Flask com templates Jinja. Adapte aos nomes do projeto e às regras dele (branches, comentários, autorizações).

## Carimbo de versão nos arquivos estáticos (cache longo sem CSS velho)

Sem mexer em nenhum template: o Flask chama `url_defaults` toda vez que um `url_for` monta um endereço. Para `static`, acrescente `?v=` com um resumo do arquivo.

```python
import hashlib, os

def ligar_carimbo_nos_estaticos(app):
    carimbos = {}

    @app.url_defaults
    def carimbar(endpoint, valores):
        if endpoint != 'static' or 'filename' not in valores or 'v' in valores:
            return
        nome = valores['filename']
        if nome not in carimbos or app.debug:              # em desenvolvimento, recalcula (o arquivo muda o tempo todo)
            caminho = os.path.join(app.static_folder, nome)
            try:
                with open(caminho, 'rb') as f:
                    carimbos[nome] = hashlib.sha256(f.read()).hexdigest()[:10]
            except OSError:
                return
        valores['v'] = carimbos[nome]

    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000      # 1 ano: a URL muda quando o arquivo muda
```

Cuidado com arquivos que o navegador pede **sem** passar pelo `url_for`:
- `manifest.webmanifest` e os ícones citados dentro dele;
- `fetch` em JS com caminho fixo;
- `url()` dentro do CSS (fontes, imagens).

Esses arquivos não ganham o carimbo e ficam presos no cache de 1 ano. Resolva de um destes jeitos:
- dê a eles um cache curto (rota própria, ou `send_static_file` com `max_age`);
- mantenha o `SEND_FILE_MAX_AGE_DEFAULT` menor (ex.: 1 dia);
- carimbe essas referências também.

## `robots.txt` e `sitemap.xml` por rota

```python
@bp.route('/robots.txt')
def robots():
    linhas = ['User-agent: *', 'Disallow: /', 'Allow: /$', 'Allow: /login', 'Allow: /termos', 'Allow: /privacidade',
              f"Sitemap: {url_for('seo.sitemap', _external=True)}"]
    return Response('\n'.join(linhas) + '\n', mimetype='text/plain')

@bp.route('/sitemap.xml')
def sitemap():
    urls = [url_for(e, _external=True) for e in ('auth.login', 'legal.termos', 'legal.privacidade')]
    corpo = ''.join(f'<url><loc>{u}</loc></url>' for u in urls)
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{corpo}</urlset>',
                    mimetype='application/xml')
```

Atrás de proxy (Render, Heroku etc.), `_external=True` só gera `https://` se o `ProxyFix` estiver ligado.

## Metadados no template-base

```jinja
<title>{% block titulo_pagina %}{{ pagina_titulo ~ ' · ' if pagina_titulo }}Nome do Produto{% endblock %}</title>
<meta name="description" content="{% block descricao %}Descrição padrão de 120 a 160 caracteres.{% endblock %}">
{% if pagina_publica %}<link rel="canonical" href="{{ request.base_url }}">{% else %}<meta name="robots" content="noindex">{% endif %}
```

Telas internas também podem levar o `noindex` por cabeçalho, num `after_request` que testa se a rota pede login. Assim nenhuma tela nova esquece.

## Compressão

O Flask não comprime as respostas. Em produção, quase sempre quem comprime é o proxy da hospedagem: confira `Content-Encoding` na produção antes de adicionar uma dependência (ex.: Flask-Compress). Se a hospedagem não comprimir, a dependência pede autorização.

## Arquivo estático sem uso

```bash
for f in $(cd app/static && find . -type f | sed 's|^\./||'); do
  grep -rqF "$f" app/templates app/static app/*.py || echo "SEM USO: $f"
done
```

Antes de apagar, confira:
- referências montadas por variável (ex.: `url_for('static', filename='img/' ~ nome)`);
- o `manifest.webmanifest`;
- o CSS (fontes e `url()`).
