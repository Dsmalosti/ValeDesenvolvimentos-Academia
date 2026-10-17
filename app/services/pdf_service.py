"""
[back-31-pdf-ficha-avaliacao] O DESENHO dos PDFs que a academia manda para o aluno: a ficha de treino e o resultado da
avaliação física. Pedido do Adauto (17/10/2026): "fichas e avaliações em PDF para mandar para o aluno, com formatação bonita".

Quem decide O QUE vai no PDF são os serviços (treino_service.dados_para_o_pdf e avaliacao_service.dados_para_o_pdf).
Aqui só se decide COMO fica na página. O gerador de PDF em si está em helpers/pdf.py.

Visual: as cores do front (tokens.css): faixa azul-marinho no topo com o nome da academia, amarelo de destaque,
cartões com borda clara, linhas zebradas. Página A4 em pé. Rodapé com a data e "Página X de Y" em todas as páginas.
"""
import unicodedata
from datetime import date

from app.helpers.pdf import PDF
from app.services import avaliacao_service, treino_service

# Cores (as mesmas de static/css/tokens.css, tema claro)
NAVY, AMARELO, AZUL, AZUL_FUNDO = '#0B3456', '#F7BE23', '#1977C4', '#E7F1F8'
TEXTO, SUAVE, BORDA, ZEBRA = '#102637', '#546E83', '#D3DFE9', '#F6F9FB'
VERDE, VERMELHO, AMARELO_FUNDO, AZUL_CLARO = '#12855F', '#C9453D', '#FEF3D8', '#C8DDEF'

MARGEM = 40
LARGURA_UTIL = PDF.LARGURA - 2 * MARGEM
LIMITE_DE_BAIXO = PDF.ALTURA - 64          # abaixo disso fica o rodapé: conteúdo novo vai para a página seguinte


def nome_do_arquivo(prefixo, nome):
    """'ficha', 'Ana Souza' -> 'ficha-ana-souza.pdf' (sem acento e sem espaço, para não quebrar no WhatsApp)."""
    simples = unicodedata.normalize('NFKD', nome or 'aluno').encode('ascii', 'ignore').decode().lower()
    simples = '-'.join(''.join(c if c.isalnum() else ' ' for c in simples).split())[:40] or 'aluno'
    return f'{prefixo}-{simples}.pdf'


def _cabecalho(pdf, rotulo, academia, aluno, linha_da_direita):
    """A faixa do topo da primeira página. Devolve o y onde o conteúdo começa."""
    pdf.retangulo(0, 0, PDF.LARGURA, 104, cor=NAVY)
    pdf.retangulo(MARGEM, 30, 4, 46, cor=AMARELO, raio=2)
    pdf.texto(MARGEM + 14, 44, rotulo.upper(), tamanho=8.5, negrito=True, cor=AMARELO)
    pdf.texto(MARGEM + 14, 70, pdf.cortar(academia, LARGURA_UTIL * 0.55, 20, True), tamanho=20, negrito=True, cor='#FFFFFF')
    direita = PDF.LARGURA - MARGEM
    # nome comprido: a letra diminui até 10 pt para caber; se nem assim couber, corta com reticências
    espaco, tamanho = LARGURA_UTIL * 0.44, 14
    while tamanho > 10 and pdf.largura(aluno, tamanho, True) > espaco:
        tamanho -= 0.5
    pdf.texto(direita, 52, pdf.cortar(aluno, espaco, tamanho, True), tamanho=tamanho, negrito=True, cor='#FFFFFF', alinhar='direita')
    pdf.texto(direita, 70, linha_da_direita, tamanho=9.5, cor=AZUL_CLARO, alinhar='direita')
    return 132


def _cabecalho_curto(pdf, academia, aluno):
    """O topo das páginas seguintes: uma linha só, para lembrar de quem é."""
    pdf.texto(MARGEM, 40, academia, tamanho=9, negrito=True, cor=NAVY)
    pdf.texto(PDF.LARGURA - MARGEM, 40, aluno, tamanho=9, cor=SUAVE, alinhar='direita')
    pdf.linha(MARGEM, 50, PDF.LARGURA - MARGEM, 50, cor=BORDA)
    return 74


def _rodape(texto_da_esquerda):
    def desenhar(pdf, numero, total):
        y = PDF.ALTURA - 34
        pdf.linha(MARGEM, y - 14, PDF.LARGURA - MARGEM, y - 14, cor=BORDA)
        pdf.texto(MARGEM, y, texto_da_esquerda, tamanho=8, cor=SUAVE)
        pdf.texto(PDF.LARGURA - MARGEM, y, f'Página {numero} de {total}', tamanho=8, cor=SUAVE, alinhar='direita')
    return desenhar


def _etiquetas(pdf, y, pares):
    """Linha de "etiquetas" (rótulo + valor) logo abaixo do cabeçalho. Quebra para a linha de baixo se não couber."""
    x = MARGEM
    for rotulo, valor in pares:
        largura = pdf.largura(rotulo, 8, True) + pdf.largura(valor, 9.5) + 26
        if x + largura > PDF.LARGURA - MARGEM:
            x, y = MARGEM, y + 30
        pdf.retangulo(x, y, largura, 22, cor=AZUL_FUNDO, raio=11)
        pdf.texto(x + 10, y + 14.5, rotulo, tamanho=8, negrito=True, cor=AZUL)
        pdf.texto(x + 16 + pdf.largura(rotulo, 8, True), y + 14.5, valor, tamanho=9.5, cor=TEXTO)
        x += largura + 8
    return y + 40


# ------------------------------------------------------------------ ficha de treino
# Colunas da tabela de exercícios: (título, onde começa (x), largura, alinhamento)
_COLUNAS = [('#', MARGEM + 12, 18, 'centro'), ('Exercício', MARGEM + 34, 228, 'esquerda'), ('Séries', MARGEM + 270, 46, 'centro'),
            ('Repetições', MARGEM + 318, 66, 'centro'), ('Carga', MARGEM + 386, 62, 'centro'), ('Descanso', MARGEM + 450, 60, 'centro')]
_ALTURA_DA_LINHA = 32


def _titulo_do_treino(pdf, y, treino, continuacao=False):
    pdf.retangulo(MARGEM, y, LARGURA_UTIL, 34, cor=NAVY, raio=8)
    pdf.retangulo(MARGEM + 8, y + 7, 20, 20, cor=AMARELO, raio=5)
    pdf.texto(MARGEM + 18, y + 21.5, treino['letra'], tamanho=11, negrito=True, cor=NAVY, alinhar='centro')
    titulo = f"Treino {treino['letra']} · {treino['nome']}" + (' (continuação)' if continuacao else '')
    pdf.texto(MARGEM + 38, y + 21.5, pdf.cortar(titulo, LARGURA_UTIL - 150, 11.5, True), tamanho=11.5, negrito=True, cor='#FFFFFF')
    total = len(treino['itens'])
    pdf.texto(PDF.LARGURA - MARGEM - 12, y + 21.5, f"{total} {'exercício' if total == 1 else 'exercícios'}", tamanho=9,
              cor=AZUL_CLARO, alinhar='direita')
    y += 34 + 16
    for titulo, x, largura, alinhar in _COLUNAS:
        ancora = x + largura / 2 if alinhar == 'centro' else x
        pdf.texto(ancora, y, titulo.upper(), tamanho=7.5, negrito=True, cor=SUAVE, alinhar=alinhar)
    return y + 8


def _linha_do_exercicio(pdf, y, numero, item):
    if numero % 2 == 0:
        pdf.retangulo(MARGEM, y, LARGURA_UTIL, _ALTURA_DA_LINHA, cor=ZEBRA, raio=6)
    meio = y + _ALTURA_DA_LINHA / 2
    valores = [str(numero), None, str(item['series']), str(item['repeticoes']), str(item['carga']), str(item['descanso'])]
    for (titulo, x, largura, alinhar), valor in zip(_COLUNAS, valores):
        if valor is None:     # a coluna do exercício: nome em negrito e o grupo muscular embaixo, menor
            pdf.texto(x, meio - 1.5, pdf.cortar(item['nome'], largura, 10.5, True), tamanho=10.5, negrito=True, cor=TEXTO)
            pdf.texto(x, meio + 10, pdf.cortar(item['grupo'], largura, 8), tamanho=8, cor=SUAVE)
        else:
            negrito = titulo in ('#', 'Séries', 'Repetições')
            pdf.texto(x + largura / 2, meio + 3.5, pdf.cortar(valor, largura, 10, negrito), tamanho=10, negrito=negrito,
                      cor=NAVY if titulo == '#' else TEXTO, alinhar='centro')
    return y + _ALTURA_DA_LINHA


def ficha_em_pdf(aluno, ficha, conta):
    """Os bytes do PDF da ficha de treino do aluno, e o nome do arquivo."""
    d = treino_service.dados_para_o_pdf(aluno, ficha)
    pdf = PDF(titulo=f"Ficha de treino · {d['aluno']}")
    pdf.nova_pagina()
    y = _cabecalho(pdf, 'Ficha de treino', conta.nome, d['aluno'], f"Válida até {d['ficha']['valida']}")
    y = _etiquetas(pdf, y, [('Ficha', d['ficha']['nome']), ('Objetivo', d['ficha']['objetivo']),
                            ('Atualizada', d['ficha']['atualizada'])])

    if not d['treinos']:
        pdf.texto(MARGEM, y + 10, 'Esta ficha ainda não tem exercícios.', tamanho=11, cor=SUAVE)

    for treino in d['treinos']:
        # o título e pelo menos dois exercícios precisam caber juntos; senão, o treino começa na página seguinte
        if y + 58 + 2 * _ALTURA_DA_LINHA > LIMITE_DE_BAIXO:
            pdf.nova_pagina()
            y = _cabecalho_curto(pdf, conta.nome, d['aluno'])
        y = _titulo_do_treino(pdf, y, treino)
        for numero, item in enumerate(treino['itens'], start=1):
            if y + _ALTURA_DA_LINHA > LIMITE_DE_BAIXO:
                pdf.nova_pagina()
                y = _titulo_do_treino(pdf, _cabecalho_curto(pdf, conta.nome, d['aluno']), treino, continuacao=True)
            y = _linha_do_exercicio(pdf, y, numero, item)
        y += 22

    # dica final, se couber na página
    if d['treinos'] and y + 52 <= LIMITE_DE_BAIXO:
        pdf.retangulo(MARGEM, y, LARGURA_UTIL, 44, cor=AMARELO_FUNDO, raio=8)
        pdf.texto(MARGEM + 14, y + 18, 'Dúvida em algum exercício?', tamanho=9.5, negrito=True, cor=TEXTO)
        contato = f' Telefone: {conta.telefone}.' if conta.telefone else ''
        pdf.texto(MARGEM + 14, y + 32, pdf.cortar(f'Fale com a equipe da {conta.nome} antes de mudar a carga ou a ordem.{contato}',
                                                  LARGURA_UTIL - 28, 9), tamanho=9, cor=SUAVE)

    dados = pdf.gerar(_rodape(f'Ficha gerada pelo Vale Tec em {date.today():%d/%m/%Y}'))
    return dados, nome_do_arquivo('ficha', d['aluno'])


# ------------------------------------------------------------------ avaliação física
def _destaques(pdf, y, destaques):
    """Os quatro números grandes (peso, altura, IMC, cintura)."""
    espaco = 10
    largura = (LARGURA_UTIL - espaco * (len(destaques) - 1)) / len(destaques)
    for i, (rotulo, valor, unidade) in enumerate(destaques):
        x = MARGEM + i * (largura + espaco)
        pdf.retangulo(x, y, largura, 66, cor='#FFFFFF', raio=10, borda=BORDA)
        pdf.texto(x + 14, y + 22, rotulo.upper(), tamanho=7.5, negrito=True, cor=SUAVE)
        pdf.texto(x + 14, y + 50, valor, tamanho=22, negrito=True, cor=NAVY)
        if unidade and valor != '—':
            pdf.texto(x + 18 + pdf.largura(valor, 22, True), y + 50, unidade, tamanho=10, cor=SUAVE)
    return y + 66 + 26


def avaliacao_em_pdf(avaliacao, conta):
    """Os bytes do PDF do resultado da avaliação física, e o nome do arquivo."""
    d = avaliacao_service.dados_para_o_pdf(avaliacao)
    pdf = PDF(titulo=f"Avaliação física · {d['aluno']}")
    pdf.nova_pagina()
    y = _cabecalho(pdf, 'Avaliação física', conta.nome, d['aluno'], f"Avaliação de {d['data']}")
    etiquetas = [('Avaliador', d['avaliador'])]
    etiquetas.append(('Comparada com', f"{d['anterior']} ({d['dias']} dias antes)") if d['anterior'] else ('Comparação', 'primeira avaliação'))
    y = _etiquetas(pdf, y, etiquetas)
    y = _destaques(pdf, y, d['destaques'])

    # tabela de medidas
    pdf.texto(MARGEM, y, 'Medidas', tamanho=13, negrito=True, cor=NAVY)
    y += 18
    tem_anterior = any(m['antes'] is not None for m in d['medidas'])
    colunas = ([('Medida', MARGEM + 12, 'esquerda'), ('Anterior', MARGEM + 300, 'direita'), ('Agora', MARGEM + 390, 'direita'),
                ('Variação', MARGEM + LARGURA_UTIL - 12, 'direita')] if tem_anterior
               else [('Medida', MARGEM + 12, 'esquerda'), ('Valor', MARGEM + LARGURA_UTIL - 12, 'direita')])
    pdf.retangulo(MARGEM, y, LARGURA_UTIL, 26, cor=AZUL_FUNDO, raio=6)
    for titulo, x, alinhar in colunas:
        pdf.texto(x, y + 17, titulo.upper(), tamanho=7.5, negrito=True, cor=AZUL, alinhar=alinhar)
    y += 26
    for i, m in enumerate(d['medidas']):
        if y + 28 > LIMITE_DE_BAIXO:
            pdf.nova_pagina()
            y = _cabecalho_curto(pdf, conta.nome, d['aluno'])
        if i % 2 == 1:
            pdf.retangulo(MARGEM, y, LARGURA_UTIL, 28, cor=ZEBRA, raio=6)
        base = y + 18
        un = f" {m['unidade']}" if m['unidade'] else ''
        pdf.texto(colunas[0][1], base, m['nome'], tamanho=10, cor=TEXTO)
        if tem_anterior:
            pdf.texto(colunas[1][1], base, (m['antes'] + un) if m['antes'] else '—', tamanho=10, cor=SUAVE, alinhar='direita')
            pdf.texto(colunas[2][1], base, m['agora'] + un, tamanho=10, negrito=True, cor=TEXTO, alinhar='direita')
            cor = {'bom': VERDE, 'ruim': VERMELHO}.get(m['tom'], SUAVE)
            if m['delta'] is None:
                variacao = '—'                                   # a medida não foi feita na avaliação anterior
            elif m['delta'].lstrip('+-').replace('0', '').replace(',', '') == '':
                variacao = 'sem mudança'                         # "0", "0,0", "-0,0"...
            else:
                variacao = m['delta'] + un
            pdf.texto(colunas[3][1], base, variacao, tamanho=10, negrito=bool(m['tom']), cor=cor, alinhar='direita')
        else:
            pdf.texto(colunas[1][1], base, m['agora'] + un, tamanho=10, negrito=True, cor=TEXTO, alinhar='direita')
        y += 28
    if tem_anterior:
        y += 8
        pdf.texto(MARGEM, y + 6, 'Verde: mudou na direção do objetivo. Vermelho: na direção contrária. Cinza: só para acompanhar.',
                  tamanho=8, cor=SUAVE)
    y += 30

    # anotação do avaliador
    linhas = pdf.quebrar(d['nota'] or 'Sem anotação.', LARGURA_UTIL - 32, 10)
    altura = 40 + 14 * len(linhas)
    if y + altura > LIMITE_DE_BAIXO:
        pdf.nova_pagina()
        y = _cabecalho_curto(pdf, conta.nome, d['aluno'])
    pdf.retangulo(MARGEM, y, LARGURA_UTIL, altura, cor='#FFFFFF', raio=10, borda=BORDA)
    pdf.texto(MARGEM + 16, y + 22, 'Anotação do avaliador', tamanho=10, negrito=True, cor=NAVY)
    for n, linha in enumerate(linhas):
        pdf.texto(MARGEM + 16, y + 40 + 14 * n, linha, tamanho=10, cor=TEXTO)
    y += altura + 18

    aviso = 'Estes números são medidas, não um diagnóstico. Para qualquer questão de saúde, procure um médico.'
    if y + 14 > LIMITE_DE_BAIXO:
        pdf.nova_pagina()
        y = _cabecalho_curto(pdf, conta.nome, d['aluno'])
    pdf.texto(MARGEM, y, aviso, tamanho=8.5, cor=SUAVE)

    dados = pdf.gerar(_rodape(f'Avaliação gerada pelo Vale Tec em {date.today():%d/%m/%Y}'))
    return dados, nome_do_arquivo('avaliacao', d['aluno'])
