from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, StringField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from app.services.instrutor_service import TAMANHO_MINIMO_SENHA, InstrutorService


# Formulario de criação de conta (instrutor = academia)
class CadastroForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired('Informe seu nome.'), Length(max=100)])
    sobrenome = StringField('Sobrenome', validators=[Optional(), Length(max=100)])
    email = EmailField('E-mail', validators=[DataRequired('Informe seu e-mail.'), Email('E-mail inválido.'), Length(max=120)])
    senha = PasswordField('Senha', validators=[
        DataRequired('Crie uma senha.'),
        Length(min=TAMANHO_MINIMO_SENHA, message=f'Use pelo menos {TAMANHO_MINIMO_SENHA} caracteres.'),
    ])

    def validate_email(self, field):
        if InstrutorService.email_em_uso(field.data):
            raise ValidationError('Já existe uma conta com este e-mail.')


# Formulario login
class LoginForm(FlaskForm):
    email = EmailField('E-mail', validators=[DataRequired('Informe seu e-mail.'), Email('E-mail inválido.')])
    senha = PasswordField('Senha', validators=[DataRequired('Informe sua senha.')])
    lembrar = BooleanField('Manter conectado', default=True)


# Formulario da própria conta
class ContaForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired('Informe seu nome.'), Length(max=100)])
    sobrenome = StringField('Sobrenome', validators=[Optional(), Length(max=100)])
    email = EmailField('E-mail', validators=[DataRequired('Informe seu e-mail.'), Email('E-mail inválido.'), Length(max=120)])
    senha_atual = PasswordField('Senha atual')
    nova_senha = PasswordField('Nova senha', validators=[
        Optional(),
        Length(min=TAMANHO_MINIMO_SENHA, message=f'Use pelo menos {TAMANHO_MINIMO_SENHA} caracteres.'),
    ])

    def __init__(self, *args, instrutor_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._instrutor_id = instrutor_id

    def validate_email(self, field):
        if InstrutorService.email_em_uso(field.data, ignorar_id=self._instrutor_id):
            raise ValidationError('Já existe uma conta com este e-mail.')

    def validate_senha_atual(self, field):
        if self.nova_senha.data and not field.data:
            raise ValidationError('Informe a senha atual para definir uma nova.')
