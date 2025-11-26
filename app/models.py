from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

class User(db.Model, UserMixin):
    __tablename__ = 'instrutores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=True)
    sobrenome = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    senha = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<Instrutor {self.nome}>'

class Aluno(db.Model):
    __tablename__ = 'alunos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    telefone = db.Column(db.String(20), nullable=True)
    data_nascimento = db.Column(db.Date, nullable=True)
    cpf = db.Column(db.String(14), unique=True, nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    # chave extrangeira para plano
    plano_id = db.Column(db.Integer, db.ForeignKey('planos.id'), nullable=True)

    # Relacionamento com o plano
    plano = db.relationship('Plano', backref='alunos', lazy=True)

    def __repr__(self):
        return f'<Aluno {self.nome}>'

class Plano(db.Model):
    __tablename__ = 'planos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    duracao_dias = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True)


    def __repr__(self):
        return f'<Plano {self.nome}>'
    
class Exercicio(db.Model):
    __tablename__ = 'exercicio'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    grupo_muscular = db.Column(db.String(50))
    descricao = db.Column(db.Text)
    video_url = db.Column(db.String(200))
    ativo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Exercicio {self.nome}>"

class Ficha(db.Model):
    __tablename__ = 'ficha'

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    observacoes = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)
    treinos = db.relationship('Treino', backref='ficha', lazy=True, cascade="all, delete")

    #relacionamento 
    aluno = db.relationship("Aluno", backref="fichas")


    def __repr__(self):
        return f"<Ficha {self.nome}>"
    
class Treino(db.Model):
    __tablename__ = "treino"

    id = db.Column(db.Integer, primary_key=True)

    ficha_id = db.Column(db.Integer, db.ForeignKey('ficha.id'), nullable=False)
    exercicio_id = db.Column(db.Integer, db.ForeignKey('exercicio.id'), nullable=False)

    series = db.Column(db.Integer, nullable=False)
    repeticoes = db.Column(db.Integer, nullable=False)
    carga = db.Column(db.String(20))
    descanso = db.Column(db.String(20))
    ordem = db.Column(db.Integer, nullable=False)
    observacoes = db.Column(db.Text)

    # relacionamentos
    exercicio = db.relationship("Exercicio", backref="treinos")
    def __repr__(self):
        return f"<Treino {self.id} - Ficha {self.ficha_id}>"










    