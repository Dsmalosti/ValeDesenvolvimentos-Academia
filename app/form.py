from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

from app import db, bcrypt
from app.models import Aluno, User


class UserForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    sobrenome = StringField('Sobrenome', validators=[DataRequired()])
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    confirmacao_senha = PasswordField('Senha', validators=[DataRequired(), EqualTo('senha')])
    BtnSubmit = SubmitField('Cadastrar')

    def validade_email(self, email):
        if User.query.filter(email=email.data).first():
            return ValidationError('Usuário já cadastrado com esse E-Mail!!!')
        
    def save(self):
        senha = bcrypt.generate_password_hash(self.senha.data.encode('utf-8'))
        user = User(
            nome = self.nome.data,
            sobrenome = self.sobrenome.data,
            email = self.email.data,
            senha=senha
        )

        db.session.add(user)
        db.session.commit()
        return user
    
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

class AlunoForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    telefone = StringField('Numero de Telefone', validators=[DataRequired()])
    data_nascimento = DateField('Data de Nascimento', validators=[DataRequired()], format='%Y-%m-%d')
    cpf = StringField('CPF', validators=[DataRequired()])
    BtnSubmit = SubmitField('Cadastrar')

    def save(self):
        aluno = Aluno(
            nome = self.nome.data,
            email = self.email.data,
            telefone = self.telefone.data,
            data_nascimento = self.data_nascimento.data,
            cpf = self.cpf.data
        )

        db.session.add(aluno)
        db.session.commit()