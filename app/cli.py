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
    # [back-28-precos-e-promocao] conta criada por aqui também entra na promoção de lançamento, se houver vaga
    from app.services import assinatura_service
    assinatura_service.entrar_na_promocao(conta)
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

    # [back-24-assinatura] assinatura do Vale Tec pela linha de comando (o painel de administração faz o mesmo pela tela)
    @app.cli.command('assinaturas')
    def assinaturas():
        """Lista as contas com a situação da assinatura (teste, em dia, vencida, bloqueada) e o vencimento."""
        from app.services import assinatura_service
        for conta in Conta.query.order_by(Conta.id).all():
            s = assinatura_service.situacao(conta)
            click.echo(f"{conta.id:>4}  {conta.nome[:34]:<34}  {s['rotulo']:<13}  vence {s['vence'].strftime('%d/%m/%Y')}")

    @app.cli.command('assinatura-paga')
    @click.option('--conta', 'conta_id', type=int, required=True, help='Número (id) da conta.')
    @click.option('--meses', type=int, default=1, show_default=True)
    @click.option('--valor', default=None, help='Valor recebido. Sem ele, o preço da conta vezes os meses.')
    def assinatura_paga(conta_id, meses, valor):
        """Confirma o pagamento da mensalidade de uma conta (depois de conferir no banco)."""
        from app.services import assinatura_service
        conta = db.session.get(Conta, conta_id)
        if conta is None:
            raise click.ClickException(f'Não existe conta com o número {conta_id}.')
        try:
            registro = assinatura_service.registrar_pagamento(conta, meses=meses, valor=valor, observacao='linha de comando')
        except ValueError as erro:
            raise click.ClickException(str(erro))
        click.echo(f'Pagamento registrado: {conta.nome}, paga até {registro.periodo_fim.strftime("%d/%m/%Y")}.')

    @app.cli.command('assinatura-teste')
    @click.option('--conta', 'conta_id', type=int, required=True, help='Número (id) da conta.')
    @click.option('--ate', required=True, help='Último dia do teste grátis, no formato AAAA-MM-DD.')
    def assinatura_teste(conta_id, ate):
        """Muda o fim do teste grátis de uma conta (ex.: o cliente piloto ganha 3 meses no total)."""
        from datetime import date as _date
        from app.services import assinatura_service
        conta = db.session.get(Conta, conta_id)
        if conta is None:
            raise click.ClickException(f'Não existe conta com o número {conta_id}.')
        try:
            assinatura_service.mudar_fim_do_teste(conta, _date.fromisoformat(ate))
        except ValueError as erro:
            raise click.ClickException(str(erro))
        click.echo(f'Teste grátis de {conta.nome} vai até {conta.teste_ate.strftime("%d/%m/%Y")}.')

    # [back-25-admin] quem é administrador do Vale Tec (só por aqui: não existe tela que torne alguém admin)
    @app.cli.command('admin-do-sistema')
    @click.option('--email', required=True, help='E-mail de login da pessoa (ela já precisa ter conta no sistema).')
    @click.option('--remover', is_flag=True, help='Tira o acesso de administrador.')
    def admin_do_sistema(email, remover):
        """Liga (ou desliga, com --remover) o acesso ao painel de administração /admin para um usuário."""
        usuario = User.query.filter(db.func.lower(User.email) == email.strip().lower()).first()
        if usuario is None:
            raise click.ClickException(f'Não existe usuário com o e-mail {email}. Crie a conta primeiro (tela /criar-conta).')
        usuario.admin_sistema = not remover
        if not remover and usuario.conta and usuario.conta.desconto_promocional:
            # [back-28-precos-e-promocao] a conta de um admin não paga: devolve a vaga da promoção para um cliente de verdade
            usuario.conta.desconto_promocional = 0
            click.echo('A conta dele estava na promoção de lançamento; a vaga foi liberada para outro cliente.')
        db.session.commit()
        click.echo(f"{usuario.email} {'não é mais' if remover else 'agora é'} administrador do Vale Tec (painel em /admin).")
