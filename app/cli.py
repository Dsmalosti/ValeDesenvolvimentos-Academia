"""
Comandos de terminal do projeto (rodam com `flask <comando>`).

[back-06-contas-e-papeis] Criado nesta branch. O cadastro aberto pela internet
(/instrutores/cadastro/) foi fechado; até a tela nova "Criar conta" existir, é por aqui que
se cria uma academia nova com o seu dono:

    flask criar-conta

O comando pergunta o nome da academia, o nome e o e-mail do dono e a senha (digitada duas
vezes, sem aparecer na tela). A senha nunca vai por parâmetro, para não ficar no histórico
do terminal.
"""
import click

from app.extensions.database import db
from app.extensions.security import bcrypt
from app.models import PAPEL_PROPRIETARIO, Conta, User


def criar_conta_com_dono(nome_academia, nome, sobrenome, email, senha, modelo='academia'):
    """
    Cria a conta (academia) e o usuário dono dela, numa transação só.
    Devolve o usuário criado. Levanta ValueError se o e-mail já estiver em uso.
    """
    email = (email or '').strip().lower()
    if not email or not senha or not nome_academia:
        raise ValueError('Informe o nome da academia, o e-mail e a senha.')
    if User.query.filter(db.func.lower(User.email) == email).first():
        raise ValueError('Já existe um usuário com este e-mail.')

    # [back-10-frequencia] antes: toda conta nascia com o check-in desligado. Academia nasce com ele ligado (a tela de
    # frequência só aparece assim); personal, desligado. Dá para trocar depois em Configurações.
    conta = Conta(nome=nome_academia.strip(), modelo=modelo, checkin_ativo=(modelo == 'academia'))
    db.session.add(conta)
    db.session.flush()   # gera o id da conta sem fechar a transação
    usuario = User(nome=nome, sobrenome=sobrenome, email=email, conta_id=conta.id, papel=PAPEL_PROPRIETARIO,
                   senha=bcrypt.generate_password_hash(senha).decode('utf-8'))
    db.session.add(usuario)
    db.session.commit()
    return usuario


def registrar_comandos(app):
    """Liga os comandos no app. Chamado uma vez, no create_app()."""

    @app.cli.command('criar-conta')
    @click.option('--academia', prompt='Nome da academia', help='Nome da academia (ou do personal).')
    @click.option('--nome', prompt='Nome do dono')
    @click.option('--sobrenome', prompt='Sobrenome do dono', default='')
    @click.option('--email', prompt='E-mail do dono (será o login)')
    @click.option('--modelo', type=click.Choice(['academia', 'personal']), default='academia', show_default=True)
    @click.password_option('--senha', prompt='Senha', confirmation_prompt='Repita a senha',
                           help='Deixe em branco na linha de comando: o comando pergunta sem mostrar na tela.')
    def criar_conta(academia, nome, sobrenome, email, modelo, senha):
        """Cria uma academia nova e o usuário dono dela."""
        try:
            usuario = criar_conta_com_dono(academia, nome, sobrenome, email, senha, modelo)
        except ValueError as erro:
            raise click.ClickException(str(erro))
        click.echo(f'Conta "{academia}" criada. Dono: {usuario.email} (entra pela tela de login).')

    @app.cli.command('semear-catalogo')
    def semear_catalogo():
        """[back-14-treinos] Grava no banco os exercícios do catálogo padrão que estiverem faltando (não duplica)."""
        from app.services.treino_service import semear_catalogo_padrao
        click.echo(f'Catálogo padrão conferido: {semear_catalogo_padrao()} exercício(s) criado(s).')

    @app.cli.command('link-de-senha')
    @click.option('--email', prompt='E-mail de quem esqueceu a senha')
    def link_de_senha(email):
        """
        [back-13-equipe] Gera um link de troca de senha (vale 1 hora, uso único) e mostra na tela, para o
        suporte mandar à pessoa pelo WhatsApp enquanto o envio de e-mail não estiver configurado.
        Precisa de SERVER_NAME (ou rodar com --host certo) para o link sair com o endereço do site.
        """
        from app.services import acesso_service
        with app.test_request_context():
            link = acesso_service.pedir_troca_de_senha(email, enviar=False)
        if link is None:
            raise click.ClickException('Não há conta ativa com este e-mail.')
        click.echo('Link de troca de senha (vale 1 hora):')
        click.echo(link)

    @app.cli.command('banco-novo')
    def banco_novo():
        """
        [back-20-producao] Monta um banco VAZIO (o de produção, na primeira vez): cria todas as tabelas a partir do
        models.py, marca o banco na versão mais nova das migrations e grava o catálogo padrão de exercícios.

        Por que existe: `flask db upgrade` num Postgres vazio para na segunda migration antiga (f456ba924031, que muda o
        tipo de treino.repeticoes de um jeito que o Postgres recusa). Num banco NOVO não há o que migrar: o caminho
        certo é criar tudo de uma vez e dizer ao Alembic que o banco já está em dia. Daí em diante, cada versão nova
        entra com `flask db upgrade`, normalmente.

        O comando se recusa a rodar se o banco já tiver qualquer tabela.
        """
        from flask_migrate import stamp
        from sqlalchemy import inspect

        from app.services.treino_service import semear_catalogo_padrao

        existentes = inspect(db.engine).get_table_names()
        if existentes:
            raise click.ClickException(f'Este banco já tem {len(existentes)} tabela(s). O comando só vale para banco vazio. '
                                       'Para atualizar um banco que já existe, use: flask db upgrade')
        db.create_all()
        stamp(revision='head')
        exercicios = semear_catalogo_padrao()
        click.echo(f'Banco criado: {len(inspect(db.engine).get_table_names())} tabelas, {exercicios} exercícios no catálogo padrão.')
        click.echo('Próximo passo: crie a primeira conta pela tela /criar-conta (ou com: flask criar-conta).')
