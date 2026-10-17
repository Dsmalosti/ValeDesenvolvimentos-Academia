"""
[back-31-pdf-ficha-avaliacao] Gerador de PDF SIMPLES, sem biblioteca nova (só a biblioteca padrão do Python).

Por que não uma biblioteca pronta (fpdf2, reportlab, weasyprint): cada uma traria de 2 a 4 pacotes novos para o
servidor (Pillow, fontTools...), e a regra 4 do CLAUDE.md pede autorização para dependência. A ficha e a avaliação
só precisam de texto, retângulos e linhas; isso o formato PDF faz com poucas instruções, escritas aqui.

O que este arquivo sabe fazer:
  - páginas A4 em pé;
  - texto nas fontes padrão do PDF (Helvetica e Helvetica negrito: todo leitor de PDF já tem, nada é embutido,
    e o arquivo fica com poucos KB), em qualquer cor, alinhado à esquerda, ao centro ou à direita;
  - medir a largura de um texto e quebrar em linhas;
  - retângulos (com ou sem canto arredondado) e linhas.

Coordenadas: em PONTOS (1 cm = 28,35 pt), com a origem no canto de CIMA à esquerda e o y crescendo para baixo, como
numa tela. (O PDF de verdade conta o y de baixo para cima; a conversão é feita aqui dentro.)

Acentos: as fontes padrão usam a tabela de letras do Windows (cp1252), que tem todo o português (á, ç, õ, ê...).
Letra fora dela (emoji, por exemplo) vira "?".

Uso:
    pdf = PDF(titulo='Ficha de treino')
    pdf.nova_pagina()
    pdf.retangulo(0, 0, pdf.LARGURA, 80, cor='#0B3456')
    pdf.texto(40, 50, 'Academia Forte', tamanho=18, negrito=True, cor='#FFFFFF')
    dados = pdf.gerar()           # bytes do arquivo .pdf
"""
import zlib
from datetime import datetime

# Largura de cada letra, em milésimos do tamanho da fonte, das letras 32 a 255 da tabela cp1252.
# São as medidas da Helvetica (iguais às do Arial, de onde foram lidas). Servem para alinhar à direita e quebrar linhas.
_LARGURAS_NORMAL = (
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584, 750,
    556, 0, 222, 556, 333, 1000, 556, 556, 333, 1000, 667, 333, 1000, 0, 611, 0,
    0, 222, 222, 333, 333, 350, 556, 1000, 333, 1000, 500, 333, 944, 0, 500, 667,
    278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 552,
    400, 549, 333, 333, 333, 576, 537, 333, 333, 333, 365, 556, 834, 834, 834, 611,
    667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 549, 611, 556, 556, 556, 556, 500, 556, 500,
)
_LARGURAS_NEGRITO = (
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584, 750,
    556, 0, 278, 556, 500, 1000, 556, 556, 333, 1000, 667, 333, 1000, 0, 611, 0,
    0, 278, 278, 500, 500, 350, 556, 1000, 333, 1000, 556, 333, 944, 0, 500, 667,
    278, 333, 556, 556, 556, 556, 280, 556, 333, 737, 370, 556, 584, 333, 737, 552,
    400, 549, 333, 333, 333, 576, 556, 333, 333, 333, 365, 556, 834, 834, 834, 611,
    722, 722, 722, 722, 722, 722, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 556, 556, 556, 556, 556, 278, 278, 278, 278,
    611, 611, 611, 611, 611, 611, 611, 549, 611, 611, 611, 611, 611, 556, 611, 556,
)

# Letras comuns que a cp1252 não tem, trocadas por uma parecida antes de escrever
_TROCAS = {'\u2212': '-', '\u2192': '>', '\u2190': '<', '\u2713': 'v', '\u00a0': ' ', '\u202f': ' ', '\u2009': ' '}

# Curva de Bézier que mais se parece com um quarto de círculo (para os cantos arredondados)
_K = 0.5523


def _bytes(texto):
    """O texto nos bytes da cp1252 (o que as fontes padrão do PDF entendem)."""
    texto = ''.join(_TROCAS.get(c, c) for c in str(texto))
    return texto.encode('cp1252', errors='replace')


def _rgb(cor):
    """'#0B3456' -> '0.043 0.204 0.337' (o PDF quer cada cor de 0 a 1)."""
    cor = cor.lstrip('#')
    return ' '.join(f'{int(cor[i:i + 2], 16) / 255:.3f}' for i in (0, 2, 4))


def _n(valor):
    """Número curto para o PDF (sem zeros sobrando)."""
    return f'{valor:.2f}'.rstrip('0').rstrip('.')


class PDF:
    LARGURA, ALTURA = 595.28, 841.89          # A4 em pé, em pontos

    def __init__(self, titulo='', autor='Vale Tec'):
        self.titulo, self.autor = titulo, autor
        self.paginas = []                       # o "desenho" de cada página (instruções do PDF, em bytes)
        self._atual = -1                        # em qual página o desenho está sendo feito

    # ------------------------------------------------------------------ medidas
    @staticmethod
    def largura(texto, tamanho=10, negrito=False):
        """Largura do texto, em pontos."""
        tabela = _LARGURAS_NEGRITO if negrito else _LARGURAS_NORMAL
        return sum(tabela[b - 32] if b >= 32 else 0 for b in _bytes(texto)) * tamanho / 1000

    def quebrar(self, texto, largura_maxima, tamanho=10, negrito=False):
        """Quebra o texto em linhas que cabem em `largura_maxima` (quebra nos espaços; palavra enorme é cortada)."""
        linhas = []
        for paragrafo in str(texto).split('\n'):
            atual = ''
            for palavra in paragrafo.split():
                tentativa = f'{atual} {palavra}'.strip()
                if self.largura(tentativa, tamanho, negrito) <= largura_maxima:
                    atual = tentativa
                    continue
                if atual:
                    linhas.append(atual)
                while self.largura(palavra, tamanho, negrito) > largura_maxima and len(palavra) > 1:
                    corte = len(palavra)
                    while corte > 1 and self.largura(palavra[:corte], tamanho, negrito) > largura_maxima:
                        corte -= 1
                    linhas.append(palavra[:corte])
                    palavra = palavra[corte:]
                atual = palavra
            linhas.append(atual)
        return linhas

    def cortar(self, texto, largura_maxima, tamanho=10, negrito=False):
        """O texto numa linha só; se não couber, corta e termina com reticências."""
        texto = str(texto)
        if self.largura(texto, tamanho, negrito) <= largura_maxima:
            return texto
        while texto and self.largura(texto + '…', tamanho, negrito) > largura_maxima:
            texto = texto[:-1]
        return texto.rstrip() + '…'

    # ------------------------------------------------------------------ desenho
    def nova_pagina(self):
        self.paginas.append(bytearray())
        self._atual = len(self.paginas) - 1

    def _escrever(self, instrucoes):
        self.paginas[self._atual] += instrucoes.encode('latin-1') if isinstance(instrucoes, str) else instrucoes

    def texto(self, x, y, texto, tamanho=10, negrito=False, cor='#102637', alinhar='esquerda'):
        """Escreve uma linha. `y` é a linha de base do texto (a "pauta" onde as letras se apoiam), medida de cima."""
        if alinhar != 'esquerda':
            w = self.largura(texto, tamanho, negrito)
            x -= w if alinhar == 'direita' else w / 2
        conteudo = _bytes(texto).replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)').replace(b'\r', b'')
        fonte = '/F2' if negrito else '/F1'
        self._escrever(f'BT {_rgb(cor)} rg {fonte} {_n(tamanho)} Tf 1 0 0 1 {_n(x)} {_n(self.ALTURA - y)} Tm (')
        self._escrever(conteudo)
        self._escrever(') Tj ET\n')

    def retangulo(self, x, y, largura, altura, cor='#FFFFFF', raio=0, borda=None, espessura=0.8):
        """Retângulo com o canto de cima à esquerda em (x, y). `borda`: cor do contorno (sem ela, só o preenchimento)."""
        topo, base = self.ALTURA - y, self.ALTURA - y - altura
        r = min(raio, largura / 2, altura / 2)
        if r <= 0:
            caminho = f'{_n(x)} {_n(base)} {_n(largura)} {_n(altura)} re'
        else:
            d, dir_ = r * _K, x + largura
            caminho = ' '.join([
                f'{_n(x + r)} {_n(base)} m',
                f'{_n(dir_ - r)} {_n(base)} l',
                f'{_n(dir_ - r + d)} {_n(base)} {_n(dir_)} {_n(base + r - d)} {_n(dir_)} {_n(base + r)} c',
                f'{_n(dir_)} {_n(topo - r)} l',
                f'{_n(dir_)} {_n(topo - r + d)} {_n(dir_ - r + d)} {_n(topo)} {_n(dir_ - r)} {_n(topo)} c',
                f'{_n(x + r)} {_n(topo)} l',
                f'{_n(x + r - d)} {_n(topo)} {_n(x)} {_n(topo - r + d)} {_n(x)} {_n(topo - r)} c',
                f'{_n(x)} {_n(base + r)} l',
                f'{_n(x)} {_n(base + r - d)} {_n(x + r - d)} {_n(base)} {_n(x + r)} {_n(base)} c h',
            ])
        if borda:
            pintar = 'B' if cor else 'S'
            self._escrever(f'q {_rgb(cor or "#FFFFFF")} rg {_rgb(borda)} RG {_n(espessura)} w {caminho} {pintar} Q\n')
        else:
            self._escrever(f'q {_rgb(cor)} rg {caminho} f Q\n')

    def linha(self, x1, y1, x2, y2, cor='#D3DFE9', espessura=0.8):
        self._escrever(f'q {_rgb(cor)} RG {_n(espessura)} w {_n(x1)} {_n(self.ALTURA - y1)} m {_n(x2)} {_n(self.ALTURA - y2)} l S Q\n')

    # ------------------------------------------------------------------ arquivo
    def gerar(self, rodape=None):
        """
        Monta o arquivo e devolve os bytes. `rodape(pdf, numero, total)` (opcional) é chamado em cada página no fim,
        quando já se sabe quantas páginas são (para escrever "Página 1 de 3").
        """
        if not self.paginas:
            self.nova_pagina()
        if rodape:
            for indice in range(len(self.paginas)):
                self._atual = indice
                rodape(self, indice + 1, len(self.paginas))

        # Objetos do PDF: 1 catálogo, 2 lista de páginas, 3 e 4 as fontes, 5 as informações; depois, página e desenho de cada página
        objetos = [None, None,
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>',
                   None]
        kids = []
        for desenho in self.paginas:
            compactado = zlib.compress(bytes(desenho))
            n_pagina, n_desenho = len(objetos) + 1, len(objetos) + 2
            kids.append(f'{n_pagina} 0 R')
            objetos.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_n(self.LARGURA)} {_n(self.ALTURA)}] '
                           f'/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {n_desenho} 0 R >>'.encode('latin-1'))
            objetos.append(f'<< /Length {len(compactado)} /Filter /FlateDecode >>\nstream\n'.encode('latin-1') + compactado + b'\nendstream')
        objetos[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
        objetos[1] = f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'.encode('latin-1')

        def literal(texto):
            # informações do arquivo em UTF-16 (aceita qualquer letra), escritas em hexadecimal
            return '<FEFF' + str(texto).encode('utf-16-be').hex().upper() + '>'
        agora = datetime.now().strftime('D:%Y%m%d%H%M%S')
        objetos[4] = (f'<< /Title {literal(self.titulo)} /Author {literal(self.autor)} /Producer {literal("Vale Tec")} '
                      f'/CreationDate ({agora}) >>').encode('latin-1')

        saida = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        posicoes = []
        for numero, corpo in enumerate(objetos, start=1):
            posicoes.append(len(saida))
            saida += f'{numero} 0 obj\n'.encode('latin-1') + corpo + b'\nendobj\n'
        inicio_da_tabela = len(saida)
        saida += f'xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n'.encode('latin-1')
        for posicao in posicoes:
            saida += f'{posicao:010d} 00000 n \n'.encode('latin-1')
        saida += (f'trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R /Info 5 0 R >>\n'
                  f'startxref\n{inicio_da_tabela}\n%%EOF\n').encode('latin-1')
        return bytes(saida)
