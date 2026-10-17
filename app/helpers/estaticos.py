"""
[back-34-auditoria-front] CACHE dos arquivos estáticos (CSS, JS, imagens) com "carimbo de versão" na URL.

Antes: o Flask servia os estáticos sem `Cache-Control` de prazo; o navegador tornava a pedir o app.css (95 KB), o app.js
(46 KB) e os outros a cada tela. A auditoria de 17/10/2026 mediu de 280 a 445 KB por tela, quase tudo repetido.

Agora:
  - todo `url_for('static', filename=...)` ganha `?v=<10 letras do resumo do arquivo>`. Mudou o arquivo, muda o carimbo,
    muda a URL, e o navegador baixa a versão nova na hora;
  - por isso o navegador pode guardar cada arquivo por 1 ano (`SEND_FILE_MAX_AGE_DEFAULT`).

Nenhum template precisou mudar: o Flask chama `url_defaults` toda vez que monta uma URL.

Exceção: as FONTES (`fonts/...`). O base.html pré-carrega duas fontes pelo `url_for`, mas o tokens.css chama as mesmas
fontes por caminho relativo, sem carimbo. Se só o pré-carregamento tivesse carimbo, o navegador baixaria cada fonte duas
vezes. Fonte não muda; fica com o cache de 1 ano e o mesmo endereço nos dois lugares.

No modo de desenvolvimento (`flask run --debug`), o carimbo é recalculado a cada pedido e o cache fica desligado:
quem mexe no CSS vê a mudança na hora.
"""
import hashlib
import os

UM_ANO = 365 * 24 * 60 * 60
SEM_CARIMBO = ('fonts/',)


def ligar(app):
    """Chamado uma vez, no create_app()."""
    carimbos = {}
    if not app.debug:
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = UM_ANO

    @app.url_defaults
    def carimbar(endpoint, valores):
        if endpoint != 'static' or 'v' in valores:
            return
        nome = valores.get('filename') or ''
        if not nome or nome.startswith(SEM_CARIMBO):
            return
        if nome not in carimbos or app.debug:
            try:
                with open(os.path.join(app.static_folder, nome), 'rb') as arquivo:
                    carimbos[nome] = hashlib.sha256(arquivo.read()).hexdigest()[:10]
            except OSError:
                return              # arquivo que não existe: a URL sai sem carimbo e o 404 aparece como antes
        valores['v'] = carimbos[nome]
