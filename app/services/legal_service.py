"""
[back-19-lgpd] TERMOS DE USO e POLÍTICA DE PRIVACIDADE: as páginas públicas /termos e /privacidade.

Os dois textos ficam em app/legal/, em Markdown (o mesmo formato dos documentos do projeto), para o
Adauto e o advogado editarem sem mexer em código. Este arquivo lê o texto e transforma em HTML.

Não foi usada biblioteca de Markdown (seria dependência nova): o leitor abaixo entende só o que os
dois textos usam: títulos, parágrafos, listas, tabelas, citação, negrito, itálico e link. TUDO o que
vem do arquivo é escapado antes de virar HTML, então o texto não consegue injetar código na página.

`VERSAO` é o que fica gravado no cadastro de quem cria a conta ("aceitou a versão tal, em tal dia").
SEMPRE que um dos dois textos mudar de conteúdo, troque a VERSAO.
"""
import os
import re

from markupsafe import Markup, escape

# [back-21-textos-legais] antes: '0.2-2026-10-13'. Mudou porque os textos ganharam os dados de quem oferece o Vale Tec
# (razão social, CNPJ, cidade e e-mail de contato).
# [back-26-lgpd-final] antes: '0.3-2026-10-13'. Mudou porque os textos passaram a descrever o teste grátis, o pagamento, o bloqueio,
# o acesso dos administradores e o suporte sem horário fixo.
# [back-32-textos-legais-final] antes: '0.4-2026-10-14' (versão preliminar). A 1.0 tem domínio, e-mails, hospedagem, e-mail e preços
VERSAO = '1.0-2026-10-17'
PASTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'legal')
DOCUMENTOS = {
    'termos': ('termos-de-uso.md', 'Termos de Uso'),
    'privacidade': ('politica-de-privacidade.md', 'Política de Privacidade'),
}
# para onde vai um link de um texto para o outro (o destino escrito no Markdown -> o endpoint)
LINKS_INTERNOS = {'politica-de-privacidade': 'legal.privacidade', 'termos-de-uso': 'legal.termos'}


def _em_linha(texto, url_para):
    """Negrito, itálico, trecho "a definir" e link dentro de uma linha. O texto entra cru e sai escapado."""
    html = str(escape(texto))
    # `[PREENCHER: ...]` é o que só o dono do sistema sabe (razão social, CNPJ, e-mails): aparece como "a definir"
    html = re.sub(r'`\[PREENCHER[^`]*\]`', '<mark>a definir</mark>', html)
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'(?<![\w*])\*([^*\s][^*]*?)\*(?![\w*])', r'<em>\1</em>', html)

    def link(achado):
        rotulo, destino = achado.group(1), achado.group(2)
        if destino in LINKS_INTERNOS:
            return f'<a href="{escape(url_para(LINKS_INTERNOS[destino]))}">{rotulo}</a>'
        if destino.startswith('https://'):
            return f'<a href="{destino}" target="_blank" rel="noopener noreferrer">{rotulo}</a>'
        return rotulo          # qualquer outro destino vira só o texto
    html = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, html)
    # endereço https solto no texto vira link
    html = re.sub(r'(?<!["\'>])(https://[^\s<]+[^\s<.,;)])', r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', html)
    return html


def para_html(markdown, url_para):
    """Markdown (só o que os textos legais usam) -> HTML seguro. Devolve (título, corpo em Markup)."""
    linhas = markdown.replace('\r\n', '\n').split('\n')
    saida, titulo, i = [], '', 0

    def fecha_paragrafo(pedacos):
        if pedacos:
            saida.append('<p>' + _em_linha(' '.join(pedacos), url_para) + '</p>')
            pedacos.clear()

    paragrafo = []
    while i < len(linhas):
        linha = linhas[i]
        limpa = linha.strip()
        if not limpa:
            fecha_paragrafo(paragrafo)
            i += 1
        elif limpa.startswith('#'):
            fecha_paragrafo(paragrafo)
            nivel = len(limpa) - len(limpa.lstrip('#'))
            texto = limpa[nivel:].strip()
            if nivel == 1:
                titulo = texto
            else:
                # o título do documento (#) é o <h2> da página; as seções (##) viram <h3> e as subseções (###), <h4>
                marca = f'h{min(nivel + 1, 5)}'
                saida.append(f'<{marca}>{_em_linha(texto, url_para)}</{marca}>')
            i += 1
        elif limpa.startswith('>'):
            fecha_paragrafo(paragrafo)
            saida.append('<p class="legal-aviso">' + _em_linha(limpa.lstrip('> ').strip(), url_para) + '</p>')
            i += 1
        elif limpa.startswith('|'):
            fecha_paragrafo(paragrafo)
            tabela = []
            while i < len(linhas) and linhas[i].strip().startswith('|'):
                tabela.append([c.strip() for c in linhas[i].strip().strip('|').split('|')])
                i += 1
            corpo = [l for l in tabela[1:] if not all(re.fullmatch(r':?-+:?', c or '-') for c in l)]
            # [back-34-auditoria-front] antes: <div class="legal-tabela"> sem foco. A tabela rola de lado no celular, e quem usa teclado não conseguia
            # rolar (axe-core: scrollable-region-focusable, gravidade séria). Agora a área recebe foco pelo Tab e tem um nome
            # próprio (número e colunas): duas áreas com o mesmo nome confundem quem navega pelo leitor de tela.
            numero = sum('class="legal-tabela"' in parte for parte in saida) + 1
            nome = escape(f"Tabela {numero}: {', '.join(re.sub(r'[*_`]', '', c) for c in tabela[0])}")
            saida.append(f'<div class="legal-tabela" tabindex="0" role="region" aria-label="{nome}"><table><thead><tr>' + ''.join(f'<th>{_em_linha(c, url_para)}</th>' for c in tabela[0])
                         + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{_em_linha(c, url_para)}</td>' for c in l) + '</tr>' for l in corpo)
                         + '</tbody></table></div>')
        elif re.match(r'(-|\*|\d+\.)\s', limpa):
            fecha_paragrafo(paragrafo)
            ordenada = limpa[0].isdigit()
            itens = []            # [(texto, [subitens])]
            while i < len(linhas) and re.match(r'\s*(-|\*|\d+\.)\s', linhas[i]):
                texto = re.sub(r'^\s*(-|\*|\d+\.)\s+', '', linhas[i])
                if linhas[i].startswith(('  ', '\t')) and itens:
                    itens[-1][1].append(texto)
                else:
                    itens.append((texto, []))
                i += 1
            marca = 'ol' if ordenada else 'ul'
            saida.append(f'<{marca}>' + ''.join(
                '<li>' + _em_linha(t, url_para) + ('<ul>' + ''.join(f'<li>{_em_linha(s, url_para)}</li>' for s in sub) + '</ul>' if sub else '') + '</li>'
                for t, sub in itens) + f'</{marca}>')
        else:
            paragrafo.append(limpa)
            i += 1
    fecha_paragrafo(paragrafo)
    return titulo, Markup('\n'.join(saida))


def pagina(chave, url_para):
    """O contexto de templates/legal/pagina.html para 'termos' ou 'privacidade'."""
    arquivo, nome = DOCUMENTOS[chave]
    with open(os.path.join(PASTA, arquivo), encoding='utf-8') as f:
        titulo, corpo = para_html(f.read(), url_para)
    outra = 'privacidade' if chave == 'termos' else 'termos'
    return {'titulo': titulo or nome, 'nome': nome, 'corpo': corpo, 'versao': VERSAO,
            'outro': {'nome': DOCUMENTOS[outra][1], 'endpoint': f'legal.{outra}'}}
