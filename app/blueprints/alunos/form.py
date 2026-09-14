from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, EmailField, SelectField, StringField
from wtforms.validators import DataRequired, Email, Length, Optional

from app.helpers.campos import CPF, Telefone
from app.helpers.date_helper import hoje


class AlunoForm(FlaskForm):
    nome = StringField('Nome completo', validators=[DataRequired('Informe o nome.'), Length(max=100)])
    email = EmailField('E-mail', validators=[DataRequired('Informe o e-mail.'), Email('E-mail inválido.'), Length(max=120)])
    telefone = StringField('Telefone / WhatsApp', validators=[Optional(), Telefone()])
    cpf = StringField('CPF', validators=[Optional(), CPF()])
    data_nascimento = DateField('Data de nascimento', validators=[Optional()])
    # choices são preenchidas na rota com os planos da academia logada
    plano_id = SelectField('Plano', coerce=int, validators=[DataRequired('Selecione um plano.')])
    data_inicio_plano = DateField('Início do plano', default=hoje, validators=[DataRequired('Informe o início do plano.')])
    ativo = BooleanField('Aluno ativo', default=True)
