from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional

from app.models import DIAS_SEMANA


class FichaForm(FlaskForm):
    nome = StringField("Nome da ficha", validators=[DataRequired("Informe o nome da ficha."), Length(max=100)])
    # choices preenchidas na rota com os alunos da academia logada
    aluno_id = SelectField("Aluno", coerce=int, validators=[DataRequired("Selecione um aluno.")])
    observacoes = TextAreaField("Objetivo e observações", validators=[Optional(), Length(max=1000)])
    ativo = BooleanField("Ficha em uso", default=True)


class TreinoForm(FlaskForm):
    dia_semana = SelectField(
        "Dia da semana",
        choices=[("", "Selecione")] + DIAS_SEMANA,
        validators=[DataRequired("Selecione o dia.")]
    )


class TreinoExercicioForm(FlaskForm):
    # choices preenchidas na rota com os exercícios ativos da academia
    exercicio_id = SelectField("Exercício", coerce=int, validators=[DataRequired("Selecione um exercício.")])
    series = IntegerField("Séries", default=3, validators=[
        InputRequired("Informe as séries."),
        NumberRange(min=1, max=20, message="Use entre 1 e 20 séries.")
    ])
    repeticoes = StringField("Repetições", default="12", validators=[
        DataRequired("Informe as repetições."),
        Length(max=50)
    ])
    carga = StringField("Carga", validators=[Optional(), Length(max=50)])
    observacoes = TextAreaField("Observações", validators=[Optional(), Length(max=500)])
