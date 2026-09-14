from decimal import Decimal

from app.helpers.date_helper import hoje


def moeda(valor):
    if valor is None:
        return "—"
    texto = f"{Decimal(valor):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def data_br(valor):
    return valor.strftime("%d/%m/%Y") if valor else "—"


def iniciais(nome):
    partes = (nome or "").split()
    if not partes:
        return "?"
    letras = partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")
    return letras.upper()


def dias_relativos(dias):
    if dias is None:
        return "—"
    if dias == 0:
        return "hoje"
    if dias == 1:
        return "amanhã"
    if dias == -1:
        return "ontem"
    if dias > 1:
        return f"em {dias} dias"
    return f"há {abs(dias)} dias"


_DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]


def data_extenso(valor):
    if not valor:
        return ""
    return f"{_DIAS[valor.weekday()].capitalize()}, {valor.day} de {_MESES[valor.month - 1]}"


def init_app(app):
    from app.models import DIAS_SEMANA, GRUPOS_MUSCULARES

    app.add_template_filter(moeda, "moeda")
    app.add_template_filter(data_br, "data_br")
    app.add_template_filter(data_extenso, "data_extenso")
    app.add_template_filter(iniciais, "iniciais")
    app.add_template_filter(dias_relativos, "dias_relativos")

    @app.context_processor
    def contexto_global():
        data_hoje = hoje()
        return {
            "hoje_data": data_hoje,
            "ano_atual": data_hoje.year,
            "DIAS_SEMANA": DIAS_SEMANA,
            "GRUPOS_MUSCULARES": GRUPOS_MUSCULARES,
        }
