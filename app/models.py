from datetime import timedelta
from decimal import Decimal

from flask_login import UserMixin

from app.extensions.admin import login_manager
from app.extensions.database import db
from app.helpers.date_helper import agora_utc, hoje


DIAS_SEMANA = [
    ("segunda", "Segunda-feira"),
    ("terca", "Terça-feira"),
    ("quarta", "Quarta-feira"),
    ("quinta", "Quinta-feira"),
    ("sexta", "Sexta-feira"),
    ("sabado", "Sábado"),
    ("domingo", "Domingo"),
]

GRUPOS_MUSCULARES = [
    ("peito", "Peito"),
    ("costas", "Costas"),
    ("ombro", "Ombros"),
    ("biceps", "Bíceps"),
    ("triceps", "Tríceps"),
    ("pernas", "Pernas"),
    ("gluteo", "Glúteo"),
    ("abdomen", "Abdômen"),
    ("outro", "Outro"),
]

# A partir de quantos dias antes do vencimento o aluno aparece como "a vencer"
DIAS_ALERTA_VENCIMENTO = 7


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


class User(db.Model, UserMixin):
    """Instrutor dono da conta. Cada instrutor é uma academia (tenant)."""
    __tablename__ = 'instrutores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=True)
    sobrenome = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    senha = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, server_default='true')

    @property
    def is_active(self):
        # Flask-Login recusa login_user() de contas desativadas
        return bool(self.ativo)

    @property
    def nome_completo(self):
        return " ".join(parte for parte in (self.nome, self.sobrenome) if parte)

    def __repr__(self):
        return f'<Instrutor {self.nome}>'


class Plano(db.Model):
    __tablename__ = 'planos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    duracao_dias = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    instrutor_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True, index=True)

    instrutor = db.relationship('User', backref='planos', lazy=True)

    @property
    def valor_mensal(self):
        """Valor equivalente a 30 dias, para comparar planos de durações diferentes."""
        if not self.duracao_dias:
            return Decimal("0")
        return (Decimal(self.valor) / Decimal(self.duracao_dias) * 30).quantize(Decimal("0.01"))

    def __repr__(self):
        return f'<Plano {self.nome}>'


class Aluno(db.Model):
    __tablename__ = 'alunos'
    # e-mail e CPF são únicos por academia, não no sistema inteiro
    __table_args__ = (
        db.UniqueConstraint('instrutor_id', 'email', name='uq_alunos_instrutor_id_email'),
        db.UniqueConstraint('instrutor_id', 'cpf', name='uq_alunos_instrutor_id_cpf'),
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    data_cadastro = db.Column(db.DateTime, default=agora_utc)
    telefone = db.Column(db.String(20), nullable=True)
    data_nascimento = db.Column(db.Date, nullable=True)
    cpf = db.Column(db.String(14), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    plano_id = db.Column(db.Integer, db.ForeignKey('planos.id'), nullable=True)
    # data em que o ciclo atual do plano começou (renovação move essa data)
    data_inicio_plano = db.Column(db.Date, nullable=True)
    instrutor_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True, index=True)

    plano = db.relationship('Plano', backref='alunos', lazy=True)
    instrutor = db.relationship('User', backref='alunos', lazy=True)
    fichas = db.relationship('Ficha', back_populates='aluno', cascade='all, delete-orphan')

    @property
    def data_vencimento(self):
        if not (self.plano and self.data_inicio_plano):
            return None
        return self.data_inicio_plano + timedelta(days=self.plano.duracao_dias)

    @property
    def dias_para_vencer(self):
        vencimento = self.data_vencimento
        return (vencimento - hoje()).days if vencimento else None

    @property
    def situacao(self):
        if not self.ativo:
            return "inativo"
        dias = self.dias_para_vencer
        if dias is None:
            return "sem_plano"
        if dias < 0:
            return "vencido"
        if dias <= DIAS_ALERTA_VENCIMENTO:
            return "a_vencer"
        return "em_dia"

    def __repr__(self):
        return f'<Aluno {self.nome}>'


class Exercicio(db.Model):
    __tablename__ = 'exercicio'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    grupo_muscular = db.Column(db.String(50))
    descricao = db.Column(db.Text)
    video_url = db.Column(db.String(200))
    ativo = db.Column(db.Boolean, default=True)
    instrutor_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True, index=True)

    @property
    def grupo_label(self):
        return dict(GRUPOS_MUSCULARES).get(self.grupo_muscular, "Outro")

    def __repr__(self):
        return f"<Exercicio {self.nome}>"


class Ficha(db.Model):
    __tablename__ = 'ficha'

    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    observacoes = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=agora_utc)
    ativo = db.Column(db.Boolean, default=True)
    instrutor_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True, index=True)

    aluno = db.relationship("Aluno", back_populates="fichas")
    treinos = db.relationship("Treino", backref="ficha", lazy=True, cascade="all, delete-orphan")

    @property
    def treinos_ordenados(self):
        ordem = {chave: i for i, (chave, _) in enumerate(DIAS_SEMANA)}
        return sorted(self.treinos, key=lambda t: ordem.get(t.dia_semana, len(ordem)))

    @property
    def total_exercicios(self):
        return sum(len(treino.exercicios) for treino in self.treinos)

    def __repr__(self):
        return f"<Ficha {self.nome}>"


class Treino(db.Model):
    __tablename__ = 'treino'

    id = db.Column(db.Integer, primary_key=True)
    ficha_id = db.Column(db.Integer, db.ForeignKey('ficha.id'), nullable=False)
    dia_semana = db.Column(db.String(20), nullable=True)

    exercicios = db.relationship(
        "TreinoExercicio",
        backref="treino",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="TreinoExercicio.id",
    )

    @property
    def dia_label(self):
        return dict(DIAS_SEMANA).get(self.dia_semana, "Sem dia")

    def __repr__(self):
        return f"<Treino {self.id} - Ficha {self.ficha_id}>"


class TreinoExercicio(db.Model):
    __tablename__ = 'treino_exercicio'

    id = db.Column(db.Integer, primary_key=True)
    treino_id = db.Column(db.Integer, db.ForeignKey('treino.id'), nullable=False)
    exercicio_id = db.Column(db.Integer, db.ForeignKey('exercicio.id'), nullable=False)
    series = db.Column(db.Integer, nullable=False)
    repeticoes = db.Column(db.String(50), nullable=False)
    carga = db.Column(db.String(50))
    observacoes = db.Column(db.Text)

    exercicio = db.relationship("Exercicio")

    def __repr__(self):
        return f"<TreinoExercicio {self.exercicio_id}>"
