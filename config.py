import os
from datetime import timedelta

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

    # [back-18-seguranca] Tudo abaixo é novo nesta branch (antes não havia nenhum destes limites).
    # Sessão: quem ficar 12 horas sem usar o sistema precisa entrar de novo (antes: valia até fechar o navegador,
    # e num celular isso é "nunca"). Cada uso renova o prazo.
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    # "Manter conectado": o cookie vale 30 dias (antes: 365, o padrão do Flask-Login).
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    # JavaScript da página não lê os cookies de login; e outro site não consegue usá-los num envio de formulário.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    # Tamanho máximo de um envio (formulário com arquivo): 5 MB. Acima disso o servidor recusa sem ler (erro 413).
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    # Limite de tentativas: onde os contadores ficam (ver app/extensions/protecao.py) e se a regra está ligada.
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI") or "memory://"   # variável vazia no .env também cai na memória
    RATELIMIT_HEADERS_ENABLED = False
    LIMITE_DE_TENTATIVAS_LIGADO = True
    # Em produção: HTTPS obrigatório e cookie só por HTTPS (ver app/extensions/protecao.py).
    EM_PRODUCAO = False


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
    # [back-18-seguranca] nos testes automáticos o limite de tentativas fica desligado (centenas de logins seguidos
    # vêm do mesmo endereço). Os testes do próprio limite ligam de volta (tests/test_seguranca.py).
    LIMITE_DE_TENTATIVAS_LIGADO = False


class ProductionConfig(Config):
    """
    Configuração de produção
    """
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")  # [back-05-repo-e-config] mesmo nome que o create_app() lê
    EM_PRODUCAO = True      # [back-18-seguranca] liga HTTPS obrigatório e HSTS

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
