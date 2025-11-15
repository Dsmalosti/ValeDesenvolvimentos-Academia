from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional

from app import db, bcrypt
from app.models import User


# Formulario Instrutor
class UserForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    sobrenome = StringField('Sobrenome', validators=[DataRequired()])
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha')
    confirmacao_senha = PasswordField('Senha', validators=[EqualTo('senha')])
    BtnSubmit = SubmitField('Cadastrar')

    def validade_email(self, email):
        if User.query.filter(email=email.data).first():
            return ValidationError('Usuário já cadastrado com esse E-Mail!!!')
        
    def save(self):
        senha = bcrypt.generate_password_hash(self.senha.data).decode('utf-8')
        user = User(
            nome = self.nome.data,
            sobrenome = self.sobrenome.data,
            email = self.email.data,
            senha=senha
        )

        db.session.add(user)
        db.session.commit()
        return user
    
# Formulario login
class LoginForm(FlaskForm):
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    btnSubmit = SubmitField('Login')

    def login(self):
        # Recuperar o usuario do e-mail
        user = User.query.filter_by(email=self.email.data).first()

        #verifica se a senha é valida
        if user:
            if bcrypt.check_password_hash(user.senha, self.senha.data.encode('utf-8')):
                #Retorna usuario
                return user
            raise Exception('Senha incorreta!!!')
        else:
            raise Exception('Usuário não encontrado!!!')
            

        return user