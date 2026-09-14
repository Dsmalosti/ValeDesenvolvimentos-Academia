from datetime import date
from decimal import Decimal

import pytest

from app.exceptions import BusinessError
from app.helpers.date_helper import dias_ate_aniversario
from app.helpers.filters import data_extenso, dias_relativos, moeda
from app.helpers.navegacao import url_segura
from app.helpers.validators import cpf_valido, normalizar_cpf, normalizar_telefone


@pytest.mark.parametrize("cpf,esperado", [
    ("529.982.247-25", True),
    ("52998224725", True),
    ("111.111.111-11", False),
    ("529.982.247-24", False),
    ("123", False),
    ("", False),
])
def test_cpf_valido(cpf, esperado):
    assert cpf_valido(cpf) is esperado


def test_normalizacoes():
    assert normalizar_cpf("52998224725") == "529.982.247-25"
    assert normalizar_cpf("  ") is None
    assert normalizar_telefone("1123456789") == "(11) 2345-6789"
    assert normalizar_telefone("(11) 91234 5678") == "(11) 91234-5678"
    assert normalizar_telefone("") is None
    with pytest.raises(BusinessError):
        normalizar_cpf("123.456.789-00")
    with pytest.raises(BusinessError):
        normalizar_telefone("12345")


@pytest.mark.parametrize("destino,seguro", [
    ("/alunos/", True),
    ("/planos/?pagina=2", True),
    ("//site-malicioso.com", False),
    ("https://site-malicioso.com", False),
    ("/\\site-malicioso.com", False),
    ("javascript:alert(1)", False),
    ("", False),
    (None, False),
])
def test_url_segura(destino, seguro):
    assert url_segura(destino) is seguro


def test_filtros_de_exibicao():
    assert moeda(Decimal("1234.5")) == "R$ 1.234,50"
    assert moeda(None) == "—"
    assert dias_relativos(0) == "hoje"
    assert dias_relativos(1) == "amanhã"
    assert dias_relativos(-3) == "há 3 dias"
    assert data_extenso(date(2026, 9, 14)) == "Segunda-feira, 14 de setembro"


def test_dias_ate_aniversario():
    referencia = date(2026, 9, 14)
    assert dias_ate_aniversario(date(1990, 9, 14), referencia) == 0
    assert dias_ate_aniversario(date(1990, 9, 20), referencia) == 6
    assert dias_ate_aniversario(date(1990, 9, 1), referencia) == 352
    assert dias_ate_aniversario(date(2000, 2, 29), date(2026, 2, 28)) == 1


def test_campo_moeda_aceita_formato_brasileiro(app):
    from app.blueprints.planos.form import PlanoForm

    for bruto, esperado in [("1.234,56", "1234.56"), ("99,9", "99.90"), ("150.00", "150.00")]:
        with app.test_request_context(method="POST", data={"nome": "X", "valor": bruto, "duracao_dias": "30"}):
            form = PlanoForm()
            assert form.validate(), form.errors
            assert form.valor.data == Decimal(esperado)
