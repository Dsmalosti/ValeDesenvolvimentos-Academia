import pytest

from app import create_app
from app.extensions.database import db
from app.extensions.security import bcrypt
from app.models import User

SENHA = "senha-segura-123"


@pytest.fixture
def app():
    app = create_app("testing")
    # não mantemos o app_context aberto durante as requisições:
    # o Flask-Login guarda o usuário em `g` e isso vazaria entre requests
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def criar_instrutor(app):
    def _criar(email="ana@academia.com", nome="Ana", ativo=True):
        with app.app_context():
            instrutor = User(
                nome=nome,
                sobrenome="Teste",
                email=email,
                senha=bcrypt.generate_password_hash(SENHA).decode("utf-8"),
                ativo=ativo,
            )
            db.session.add(instrutor)
            db.session.commit()
            return instrutor.id
    return _criar


@pytest.fixture
def logar(client):
    def _logar(email, senha=SENHA):
        return client.post("/instrutores/login/", data={"email": email, "senha": senha})
    return _logar
