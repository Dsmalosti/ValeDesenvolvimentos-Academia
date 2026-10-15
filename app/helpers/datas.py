"""
[back-24-assinatura] Contas com datas que o Python não faz sozinho.
"""
import calendar
from datetime import date


def somar_meses(dia, meses):
    """
    O mesmo dia, `meses` meses depois. Se o mês de destino for mais curto, cai no último dia dele:
    31/01 + 1 mês = 28/02 (ou 29/02 em ano bissexto).
    """
    total = dia.month - 1 + meses
    ano, mes = dia.year + total // 12, total % 12 + 1
    return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))
