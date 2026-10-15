"""
Blueprint `auth` — entrar e sair do sistema (tela nova: templates/auth/login.html).

[back-01-auth-login] Criado nesta branch. Antes o login ficava em `instrutores.login`
(/instrutores/login/) com a tela antiga. As rotas antigas continuam funcionando até a
tela antiga sair; veja docs/mudancas/back-01-auth-login.md.

Os nomes das funções seguem o contrato do front: os templates chamam
url_for('auth.login'), url_for('auth.logout'), url_for('auth.esqueci_senha') e
url_for('auth.criar_conta'). Se algum desses endpoints sumir, a página quebra (BuildError).
"""
from urllib.parse import urlsplit

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, current_user, login_required

from app.services.auth_service import AuthService
from app.services import registro_de_acesso_service  # [back-26-lgpd-final]
from app.exceptions import BusinessError
from app.extensions.protecao import limiter  # [back-18-seguranca] limite de tentativas nas telas públicas
from app.helpers.email import email_configurado  # [back-13-equipe]
from app.services import acesso_service as acesso  # [back-13-equipe]

auth_blueprint = Blueprint('auth', __name__)

# Nome da chave que guarda, na sessão, a página que a pessoa pediu antes de logar.
_CHAVE_PROXIMO = 'login_proximo'


def _destino_seguro(proximo):
    """
    Devolve `proximo` só se for uma página do próprio sistema; senão None.
    """
    if not proximo:
        return None
    # navegadores leem "\" como "/", então "/\site.com" viraria "//site.com"
    if '\\' in proximo or any(ord(c) < 32 for c in proximo):
        return None
    partes = urlsplit(proximo)
    if partes.scheme or partes.netloc or not proximo.startswith('/') or proximo.startswith('//'):
        return None
    return proximo


# [back-18-seguranca] Limites de tentativa das telas públicas (antes não havia nenhum). Só o envio (POST) conta;
# abrir a tela é livre. A chave é o IP de quem chama. Passou do limite: resposta 429 (helpers/erros.py).
LIMITE_DO_LOGIN = '10 per minute; 40 per hour'           # adivinhar senha
LIMITE_POR_CONTA = '10 per 15 minutes'                   # ... e o mesmo e-mail, venha de onde vier
LIMITE_DE_CONTAS_NOVAS = '5 per hour; 20 per day'        # criar contas em série
LIMITE_DE_PEDIDOS_DE_SENHA = '5 per hour'                # pedir troca de senha sem parar
LIMITE_DOS_LINKS = '20 per hour'                         # tentar códigos de convite ou de troca de senha


def _email_da_tentativa():
    """A segunda chave do limite do login: o e-mail digitado (sem ele, o IP)."""
    return 'login:' + ((request.form.get('identificador') or '').strip().lower() or request.remote_addr or '')


@auth_blueprint.route('/login', methods=['GET', 'POST'])
@limiter.limit(LIMITE_DO_LOGIN, methods=['POST'])
@limiter.limit(LIMITE_POR_CONTA, methods=['POST'], key_func=_email_da_tentativa)
def login():
    # Quem já está logado não precisa ver a tela de login.
    if current_user.is_authenticated:
        # [back-04-painel] antes: 'main.homepage' (tela inicial antiga)
        return redirect(url_for('painel.index'))

    if request.method == 'POST':
        # Os nomes dos campos são os `name` do formulário em templates/auth/login.html.
        identificador = request.form.get('identificador', '').strip()
        senha = request.form.get('senha', '')
        # `perfil` vem do popup "Como você vai entrar?". É só dica de tela para teste
        # (o popup sai na versão final). NÃO usar para dar permissão: quem decide o
        # que a pessoa pode ver é o banco (coluna `papel`, tarefa 3.6).
        perfil = request.form.get('perfil') or None
        lembrar = request.form.get('lembrar') == '1'

        def tela_com_erro(mensagem):
            # Volta para a tela com o aviso vermelho, o e-mail preenchido e o perfil
            # escolhido (assim o popup não abre de novo).
            return render_template('auth/login.html', erro=mensagem,
                                   identificador=identificador, perfil=perfil, escolher_perfil=False)

        if not identificador or not senha:
            return tela_com_erro('Preencha o e-mail e a senha.')

        try:
            usuario = AuthService.autentificar_instrutor(email=identificador, senha=senha)
        except BusinessError as e:
            return tela_com_erro(str(e))

        # Lê o `next` ANTES de limpar a sessão. Ele vem da URL ou, no uso normal pelo
        # navegador, da sessão: o form da tela posta em /login sem o ?next= (veja o GET abaixo).
        proximo = _destino_seguro(request.args.get('next') or session.get(_CHAVE_PROXIMO))

        # Sessão nova a cada login: impede "session fixation" (alguém que plantou um
        # cookie de sessão antes do login não herda a sessão logada).
        session.clear()
        session.permanent = True        # [back-18-seguranca] a sessão passa a ter prazo (PERMANENT_SESSION_LIFETIME, 12 horas sem uso)
        login_user(usuario, remember=lembrar)
        registro_de_acesso_service.registrar(usuario)     # [back-26-lgpd-final] data, hora e IP (Marco Civil). Antes: não era guardado
        # [back-04-painel] antes: 'main.homepage' (tela inicial antiga)
        return redirect(proximo or url_for('painel.index'))

    # GET: o Flask-Login manda quem não está logado para /login?next=/pagina-que-pediu, mas o
    # form do template posta em url_for('auth.login'), sem o ?next=. Sem guardar o destino aqui,
    # ele se perderia no envio e a pessoa cairia sempre no painel. Fica na sessão (cookie assinado)
    # só até o login; abrir /login sem ?next= apaga o destino antigo.
    proximo = _destino_seguro(request.args.get('next'))
    if proximo:
        session[_CHAVE_PROXIMO] = proximo
    else:
        session.pop(_CHAVE_PROXIMO, None)
    # [back-18-seguranca] `escolher_perfil=False`: o popup "Como você vai entrar?" sai. O papel vem do banco desde a
    # back-06; o popup era só para o front de exemplo. Antes: o popup abria sempre.
    return render_template('auth/login.html', escolher_perfil=False)


@auth_blueprint.route('/sair', methods=['POST'])
@login_required
def logout():
    """
    Sair só por POST (o form do front manda o csrf_token).

    Por GET, qualquer site poderia deslogar o usuário com uma <img src="/sair">, e o
    "prefetch" de links do front poderia deslogar sozinho ao passar o mouse no botão.
    """
    # A ordem importa: limpar a sessão ANTES do logout_user(). O logout_user() deixa na
    # sessão a marca "apague o cookie lembrar-de-mim"; se limpar depois, a marca some,
    # o cookie fica e a pessoa é logada de volta na próxima página.
    session.clear()
    logout_user()
    return redirect(url_for('auth.login'))


# ---------------------------------------------------------------------------
# [back-13-equipe] Criar conta, aceitar convite e trocar a senha. Regras em services/acesso_service.py.
# Antes: 'auth.esqueci_senha' e 'auth.criar_conta' só respondiam 501 ("em construção"), para os
# links da tela de login não quebrarem; 'auth.convite' e 'auth.nova_senha' não existiam.
# As quatro telas são PÚBLICAS (não pedem login): é por elas que a pessoa ganha o acesso.
# ---------------------------------------------------------------------------
def _entrar(usuario):
    """Sessão nova e login, como na tela de entrar (impede herdar uma sessão plantada antes)."""
    session.clear()
    session.permanent = True            # [back-18-seguranca] sessão com prazo, como no login
    login_user(usuario)


@auth_blueprint.route('/criar-conta', methods=['GET', 'POST'])
@limiter.limit(LIMITE_DE_CONTAS_NOVAS, methods=['POST'])
def criar_conta():
    if current_user.is_authenticated:
        return redirect(url_for('painel.index'))
    if request.method == 'POST':
        valores, erros = acesso.validar_conta_nova(request.form)
        if erros:
            return render_template('auth/criar_conta.html', erros=erros, f=valores), 400
        _entrar(acesso.criar_conta(valores, request.form.get('senha')))
        flash('Conta criada. Bem-vindo ao Vale Tec! Complete os dados da academia em Configurações.', 'success')
        return redirect(url_for('painel.index'))
    return render_template('auth/criar_conta.html', f={}, erros={})


@auth_blueprint.route('/convite/<token>', methods=['GET', 'POST'])
@limiter.limit(LIMITE_DOS_LINKS)
def convite(token):
    convite = acesso.convite_do_link(token)
    if convite is None:
        # não existe, venceu ou já foi usado: a mesma tela e 404 nos três casos
        return render_template('auth/convite.html', convite=None, token=token, erros={}), 404
    contexto = acesso.convite_para_a_tela(convite)
    if request.method == 'POST':
        erros = {}
        if not (request.form.get('nome') or '').strip():
            erros['nome'] = 'Diga seu nome.'
        if acesso.erro_da_senha(request.form.get('senha')):
            erros['senha'] = acesso.erro_da_senha(request.form.get('senha'))
        if not erros:
            try:
                usuario = acesso.aceitar_convite(convite, request.form.get('nome'), request.form.get('senha'))
            except acesso.AcessoInvalido:
                return render_template('auth/convite.html', convite=None, token=token, erros={}), 404
            _entrar(usuario)
            flash('Pronto! Você já faz parte da equipe.', 'success')
            return redirect(url_for('painel.index'))
        return render_template('auth/convite.html', convite=contexto, token=token, erros=erros), 400
    return render_template('auth/convite.html', convite=contexto, token=token, erros={})


@auth_blueprint.route('/esqueci-senha', methods=['GET', 'POST'])
@limiter.limit(LIMITE_DE_PEDIDOS_DE_SENHA, methods=['POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        # Cria o link (se houver conta) e manda por e-mail. A resposta na tela é SEMPRE a mesma,
        # exista a conta ou não: senão a tela serviria para descobrir quem tem cadastro.
        acesso.pedir_troca_de_senha(email)
        return render_template('auth/esqueci_senha.html', enviado=True, email=email, email_configurado=email_configurado())
    return render_template('auth/esqueci_senha.html', email_configurado=email_configurado())


@auth_blueprint.route('/nova-senha/<token>', methods=['GET', 'POST'])
@limiter.limit(LIMITE_DOS_LINKS)
def nova_senha(token):
    pedido = acesso.pedido_de_troca_do_link(token)
    if pedido is None:
        return render_template('auth/nova_senha.html', valido=False, token=token, erro=None), 404
    if request.method == 'POST':
        erro = acesso.erro_da_senha(request.form.get('senha'))
        if erro:
            return render_template('auth/nova_senha.html', valido=True, token=token, erro=erro), 400
        acesso.trocar_senha(pedido, request.form.get('senha'))
        # não entra sozinho: a pessoa faz o login com a senha nova (confirma que ela sabe a senha)
        session.clear()
        logout_user()
        flash('Senha trocada. Entre com a senha nova.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/nova_senha.html', valido=True, token=token, erro=None)
