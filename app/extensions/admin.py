from flask_login import LoginManager


login_manager = LoginManager()

def init_app(app):
    login_manager.init_app(app)
    # [back-01-auth-login] antes: "instrutores.login" (tela antiga). Quem não está logado
    # agora cai na tela nova de login.
    login_manager.login_view = "auth.login"

