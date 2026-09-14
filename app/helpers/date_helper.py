import os
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context


def _fuso():
    nome = current_app.config.get("APP_TIMEZONE") if has_app_context() else None
    return ZoneInfo(nome or os.getenv("APP_TIMEZONE", "America/Sao_Paulo"))


def hoje():
    """Data de hoje no fuso da academia (não no fuso do servidor)."""
    return datetime.now(_fuso()).date()


def agora_utc():
    """Datetime naive em UTC (as colunas DateTime do projeto não guardam fuso)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def is_aniversariante(data_nascimento, referencia=None):
    if not data_nascimento:
        return False

    hoje_data = referencia or hoje()
    return (
        data_nascimento.day == hoje_data.day
        and data_nascimento.month == hoje_data.month
    )


def dias_ate_aniversario(data_nascimento, referencia=None):
    """Quantos dias faltam para o próximo aniversário (0 = hoje)."""
    if not data_nascimento:
        return None

    hoje_data = referencia or hoje()
    aniversario = _aniversario_no_ano(data_nascimento, hoje_data.year)
    if aniversario < hoje_data:
        aniversario = _aniversario_no_ano(data_nascimento, hoje_data.year + 1)
    return (aniversario - hoje_data).days


def _aniversario_no_ano(data_nascimento, ano):
    try:
        return data_nascimento.replace(year=ano)
    except ValueError:
        # nascido em 29/02 comemora em 01/03 nos anos não bissextos
        return date(ano, 3, 1)
