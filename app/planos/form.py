from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, DateField, FloatField, BooleanField, DecimalField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, NumberRange

from app import db, bcrypt
from app.models import Plano

class PlanoForm(FlaskForm):
    nome = StringField('Nome do plano', validators=[DataRequired()])
    valor = DecimalField('Valor (R$)', validators=[DataRequired(), NumberRange(min=0)])
    duracao_dias = FloatField('Duração (dias)', validators=[DataRequired(), NumberRange(min=0)])
    descricao  = StringField('Descrição', validators=[DataRequired()])
    ativo = BooleanField('Ativo', default=True)
    btnSubmit = SubmitField('Salvar Plano')