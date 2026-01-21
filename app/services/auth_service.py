from models import User
from app.exceptions import BusinessError
from app.extensions.security import bcrypt



class AuthService:

    @staticmethod
    def autentificar_instrutor(email: str, senha: str) -> User:
        instrutor = User.query.filter_by(email=email).first()

        if not instrutor:
            raise BusinessError("Usuário ou senha inválidos")

        if not instrutor.ativo:
            raise BusinessError("Usuário desativado")

        if not bcrypt.check_password_hash(instrutor.senha, senha):
            raise BusinessError("Usuário ou senha inválidos")

        return instrutor