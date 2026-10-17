import hashlib
from datetime import date, datetime

from sqlalchemy import event
from app.extensions.database import db
from app.extensions.admin import login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    """
    Quem é o usuário desta sessão. O que fica guardado no cookie é "id|marca da senha" (ver User.get_id).

    [back-18-seguranca] antes: `User.query.get(user_id)`, com o id puro. Isso tinha dois buracos:
      - trocar a senha não derrubava quem já estava logado em outro aparelho (quem roubou a senha continuava dentro);
      - quem foi removido da equipe (`ativo` falso) continuava usando o sistema até sair por conta própria.
    Agora a sessão só vale se a marca bater com a senha ATUAL e o usuário estiver ativo. Sessão antiga (id puro)
    não tem a marca e deixa de valer: todo mundo entra de novo uma vez, depois que esta branch for ao ar.
    """
    identificador, _, marca = str(user_id).partition('|')
    if not identificador.isdigit():
        return None
    usuario = db.session.get(User, int(identificador))
    if usuario is None or not usuario.ativo or marca != usuario.marca_da_senha():
        return None
    return usuario

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
    # [back-22-ajustes-de-produto] antes: default=True (toda conta nova nascia com a regra ligada). Decisão do Adauto em 14/10/2026:
    # nasce DESLIGADA; o dono liga em Configurações se quiser. Contas que já existem não mudam.
    inatividade_ligada = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    inatividade_dias = db.Column(db.Integer, nullable=False, default=60, server_default='60')
    inatividade_conferida_em = db.Column(db.Date, nullable=True)    # último dia em que a regra rodou para esta conta
    lembretes_ligados = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    # [back-17-personal] Só a conta de personal trainer usa (modelo == 'personal'): o profissional é pessoa física.
    cpf = db.Column(db.String(14), nullable=True)
    cref = db.Column(db.String(20), nullable=True)                  # registro no conselho, ex.: 012345-G/SP
    # Locais de atendimento LIGADOS, separados por vírgula ("estudio,casa"). Vazio = todos ligados.
    locais_ativos = db.Column(db.String(60), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    # [back-24-assinatura] ASSINATURA no Vale Tec (as regras ficam em services/assinatura_service.py). Antes não existia: toda conta
    # usava o sistema para sempre. `teste_ate`: último dia do teste grátis (conta nova: hoje + 2 meses; o admin pode
    # mudar, ex.: o piloto ganha 3 meses). `pago_ate`: último dia do período pago; vazio = nunca pagou.
    teste_ate = db.Column(db.Date, nullable=True, default=lambda: _fim_do_teste_de_uma_conta_nova())
    pago_ate = db.Column(db.Date, nullable=True)
    # [back-25-admin] bloqueio feito à mão por um admin (independe do pagamento): o dia e o motivo, que o cliente vê. Vazio = sem bloqueio.
    bloqueio_manual_em = db.Column(db.Date, nullable=True)
    bloqueio_motivo = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<Conta {self.nome}>'


# [back-24-assinatura] quanto dura o teste grátis de uma conta nova (decisão do Adauto, 14/10/2026)
MESES_DE_TESTE_GRATIS = 2


def _fim_do_teste_de_uma_conta_nova():
    from app.helpers.datas import somar_meses
    return somar_meses(date.today(), MESES_DE_TESTE_GRATIS)


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
    # [back-19-lgpd] Qual versão dos termos de uso e da política de privacidade a pessoa aceitou ao criar a conta, e quando.
    # Vazio para quem entrou antes desta branch e para quem entrou por convite (o contrato é com o dono da conta).
    termos_versao = db.Column(db.String(30), nullable=True)
    termos_aceitos_em = db.Column(db.DateTime, nullable=True)
    # [back-25-admin] ADMINISTRADOR DO VALE TEC (o Adauto e o Diogo): vê todas as contas no /admin. Só se liga pela linha de comando
    # (`flask admin-do-sistema`), nunca por tela: como qualquer um cria conta, ninguém pode virar admin pelo e-mail.
    admin_sistema = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    # quando a pessoa usou o sistema pela última vez (gravado no máximo a cada 10 minutos); o /admin mostra
    ultimo_acesso_em = db.Column(db.DateTime, nullable=True)

    # [back-18-seguranca] ver load_user, lá em cima.
    def marca_da_senha(self):
        """Um pedaço do resumo (sha256) da senha guardada. Muda quando a senha muda; não revela a senha nem o hash dela."""
        return hashlib.sha256((self.senha or '').encode('utf-8')).hexdigest()[:16]

    def get_id(self):
        """O que o Flask-Login guarda na sessão: o id e a marca da senha daquele momento."""
        return f'{self.id}|{self.marca_da_senha()}'

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
    # [back-19-lgpd] O aluno aceita receber avisos pelo WhatsApp? True, False ou vazio (ainda não foi perguntado).
    # Quem RECUSOU não entra na fila de mensagens (services/mensagem_service.py).
    aceita_whatsapp = db.Column(db.Boolean, nullable=True)
    # [back-19-lgpd] Quando os dados pessoais deste aluno foram apagados a pedido (services/lgpd_service.py). Com a data
    # preenchida, o aluno some de todas as telas (helpers/conta.py, da_conta); a linha fica só para os pagamentos apontarem.
    anonimizado_em = db.Column(db.DateTime, nullable=True)
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
    # [back-17-personal] Na conta de personal o "plano" é um PACOTE DE SESSÕES: este é o número que manda (o saldo que
    # o aluno ganha ao comprar). `duracao_dias` continua existindo e vira só a validade do pacote. Na academia fica vazio.
    quantidade_sessoes = db.Column(db.Integer, nullable=True)
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
    equipamento = db.Column(db.String(60), nullable=True)   # [back-14-treinos] barra, halteres, máquina... (campo do formulário do front)
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
    # [back-14-treinos] colunas da tela nova de ficha. A ficha em uso de um aluno é a ATIVA mais recente.
    objetivo = db.Column(db.String(200), nullable=True)
    rascunho = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())   # nasce rascunho ao vir de um modelo; "Salvar ficha" tira
    modelo = db.Column(db.String(40), nullable=True)            # de qual modelo pronto ela nasceu (chave em app/dados_padrao.py)
    valida_ate = db.Column(db.Date, nullable=True)
    atualizada_em = db.Column(db.DateTime, nullable=True)
    atualizada_por_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)   # quem mexeu por último

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
    # [back-14-treinos] a tela nova organiza os treinos por LETRA (A a E) e nome ("Peito e costas"),
    # e não por dia da semana. Treino antigo, sem letra, ganha uma pela ordem de criação.
    letra = db.Column(db.String(1), nullable=True)
    nome = db.Column(db.String(100), nullable=True)

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
    # [back-14-treinos] descanso entre as séries ("60s") e a posição da linha dentro do treino
    descanso = db.Column(db.String(20), nullable=True)
    ordem = db.Column(db.Integer, nullable=False, default=0, server_default='0')

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
    # [back-17-personal] Quantas sessões esta compra dá ao aluno, congelado quando a cobrança nasce (como o valor).
    # Só na conta de personal; na academia fica vazio. O saldo do aluno é a soma disto menos as sessões que abateram.
    quantidade_sessoes = db.Column(db.Integer, nullable=True)

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


# [back-15-avaliacoes] valores aceitos nas colunas de texto das duas tabelas abaixo (conferidos pela
# aplicação, como nas cobranças, para dar para acrescentar um valor sem migration).
AVALIACAO_PRIMEIRA, AVALIACAO_REAVALIACAO = 'primeira', 'reavaliacao'
AGENDA_CONFIRMADA, AGENDA_A_CONFIRMAR, AGENDA_REMARCADA = 'confirmada', 'a_confirmar', 'remarcada'
AGENDA_REALIZADA, AGENDA_CANCELADA = 'realizada', 'cancelada'
AVALIACAO_INCLUSA, AVALIACAO_AVULSA = 'inclusa', 'avulsa'


class AvaliacaoAgendada(db.Model):
    """
    [back-15-avaliacoes] Um horário marcado para avaliar um aluno. É só a AGENDA: as medidas ficam em
    `AvaliacaoFisica`, criada quando a avaliação acontece (e este horário passa a `realizada`).
    Remarcar não apaga: o horário antigo vira `remarcada` e nasce outro.
    """
    __tablename__ = 'avaliacoes_agendadas'
    __table_args__ = (
        db.Index('ix_avaliacoes_agendadas_conta_data', 'conta_id', 'data'),   # a agenda do dia e o painel
    )
    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False)            # a academia
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False, index=True)
    data = db.Column(db.Date, nullable=False)
    hora = db.Column(db.String(5), nullable=False)                                           # "09:00"
    tipo = db.Column(db.String(20), nullable=False, default=AVALIACAO_PRIMEIRA)              # primeira | reavaliacao
    status = db.Column(db.String(20), nullable=False, default=AGENDA_CONFIRMADA)             # confirmada | a_confirmar | remarcada | realizada | cancelada
    avaliador_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)     # quem vai avaliar
    observacao = db.Column(db.String(200), nullable=True)                                    # recado para a recepção
    cobranca = db.Column(db.String(10), nullable=False, default=AVALIACAO_INCLUSA)           # inclusa (no plano) | avulsa (cobrada à parte)
    criado_por_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # passive_deletes='all': apagar o aluno não zera nem apaga a agenda dele em silêncio.
    # Quem tem avaliação não pode ser excluído: AlunoService.excluir_aluno confere antes.
    aluno = db.relationship('Aluno', backref=db.backref('avaliacoes_agendadas', lazy=True, passive_deletes='all'), lazy=True)
    avaliador = db.relationship('User', foreign_keys=[avaliador_id], lazy=True)

    def __repr__(self):
        return f'<AvaliacaoAgendada aluno={self.aluno_id} {self.data} {self.hora}>'


class AvaliacaoFisica(db.Model):
    """
    [back-15-avaliacoes] Uma avaliação física FEITA: anamnese, medidas, dobras e testes. Os nomes das
    colunas são os `name` dos campos do formulário do front.

    É MEDIDA, não diagnóstico: não existe campo de laudo. `imc` e `rcq` nunca vêm do formulário: o
    servidor calcula ao salvar (services/avaliacao_service.py). São dados de saúde (sensíveis pela
    LGPD): só o dono e os instrutores abrem (regra nas rotas).
    """
    __tablename__ = 'avaliacoes_fisicas'
    __table_args__ = (
        db.Index('ix_avaliacoes_fisicas_aluno_data', 'aluno_id', 'data'),    # o histórico do aluno
    )
    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False, index=True)   # a academia
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    avaliador_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)       # quem avaliou
    agendamento_id = db.Column(db.Integer, db.ForeignKey('avaliacoes_agendadas.id'), nullable=True)
    # anamnese
    objetivo = db.Column(db.String(200), nullable=True)
    restricoes = db.Column(db.Text, nullable=True)
    medicamentos = db.Column(db.String(200), nullable=True)
    liberacao_medica = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    # medidas
    peso_kg = db.Column(db.Numeric(5, 2), nullable=False)
    altura_cm = db.Column(db.Numeric(5, 1), nullable=False)
    imc = db.Column(db.Numeric(4, 1), nullable=False)             # calculado: peso / altura²
    cintura_cm = db.Column(db.Numeric(5, 1), nullable=True)
    quadril_cm = db.Column(db.Numeric(5, 1), nullable=True)
    rcq = db.Column(db.Numeric(4, 2), nullable=True)              # calculado: cintura / quadril (vazio se faltar uma das duas)
    braco_d_cm = db.Column(db.Numeric(5, 1), nullable=True)
    coxa_d_cm = db.Column(db.Numeric(5, 1), nullable=True)
    torax_cm = db.Column(db.Numeric(5, 1), nullable=True)
    panturrilha_cm = db.Column(db.Numeric(5, 1), nullable=True)
    # dobras cutâneas, em milímetros
    dobra_triceps = db.Column(db.Numeric(4, 1), nullable=True)
    dobra_subescapular = db.Column(db.Numeric(4, 1), nullable=True)
    dobra_suprailiaca = db.Column(db.Numeric(4, 1), nullable=True)
    dobra_abdominal = db.Column(db.Numeric(4, 1), nullable=True)
    dobra_coxa = db.Column(db.Numeric(4, 1), nullable=True)
    # testes
    teste_flexao = db.Column(db.Integer, nullable=True)           # repetições em 1 minuto
    teste_abdominal = db.Column(db.Integer, nullable=True)        # repetições em 1 minuto
    teste_flexibilidade = db.Column(db.Numeric(4, 1), nullable=True)   # sentar e alcançar, em cm
    anotacao = db.Column(db.Text, nullable=True)                  # do avaliador; medida, nunca laudo
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    aluno = db.relationship('Aluno', backref=db.backref('avaliacoes_fisicas', lazy=True, passive_deletes='all'), lazy=True)
    avaliador = db.relationship('User', lazy=True)

    def __repr__(self):
        return f'<AvaliacaoFisica aluno={self.aluno_id} {self.data}>'


# [back-16-mensagens] tipos de mensagem da fila do dia (os mesmos nomes dos modelos de texto em `modelos_mensagem`)
MENSAGEM_ANIVERSARIO, MENSAGEM_AVALIACAO, MENSAGEM_COBRANCA = 'aniversario', 'avaliacao', 'cobranca'


class MensagemEnviada(db.Model):
    """
    [back-16-mensagens] Registro de que alguém da equipe tocou em "Enviar no WhatsApp" numa linha da
    fila de mensagens. O SISTEMA NÃO ENVIA nada: ele abre o WhatsApp de quem está usando com o texto
    pronto. Esta tabela só guarda o toque, para a linha aparecer como "Enviada hoje" para toda a
    equipe e para a mesma cobrança não ser mandada de novo dia após dia.

    Não guarda o texto nem o telefone: só quem, para quem, de que tipo e quando.
    """
    __tablename__ = 'mensagens_enviadas'
    __table_args__ = (
        # uma linha por mensagem por dia: tocar duas vezes no mesmo dia não duplica
        db.UniqueConstraint('conta_id', 'tipo', 'referencia', 'data', name='uq_mensagens_enviadas_conta_id_tipo_referencia_data'),
        db.Index('ix_mensagens_enviadas_conta_data', 'conta_id', 'data'),
    )
    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False)          # a academia
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False)                                        # aniversario | avaliacao | cobranca
    referencia = db.Column(db.String(40), nullable=False)        # o id do aluno (aniversário, cobrança) ou do horário da avaliação
    data = db.Column(db.Date, nullable=False)                    # o dia do envio (é o que entra na regra de "uma por dia")
    enviada_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    enviada_por_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)   # quem tocou no botão

    # cascade: é só um registro de toque. Se o aluno for excluído (cadastro feito por engano), os registros dele vão junto,
    # em vez de impedirem a exclusão.
    aluno = db.relationship('Aluno', backref=db.backref('mensagens_enviadas', lazy=True, cascade='all, delete-orphan'), lazy=True)

    def __repr__(self):
        return f'<MensagemEnviada {self.tipo} aluno={self.aluno_id} {self.data}>'


# [back-17-personal] valores aceitos nas colunas de texto de `sessoes` (conferidos pela aplicação)
SESSAO_AGENDADA, SESSAO_CONCLUIDA, SESSAO_CANCELADA = 'agendada', 'concluida', 'cancelada'
SESSAO_UNICA, SESSAO_SEMANAL = 'unica', 'semanal'
LOCAIS_DE_ATENDIMENTO = ('estudio', 'casa', 'parque', 'online')
CONTA_PERSONAL = 'personal'


class Sessao(db.Model):
    """
    [back-17-personal] Uma sessão de treino marcada na AGENDA do personal trainer. Na conta de personal ela faz o
    papel que o check-in faz na academia: em vez de entrada na catraca, sessão marcada.

    Regra do saldo: só sessão CONCLUÍDA consome o pacote, e só se o aluno tinha saldo na hora (`abateu`).
    Cancelada não consome. Regras em services/pacote_service.py e services/agenda_service.py.
    """
    __tablename__ = 'sessoes'
    __table_args__ = (
        db.Index('ix_sessoes_conta_data', 'conta_id', 'data'),       # a agenda do dia
        db.Index('ix_sessoes_aluno_status', 'aluno_id', 'status'),   # o saldo do aluno
    )
    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False)             # a conta do personal
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    instrutor_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)     # quem dá a sessão
    data = db.Column(db.Date, nullable=False)
    hora = db.Column(db.String(5), nullable=False)                                           # "07:30"
    duracao = db.Column(db.Integer, nullable=False, default=60)                              # em minutos
    local = db.Column(db.String(20), nullable=False, default='estudio')                      # estudio | casa | parque | online
    repete = db.Column(db.String(10), nullable=False, default=SESSAO_UNICA)                  # unica | semanal
    status = db.Column(db.String(20), nullable=False, default=SESSAO_AGENDADA)               # agendada | concluida | cancelada
    abateu = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())  # consumiu 1 sessão do saldo?
    concluida_em = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Quem tem sessão não pode ser excluído (AlunoService.excluir_aluno confere antes): o saldo depende delas.
    aluno = db.relationship('Aluno', backref=db.backref('sessoes', lazy=True, passive_deletes='all'), lazy=True)

    def __repr__(self):
        return f'<Sessao aluno={self.aluno_id} {self.data} {self.hora} {self.status}>'


class Mensalidade(db.Model):
    """
    [back-24-assinatura] Um pagamento da mensalidade do Vale Tec feito por uma conta (academia ou personal).
    O pagamento é por PIX e a confirmação é feita à mão por um administrador (o sistema não recebe aviso do banco).
    Cada linha estende contas.pago_ate até `periodo_fim`.
    """
    __tablename__ = 'mensalidades'

    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas.id'), nullable=False, index=True)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    meses = db.Column(db.Integer, nullable=False, default=1)
    periodo_inicio = db.Column(db.Date, nullable=False)
    periodo_fim = db.Column(db.Date, nullable=False)
    pago_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    forma = db.Column(db.String(20), nullable=False, default='pix')
    registrado_por_id = db.Column(db.Integer, db.ForeignKey('instrutores.id'), nullable=True)    # quem confirmou (admin); vazio = linha de comando
    observacao = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<Mensalidade conta={self.conta_id} até {self.periodo_fim}>'


class AcaoAdmin(db.Model):
    """
    [back-25-admin] O que um administrador fez numa conta: confirmou pagamento, mudou o teste, bloqueou, entrou como o dono,
    apagou. SEM chave estrangeira de propósito: o registro continua depois de a conta (ou o admin) ser apagada.
    """
    __tablename__ = 'acoes_admin'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, nullable=True)
    admin_email = db.Column(db.String(120), nullable=False, default='')
    conta_id = db.Column(db.Integer, nullable=True, index=True)
    conta_nome = db.Column(db.String(120), nullable=False, default='')
    acao = db.Column(db.String(30), nullable=False)          # pagamento | teste | bloqueio | desbloqueio | entrou | saiu | apagou
    detalhe = db.Column(db.String(300), nullable=True)
    quando = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f'<AcaoAdmin {self.acao} conta={self.conta_id}>'


class RegistroDeAcesso(db.Model):
    """
    [back-26-lgpd-final] Data, hora e IP de cada entrada no sistema (Marco Civil da Internet, art. 15: guardar por 6 meses).
    SEM chave estrangeira de propósito: o registro dura os 6 meses mesmo que a conta seja apagada antes.
    Regras em services/registro_de_acesso_service.py.
    """
    __tablename__ = 'registros_de_acesso'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=True)
    conta_id = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String(120), nullable=False, default='')
    ip = db.Column(db.String(45), nullable=False, default='')           # cabe um endereço IPv6
    evento = db.Column(db.String(20), nullable=False, default='login')  # login | admin_entrou
    quando = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)

    def __repr__(self):
        return f'<RegistroDeAcesso {self.email} {self.quando}>'
