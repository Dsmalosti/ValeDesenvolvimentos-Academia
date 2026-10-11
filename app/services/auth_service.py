from sqlalchemy import func

from app.models import User
from app.exceptions import BusinessError
from app.extensions.security import bcrypt



class AuthService:

    @staticmethod
    def autentificar_instrutor(email: str, senha: str) -> User:
        # [back-01-auth-login] antes: filter_by(email=email), que diferencia maiúscula de
        # minúscula. O teclado do celular escreve "Ana@..." e o login falhava com a senha certa.
        email = (email or '').strip().lower()
        instrutor = User.query.filter(func.lower(User.email) == email).first()

        if not instrutor:
            raise BusinessError("Usuário ou senha inválidos")

        if not instrutor.ativo:
            raise BusinessError("Usuário desativado")

        if not bcrypt.check_password_hash(instrutor.senha, senha):
            raise BusinessError("Usuário ou senha inválidos")

        return instrutor