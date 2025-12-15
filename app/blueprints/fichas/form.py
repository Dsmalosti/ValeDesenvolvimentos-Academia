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
    id = HiddenField()
    ficha_id = HiddenField("Ficha")

    dia_semana = SelectField(
        "Dia da Semana",
        choices=[
            ("segunda", "Segunda-feira"),
            ("terca", "Terça-feira"),
            ("quarta", "Quarta-feira"),
            ("quinta", "Quinta-feira"),
            ("sexta", "Sexta-feira"),
            ("sabado", "Sábado"),
            ("domingo", "Domingo")
        ],
        validators=[DataRequired()]
    )

    submit = SubmitField("Salvar")


class TreinoExercicioForm(FlaskForm):
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

    observacoes = TextAreaField("Observações", validators=[Optional()])

    submit = SubmitField("Salvar")

