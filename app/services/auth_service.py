from sqlalchemy import func

from app.models import User
from app.exceptions import BusinessError
from app.extensions.security import bcrypt


class AuthService:

    @staticmethod
    def autenticar_instrutor(email: str, senha: str) -> User:
        email = (email or "").strip().lower()
        instrutor = User.query.filter(func.lower(User.email) == email).first()

        if not instrutor or not AuthService._senha_confere(instrutor, senha):
            # mesma mensagem para e-mail inexistente e senha errada (evita enumeração)
            raise BusinessError("E-mail ou senha inválidos.")

        if not instrutor.ativo:
            raise BusinessError("Esta conta está desativada. Fale com o suporte.")

        return instrutor

    @staticmethod
    def _senha_confere(instrutor, senha):
        if not instrutor.senha:
            return False
        try:
            return bcrypt.check_password_hash(instrutor.senha, senha or "")
        except ValueError:
            # hash legado/corrompido no banco
            return False
