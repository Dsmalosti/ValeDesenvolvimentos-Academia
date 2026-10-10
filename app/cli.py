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

    conta = Conta(nome=nome_academia.strip(), modelo=modelo)
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
