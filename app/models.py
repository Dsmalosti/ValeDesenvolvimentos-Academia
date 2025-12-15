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

    # relacionamento com aluno
    aluno = db.relationship("Aluno", backref="fichas")

    # cada ficha tem vários treinos
    treinos = db.relationship("Treino", backref="ficha", lazy=True, cascade="all, delete")

    def __repr__(self):
        return f"<Ficha {self.nome}>"


class Treino(db.Model):
    __tablename__ = 'treino'

    id = db.Column(db.Integer, primary_key=True)
    ficha_id = db.Column(db.Integer, db.ForeignKey('ficha.id'), nullable=False)

    dia_semana = db.Column(db.String(20), nullable=True)

    # cada treino tem vários exercícios
    exercicios = db.relationship(
        "TreinoExercicio",
        backref="treino",
        lazy=True,
        cascade="all, delete"
    )

    def __repr__(self):
        return f"<Treino {self.id} - Ficha {self.ficha_id}>"


class TreinoExercicio(db.Model):
    __tablename__ = 'treino_exercicio'

    id = db.Column(db.Integer, primary_key=True)

    treino_id = db.Column(db.Integer, db.ForeignKey('treino.id'), nullable=False)
    exercicio_id = db.Column(db.Integer, db.ForeignKey('exercicio.id'), nullable=False)

    # acesso ao exercício
    exercicio = db.relationship("Exercicio")

    series = db.Column(db.Integer, nullable=False)
    repeticoes = db.Column(db.String(50), nullable=False)
    carga = db.Column(db.String(50))
    observacoes = db.Column(db.Text)

    def __repr__(self):
        return f"<TreinoExercicio {self.exercicio.nome}>"










    