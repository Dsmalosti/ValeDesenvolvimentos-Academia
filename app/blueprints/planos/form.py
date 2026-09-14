from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, StringField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional

from app.helpers.campos import MoedaField


class PlanoForm(FlaskForm):
    nome = StringField('Nome do plano', validators=[DataRequired('Informe o nome do plano.'), Length(max=100)])
    valor = MoedaField('Valor (R$)', places=2, validators=[
        InputRequired('Informe o valor.'),
        NumberRange(min=0, message='O valor não pode ser negativo.'),
    ])
    duracao_dias = IntegerField('Duração (dias)', validators=[
        InputRequired('Informe a duração.'),
        NumberRange(min=1, max=3650, message='Use entre 1 e 3650 dias.'),
    ])
    descricao = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    ativo = BooleanField('Disponível para novas matrículas', default=True)
