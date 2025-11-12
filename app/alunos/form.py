from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, DateField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

from app import db, bcrypt
from app.models import Aluno, Plano


class AlunoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    telefone = StringField('Numero de Telefone', validators=[DataRequired()])
    data_nascimento = DateField('Data de Nascimento', validators=[DataRequired()], format='%Y-%m-%d')
    cpf = StringField('CPF', validators=[DataRequired()])
    ativo = BooleanField('Ativo', default=True)
    plano_id = SelectField('Plano', coerce=int, validators=[DataRequired()])
    BtnSubmit = SubmitField('Cadastrar')

    def __init__(self, *args, **kwargs):
        super(AlunoForm, self).__init__(*args, **kwargs)
        self.plano_id.choices = [(p.id, p.nome) for p in Plano.query.all()]
