from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email


class AlunoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    numeroTelefone = StringField('NumeroTelefone', validators=[DataRequired()])
    dataNascimento = StringField('DataNascimento', validators=[DataRequired()])
    cpf = StringField('CPF', validators=[DataRequired()])
    BtnSubmit = SubmitField('Cadastrar')