"""
Dinheiro em reais: ler o que o usuário digita ("1.234,56") e escrever no mesmo formato.

[back-09-cobranca] Criado para a cobrança e os planos usarem a mesma leitura de valor
(a de planos nasceu na back-08, dentro do plano_tela_service.py).
"""
import re
from decimal import Decimal

# "1.234,56", "1234,56", "1234" ou "149,9": milhar com ponto (opcional) e centavos com vírgula
_VALOR_BR = re.compile(r'(\d{1,3}(\.\d{3})+|\d+)(,\d{1,2})?')


def ler_reais(texto):
    """'1.234,56' -> Decimal('1234.56'). Levanta ValueError se não estiver no formato brasileiro."""
    texto = (texto or '').replace('R$', '').strip()
    if not _VALOR_BR.fullmatch(texto):
        # Não "adivinha" formatos: aceitar "149.90" tirando o ponto gravaria R$ 14.990,00.
        raise ValueError(texto)
    return Decimal(texto.replace('.', '').replace(',', '.'))


def reais_txt(valor):
    """1234.5 -> '1.234,50' (sem o 'R$')."""
    return f'{float(valor or 0):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
