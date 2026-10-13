from sqlalchemy import func

from app.models import User
from app.exceptions import BusinessError
from app.extensions.security import bcrypt



# [back-18-seguranca] hash de uma senha que ninguém tem: é contra ele que a senha digitada é conferida quando o
# e-mail não existe, só para a resposta levar o mesmo tempo de um e-mail que existe. Gerado uma vez, no primeiro uso.
_guardado = {}


def _senha_de_ninguem():
    if 'hash' not in _guardado:
        _guardado['hash'] = bcrypt.generate_password_hash('uma-senha-que-ninguem-tem').decode('utf-8')
    return _guardado['hash']


class AuthService:

    @staticmethod
    def autentificar_instrutor(email: str, senha: str) -> User:
        # [back-01-auth-login] antes: filter_by(email=email), que diferencia maiúscula de
        # minúscula. O teclado do celular escreve "Ana@..." e o login falhava com a senha certa.
        email = (email or '').strip().lower()
        instrutor = User.query.filter(func.lower(User.email) == email).first()

        # [back-18-seguranca] antes: respondia "Usuário desativado" ANTES de conferir a senha, o que contava a qualquer
        # pessoa que aquele e-mail tem conta; e, quando o e-mail não existia, respondia na hora, sem conferir senha
        # nenhuma (dava para descobrir quem tem cadastro medindo o tempo da resposta). Agora os três casos (e-mail
        # que não existe, senha errada e conta desativada) dão a MESMA mensagem, depois do mesmo trabalho.
        guardada = instrutor.senha if (instrutor and instrutor.senha) else _senha_de_ninguem()
        try:
            confere = bcrypt.check_password_hash(guardada, senha)
        except ValueError:          # senha guardada num formato que o bcrypt não lê (dado antigo)
            confere = False
        if not instrutor or not confere or not instrutor.ativo:
            raise BusinessError("Usuário ou senha inválidos")

        return instrutor