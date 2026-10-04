from flask_wtf import FlaskForm
from wtforms import DecimalField, DateField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class PagamentoForm(FlaskForm):
    valor = DecimalField('Valor', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    data_pagamento = DateField('Data do Pagamento', validators=[DataRequired()], format='%Y-%m-%d')
    forma_pagamento = SelectField('Forma de Pagamento', choices=[
        ('dinheiro', 'Dinheiro'),
        ('pix', 'Pix'),
        ('cartao', 'Cartão'),
        ('outro', 'Outro'),
    ], validators=[DataRequired()])
    observacao = TextAreaField('Observação')
    BtnSubmit = SubmitField('Registrar Pagamento')