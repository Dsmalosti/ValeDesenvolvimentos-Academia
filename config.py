import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    Configuração base (comum a todos os ambientes)
    """
    SECRET_KEY = os.getenv("SECRET_KEY", "chave-dev")
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
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


# Mapeamento dos ambientes
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
