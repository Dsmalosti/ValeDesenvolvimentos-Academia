from flask_login import LoginManager


login_manager = LoginManager()

def init_app(app):
    login_manager.init_app(app)
    login_manager.login_view = "instrutores.login"
    login_manager.login_message = "Faça login para acessar esta página."
    login_manager.login_message_category = "info"
