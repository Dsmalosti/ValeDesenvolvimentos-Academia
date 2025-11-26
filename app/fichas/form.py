from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, HiddenField,FloatField,DateField, BooleanField, IntegerField,SelectField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional, URL, NumberRange


class FichaForm(FlaskForm):
    nome = StringField("Nome da ficha", validators=[DataRequired()])
    observacoes = TextAreaField("Observações")
    aluno_id = SelectField("Aluno", coerce=int, validators=[DataRequired()])
    ativo = BooleanField('Ativo', default=True)
    submit = SubmitField("Salvar")

class TreinoForm(FlaskForm):
    ficha_id = HiddenField("Ficha")
    exercicio_id = SelectField("Exercício", coerce=int, validators=[DataRequired()])
    
    series = IntegerField("Séries", validators=[
        DataRequired(),
        NumberRange(min=1, max=20)
    ])

    repeticoes = IntegerField("Repetições", validators=[
        DataRequired(),
        NumberRange(min=1, max=100)
    ])

    carga = FloatField("Carga (kg)", validators=[Optional()])

    descanso = IntegerField("Descanso (segundos)", validators=[
        Optional(),
        NumberRange(min=0, max=600)
    ])

    observacoes = StringField("Observações", validators=[Optional()])

    submit = SubmitField("Salvar")

