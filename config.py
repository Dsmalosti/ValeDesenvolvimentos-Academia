import os
from datetime import timedelta

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Carrega o .env antes de montar as classes de configuração
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _database_uri():
    uri = os.getenv("DATABASE_URI") or os.getenv("DATABASE_URL")
    # Render/Heroku entregam "postgres://", que o SQLAlchemy 2 não aceita
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    return uri


class Config:
    """
    Configuração base (comum a todos os ambientes)
    """
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    WTF_CSRF_TIME_LIMIT = None
    MAX_CONTENT_LENGTH = 1024 * 1024

    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")
    ITENS_POR_PAGINA = 20


class DevelopmentConfig(Config):
    """
    Configuração de desenvolvimento
    """
    DEBUG = True


class TestingConfig(Config):
    """
    Configuração de testes (SQLite em memória, sem CSRF)
    """
    TESTING = True
    SECRET_KEY = "chave-de-teste"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    BCRYPT_LOG_ROUNDS = 4


class ProductionConfig(Config):
    """
    Configuração de produção
    """
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


# Mapeamento dos ambientes
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
