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

from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_login import login_user, logout_user, current_user, login_required

from app.services.auth_service import AuthService
from app.exceptions import BusinessError

auth_blueprint = Blueprint('auth', __name__)

# Nome da chave que guarda, na sessão, a página que a pessoa pediu antes de logar.
_CHAVE_PROXIMO = 'login_proximo'


def _destino_seguro(proximo):
    """
    Devolve `proximo` só se for uma página do próprio sistema; senão None.

    O Flask-Login manda quem não está logado para /login?next=/pagina-que-pediu.
    Sem essa checagem, um link /login?next=https://site-falso.com mandaria a pessoa,
    já logada, para um site de golpe (open redirect).
    """
    if not proximo:
        return None
    partes = urlsplit(proximo)
    # precisa ser caminho relativo: começa com "/", não "//" (que o navegador lê como outro site)
    if partes.scheme or partes.netloc or not proximo.startswith('/') or proximo.startswith('//'):
        return None
    return proximo


@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    # Quem já está logado não precisa ver a tela de login.
    if current_user.is_authenticated:
        return redirect(url_for('main.homepage'))

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
                                   identificador=identificador, perfil=perfil)

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
        login_user(usuario, remember=lembrar)
        return redirect(proximo or url_for('main.homepage'))

    # GET: o Flask-Login manda quem não está logado para /login?next=/pagina-que-pediu, mas o
    # form do template posta em url_for('auth.login'), sem o ?next=. Sem guardar o destino aqui,
    # ele se perderia no envio e a pessoa cairia sempre no painel. Fica na sessão (cookie assinado)
    # só até o login; abrir /login sem ?next= apaga o destino antigo.
    proximo = _destino_seguro(request.args.get('next'))
    if proximo:
        session[_CHAVE_PROXIMO] = proximo
    else:
        session.pop(_CHAVE_PROXIMO, None)
    return render_template('auth/login.html')


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
# Os dois links da tela de login ("Esqueci a senha" e "Criar conta") precisam que
# estes endpoints EXISTAM, senão o url_for quebra a página inteira.
# As telas de verdade entram nas próximas branches (tarefa 5.10). Por enquanto
# respondem 501 (= "ainda não implementado").
# ---------------------------------------------------------------------------
@auth_blueprint.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    return 'Recuperar senha: em construção.', 501


@auth_blueprint.route('/criar-conta', methods=['GET', 'POST'])
def criar_conta():
    return 'Criar conta: em construção.', 501
