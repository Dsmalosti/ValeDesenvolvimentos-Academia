import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    Configuração base (comum a todos os ambientes)
    """
    # [back-05-repo-e-config] antes: os.getenv("SECRET_KEY", "chave-dev"). Com o valor padrão, se a
    # variável faltasse o app subia com uma chave que está no GitHub, e qualquer pessoa conseguiria
    # forjar uma sessão de login. Agora não há padrão: o create_app() recusa subir sem a chave.
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    """
    Configuração de desenvolvimento
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{os.path.join(BASE_DIR, 'dev.db')}"
    )


class TestingConfig(Config):
    """
    Configuração de testes
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{os.path.join(BASE_DIR, 'test.db')}"
    )


class ProductionConfig(Config):
    """
    Configuração de produção
    """
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")  # [back-05-repo-e-config] mesmo nome que o create_app() lê

    # [back-01-auth-login] Cookies de login protegidos (só valem com HTTPS, que a produção terá).
    # Secure: o navegador só manda o cookie por HTTPS (não vaza em rede aberta).
    # SameSite=Lax: outro site não consegue disparar ações usando o cookie do usuário (CSRF).
    # HttpOnly: JavaScript da página não lê o cookie (já é o padrão do Flask para a sessão).
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"


# Mapeamento dos ambientes
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
