from datetime import datetime

from sqlalchemy import event
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
    # [back-12-config] Configurações da conta (tela /configuracoes). Regras em services/config_service.py.
    # Horário de funcionamento: texto livre, como aparece para o aluno ("06h - 22h", "Fechado"). Vazio = não informado.
    horario_semana = db.Column(db.String(40), nullable=True)
    horario_sabado = db.Column(db.String(40), nullable=True)
    horario_domingo = db.Column(db.String(40), nullable=True)
    # Metas: viram a linha tracejada dos gráficos. Vazio = sem meta (o gráfico mostra a média, ou nada).
    meta_alunos_ativos = db.Column(db.Integer, nullable=True)
    meta_faturamento = db.Column(db.Numeric(10, 2), nullable=True)
    meta_retencao = db.Column(db.Integer, nullable=True)            # % que continua depois de 90 dias
    # "O aluno vira Inativo sozinho depois de X dias sem renovar a matrícula"
    inatividade_ligada = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    inatividade_dias = db.Column(db.Integer, nullable=False, default=60, server_default='60')
    inatividade_conferida_em = db.Column(db.Date, nullable=True)    # último dia em que a regra rodou para esta conta
    lembretes_ligados = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
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
    # [back-10-frequencia] o botão "Bloquear" da recepção: com falso, o check-in recusa a entrada deste aluno.
    # Não mexe em matrícula nem em cobrança. O nome é o que o front usa (aluno.acesso_liberado).
    acesso_liberado = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    # [back-11-relatorios] quando o aluno foi desativado (vazia para quem está ativo). É preenchida e apagada
    # sozinha sempre que `ativo` muda (função _marca_a_inativacao, logo depois da classe). Sem ela não dá
    # para saber quanto tempo um aluno ficou, nem quantos saíram em cada mês.
    data_inativacao = db.Column(db.DateTime, nullable=True)
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


@event.listens_for(Aluno.ativo, 'set', active_history=True)
def _marca_a_inativacao(aluno, novo, antigo, _iniciador):
    """
    [back-11-relatorios] Guarda a data em que o aluno deixou de ser ativo, e apaga quando ele volta.
    Fica aqui, e não em cada rota, porque `ativo` muda em vários lugares (desativar, o botão de
    status da tela antiga, a reativação ao pagar): assim nenhum deles esquece.
    """
    if novo:
        aluno.data_inativacao = None
    elif antigo is True:            # só na passagem de ativo para inativo (aluno criado já inativo não tem data)
        aluno.data_inativacao = datetime.now()


class Convite(db.Model):
    """
    [back-13-equipe] Convite para alguém entrar na equipe de uma conta (recepção ou instrutor).
    Vale 7 dias e só pode ser usado uma vez. O banco guarda o HASH do código do link
    (`token_hash`), nunca o código: se o banco vazar, o link não vaza junto.
    """
    __tablename__ = 'convites'
    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False)                 # o e-mail convidado: será o login da pessoa
    papel = db.Column(db.String(20), nullable=False)                  # recepcao | instrutor (dono não se convida)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    expira_em = db.Column(db.DateTime, nullable=False)
    usado_em = db.Column(db.DateTime, nullable=True)                  # preenchido ao aceitar: é o que garante o uso único

    conta = db.relationship('Conta', lazy=True)

    def __repr__(self):
        return f'<Convite {self.id} {self.papel}>'


class RedefinicaoSenha(db.Model):
    """
    [back-13-equipe] Pedido de troca de senha ("esqueci a senha"). Vale 1 hora, uso único. Como no
    convite, o banco guarda só o hash do código do link.
    """
    __tablename__ = 'redefinicoes_senha'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    expira_em = db.Column(db.DateTime, nullable=False)
    usado_em = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<RedefinicaoSenha usuario={self.usuario_id}>'


class ModeloMensagem(db.Model):
    """
    [back-12-config] O texto de um modelo de mensagem de WhatsApp que a academia ALTEROU (cobrança,
    aniversário, aluno sumido...). Só existe linha para o que foi alterado: quem nunca mexeu usa o
    texto padrão, que fica em services/config_service.py.
    """
    __tablename__ = 'modelos_mensagem'
    __table_args__ = (db.UniqueConstraint('conta_id', 'tipo', name='uq_modelos_mensagem_conta_id_tipo'),)
    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)        # cobranca | aniversario | sumido | boasvindas | avaliacao | sessao
    texto = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<ModeloMensagem {self.tipo}>'


class Custo(db.Model):
    """
    [back-11-relatorios] Custo fixo mensal da academia (aluguel, folha, energia...). A soma dos custos de
    uma conta é o "mínimo" do ponto de equilíbrio do painel administrativo.
    """
    __tablename__ = 'custos'
    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False, index=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)          # por mês

    def __repr__(self):
        return f'<Custo {self.descricao}>'


class Frequencia(db.Model):
    """
    [back-10-frequencia] Uma linha para cada ENTRADA de aluno na academia (check-in).

    Não existe coluna "presente sim/não": faltar é não ter linha. Por isso quem nunca teve entrada
    registrada é "sem dado", e não "0 acessos" (regras em services/frequencia_service.py).
    """
    __tablename__ = 'frequencias'
    __table_args__ = (
        db.Index('ix_frequencias_conta_entrada', 'conta_id', 'data_hora_entrada'),   # a tela do dia e o painel
        db.Index('ix_frequencias_aluno_entrada', 'aluno_id', 'data_hora_entrada'),   # o perfil do aluno
    )
    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False)          # a academia
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    data_hora_entrada = db.Column(db.DateTime, nullable=False)
    origem = db.Column(db.String(20), nullable=False, default='recepcao')                 # recepcao | app
    instrutor_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)  # QUEM registrou

    aluno = db.relationship('Aluno', backref=db.backref('frequencias', lazy=True, passive_deletes='all'), lazy=True)

    def __repr__(self):
        return f'<Frequencia aluno={self.aluno_id} {self.data_hora_entrada}>'


# [back-09-cobranca] valores aceitos nas colunas de texto das duas tabelas abaixo. São conferidos
# pela aplicação (não são db.Enum), para dar para acrescentar um valor sem migration.
COBRANCA_MATRICULA, COBRANCA_RENOVACAO, COBRANCA_DIARIA = 'matricula', 'renovacao', 'diaria'
COBRANCA_PENDENTE, COBRANCA_PAGA, COBRANCA_CANCELADA = 'pendente', 'paga', 'cancelada'
FORMAS_DE_PAGAMENTO = ('pix', 'debito', 'credito', 'dinheiro')
FORMA_NAO_INFORMADA = 'nao_informada'      # só em pagamento anterior à back-09, que não guardava a forma
ORIGEM_MANUAL, ORIGEM_WEBHOOK = 'manual', 'webhook'


class Cobranca(db.Model):
    """
    [back-09-cobranca] Uma cobrança é "o que se deve": nasce na matrícula, na renovação ou na
    diária avulsa e fica `pendente` até ser paga. Antes só existia o que já tinha sido pago.

    A cobrança cobre o período de `data_inicio` a `data_vencimento`. O aluno está em dia até a
    `data_vencimento` da última cobrança PAGA dele (regras em services/situacao_service.py).
    """
    __tablename__ = 'cobrancas'
    __table_args__ = (
        # é a combinação que o painel consulta: as cobranças de uma conta, por status e vencimento
        db.Index('ix_cobrancas_conta_status_vencimento', 'conta_id', 'status', 'data_vencimento'),
    )
    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False)      # a academia dona da cobrança
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=True)       # vazio só na diária avulsa
    plano_id = db.Column(db.Integer, db.ForeignKey('planos.id'), nullable=True)       # o plano DA ÉPOCA; vazio só na diária
    tipo = db.Column(db.String(20), nullable=False)                                   # matricula | renovacao | diaria
    nome_visitante = db.Column(db.String(100), nullable=True)                         # quem pagou a diária, se informado
    valor = db.Column(db.Numeric(10, 2), nullable=False)                              # congelado quando a cobrança nasce
    data_inicio = db.Column(db.Date, nullable=False)                                  # começo do período cobrado
    data_vencimento = db.Column(db.Date, nullable=True)                               # fim do período; vazio na diária
    status = db.Column(db.String(20), nullable=False, default=COBRANCA_PENDENTE)      # pendente | paga | cancelada
    data_geracao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    instrutor_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)   # QUEM criou a cobrança

    # passive_deletes='all': ao apagar um aluno, o SQLAlchemy NÃO zera sozinho o aluno_id das cobranças
    # dele (o padrão seria esse, e a cobrança viraria uma "diária avulsa" sem dono). Quem tem cobrança
    # não pode ser excluído: AlunoService.excluir_aluno confere antes.
    aluno = db.relationship('Aluno', backref=db.backref('cobrancas', lazy=True, passive_deletes='all'), lazy=True)
    plano = db.relationship('Plano', lazy=True)

    def __repr__(self):
        return f'<Cobranca {self.id} {self.tipo} {self.status}>'


class Pagamento(db.Model):
    """
    Um pagamento é "o que entrou no caixa": a confirmação de uma cobrança.

    [back-09-cobranca] antes esta tabela guardava tudo junto (aluno_id, instrutor_id, valor,
    data_vencimento, forma_pagamento). O aluno, o valor devido e o vencimento passaram para a
    Cobranca; aqui ficou o recebimento, com QUEM confirmou e COMO (`origem_confirmacao`).
    """
    __tablename__ = 'pagamentos'
    id = db.Column(db.Integer, primary_key=True)
    # [back-06-contas-e-papeis] a academia dona do pagamento. Repete o da cobrança de propósito:
    # toda consulta do sistema filtra por esta coluna (helpers/conta.py).
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False, index=True)
    cobranca_id = db.Column(db.Integer, db.ForeignKey('cobrancas.id'), nullable=False, index=True)
    forma = db.Column(db.String(20), nullable=False)                    # pix | debito | credito | dinheiro (antes: forma_pagamento)
    valor_pago = db.Column(db.Numeric(10, 2), nullable=False)           # quanto entrou (antes: valor)
    data_pagamento = db.Column(db.DateTime, nullable=False)             # dia e hora (antes: só a data)
    origem_confirmacao = db.Column(db.String(20), nullable=False, default=ORIGEM_MANUAL)   # manual | webhook
    confirmado_por_instrutor_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)   # antes: instrutor_id
    referencia_externa = db.Column(db.String(100), nullable=True)       # código da transação no banco (PIX automático, no futuro)
    observacao = db.Column(db.Text, nullable=True)

    cobranca = db.relationship('Cobranca', backref='pagamentos', lazy=True)
    confirmado_por = db.relationship('User', lazy=True)

    def __repr__(self):
        return f'<Pagamento {self.id} cobranca={self.cobranca_id}>'










    