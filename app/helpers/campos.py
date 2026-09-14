from wtforms import DecimalField
from wtforms.validators import ValidationError

from app.helpers.validators import cpf_valido, somente_digitos


class MoedaField(DecimalField):
    """Aceita valores no formato brasileiro: 1.234,56 / 1234,56 / 1234.56"""

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            bruto = valuelist[0].replace("R$", "").replace(" ", "").strip()
            if "," in bruto:
                bruto = bruto.replace(".", "").replace(",", ".")
            valuelist = [bruto]
        super().process_formdata(valuelist)

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        if self.data is not None:
            return f"{self.data:.2f}".replace(".", ",")
        return ""


class CPF:
    def __init__(self, message="CPF inválido."):
        self.message = message

    def __call__(self, form, field):
        if field.data and not cpf_valido(field.data):
            raise ValidationError(self.message)


class Telefone:
    def __init__(self, message="Informe DDD + número."):
        self.message = message

    def __call__(self, form, field):
        if field.data and len(somente_digitos(field.data)) not in (10, 11):
            raise ValidationError(self.message)
