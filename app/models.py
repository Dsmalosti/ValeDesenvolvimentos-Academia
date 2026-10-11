from datetime import datetime
from app.extensions.database import db
from app.extensions.admin import login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# [back-06-contas-e-papeis] Papéis de quem usa o sistema dentro de uma conta (academia).
PAPEL_PROPRIETARIO, PAPEL_RECEPCAO, PAPEL_INSTRUTOR = 'proprietario', 'recepcao', 'instrutor'
PAPEIS = (PAPEL_PROPRIETARIO, PAPEL_RECEPCAO, PAPEL_INSTRUTOR)


class Conta(db.Model):
    """
    [back-06-contas-e-papeis] A conta é a academia (ou o personal trainer) que usa o sistema.

    Antes cada linha de `instrutores` ERA uma academia: o dono via os próprios alunos e mais
    ninguém. Com a conta separada, o dono, a recepção e os instrutores são usuários diferentes
    da MESMA conta e enxergam os mesmos alunos. É a `conta_id` que isola uma academia da outra.
    """
    __tablename__ = 'contas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    razao = db.Column(db.String(160), nullable=True)
    cnpj = db.Column(db.String(18), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    cidade = db.Column(db.String(80), nullable=True)
    endereco = db.Column(db.String(200), nullable=True)
    # 'academia' ou 'personal': muda o menu e o painel no front
    modelo = db.Column(db.String(20), nullable=False, default='academia', server_default='academia')
    # funcionalidades ligadas na conta (no front: academia.checkin_ativo e academia.pix_ligado)
    checkin_ativo = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    pix_ligado = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Conta {self.nome}>'


class User(db.Model, UserMixin):
    __tablename__ = 'instrutores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=True)
    sobrenome = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    senha = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False, server_default='true')
    # [back-06-contas-e-papeis] a academia a que o usuário pertence, e o que ele pode fazer nela
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False)
    papel = db.Column(db.String(20), nullable=False, default=PAPEL_PROPRIETARIO, server_default=PAPEL_PROPRIETARIO)

    conta = db.relationship('Conta', backref='usuarios', lazy=True)

    def __repr__(self):
        return f'<Instrutor {self.nome}>'

class Aluno(db.Model):
    __tablename__ = 'alunos'
    # [back-06-contas-e-papeis] antes: e-mail e CPF eram únicos no banco INTEIRO (unique=True em cada
    # coluna). Um aluno que treina em duas academias travava o cadastro, e a mensagem de erro
    # revelava para a segunda que ele existia na primeira. Agora são únicos dentro de cada conta.
    __table_args__ = (
        db.UniqueConstraint('conta_id', 'email', name='uq_alunos_conta_id_email'),
        db.UniqueConstraint('conta_id', 'cpf', name='uq_alunos_conta_id_cpf'),
    )
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    telefone = db.Column(db.String(20), nullable=True)
    data_nascimento = db.Column(db.Date, nullable=True)
    cpf = db.Column(db.String(14), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    # [back-07-alunos] colunas que o formulário do front novo envia e o banco não tinha onde guardar.
    # O nome de cada uma é igual ao `name` do campo no formulário (regra do contrato front <-> back).
    data_inicio = db.Column(db.Date, nullable=True)              # quando o aluno começa (pode ser futuro)
    dia_vencimento = db.Column(db.Integer, nullable=True)        # dia do mês em que a mensalidade vence, de 1 a 28
    forma_pagamento = db.Column(db.String(20), nullable=True)    # pix | debito | credito | dinheiro (a preferida do aluno)
    observacoes = db.Column(db.Text, nullable=True)              # restrição médica, objetivo, indicação...
    # chave extrangeira para plano
    plano_id = db.Column(db.Integer, db.ForeignKey('planos.id'), nullable=True)
    # chave estrangeira para o instrutor (academia) dono deste aluno
    # OBS: nullable=True por enquanto, só até preenchermos os registros
    # antigos. Depois trocamos para nullable=False (passo 4 do plano).
    instrutor_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)
    # [back-06-contas-e-papeis] a academia dona do aluno. É por esta coluna que o sistema isola as
    # contas. `instrutor_id` (acima) deixou de ser "o dono" e passou a ser só "quem cadastrou".
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False, index=True)

    # Relacionamento com o plano
    plano = db.relationship('Plano', backref='alunos', lazy=True)
    instrutor = db.relationship('User', backref='alunos', lazy=True)

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
    # [back-08-planos] quantas avaliações físicas o plano inclui: 0 (cobrada à parte), 1, 2 ou 4.
    # É o campo "Avaliação física inclusa" do formulário do front. Por enquanto só é guardado;
    # quem vai usar é o módulo de avaliações.
    avaliacoes_incluidas = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    # chave estrangeira para o instrutor (academia) dono deste plano
    # OBS: nullable=True por enquanto, só até preenchermos os registros
    # antigos. Depois trocamos para nullable=False (passo 4 do plano).
    instrutor_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)
    # [back-06-contas-e-papeis] a academia dona do plano (veja o comentário em Aluno.conta_id)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False, index=True)

    instrutor = db.relationship('User', backref='planos', lazy=True)

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
    # [back-06-contas-e-papeis] antes o exercício não tinha dono: era um catálogo único que qualquer
    # academia logada via, editava e apagava. Agora: conta_id vazio = catálogo padrão do sistema
    # (todo mundo vê, ninguém edita); conta_id preenchido = exercício criado por aquela academia.
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=True, index=True)

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


class Pagamento(db.Model):
    __tablename__ = 'pagamentos'
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    instrutor_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=False)
    # [back-06-contas-e-papeis] a academia dona do pagamento; `instrutor_id` é quem registrou
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False, index=True)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_pagamento = db.Column(db.Date, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    forma_pagamento = db.Column(db.String(20), nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    aluno = db.relationship('Aluno', backref='pagamentos', lazy=True)
    instrutor = db.relationship('User', backref='pagamentos', lazy=True)

    def __repr__(self):
        return f'<Pagamento {self.aluno_id} - {self.data_pagamento}>'










    