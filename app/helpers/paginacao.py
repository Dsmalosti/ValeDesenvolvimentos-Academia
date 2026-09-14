import math


class Paginacao:
    """Paginação simples sobre uma lista já filtrada em memória."""

    def __init__(self, itens, pagina, por_pagina):
        self.total = len(itens)
        self.por_pagina = por_pagina
        self.paginas = max(1, math.ceil(self.total / por_pagina))
        self.pagina = min(max(1, pagina or 1), self.paginas)

        inicio = (self.pagina - 1) * por_pagina
        self.itens = itens[inicio:inicio + por_pagina]
        self.inicio = inicio + 1 if self.total else 0
        self.fim = inicio + len(self.itens)

    @property
    def tem_anterior(self):
        return self.pagina > 1

    @property
    def tem_proxima(self):
        return self.pagina < self.paginas
