from sqlalchemy import func

from app.models import User
from app.services.base_service import BaseService
from app.exceptions import BusinessError
from app.extensions.database import db
from app.extensions.security import bcrypt
from app.helpers.validators import normalizar_email, texto_ou_none

TAMANHO_MINIMO_SENHA = 8


class InstrutorService:

    @staticmethod
    def email_em_uso(email, ignorar_id=None):
        query = User.query.filter(func.lower(User.email) == (email or "").strip().lower())
        if ignorar_id:
            query = query.filter(User.id != ignorar_id)
        return db.session.query(query.exists()).scalar()

    @staticmethod
    def criar_instrutor(dados):
        """
        Cria a conta do instrutor (a academia) com senha criptografada
        """
        email = normalizar_email(dados.get("email"))
        if InstrutorService.email_em_uso(email):
            raise BusinessError("Já existe uma conta com este e-mail.")

        nome = (dados.get("nome") or "").strip()
        if not nome:
            raise BusinessError("Informe seu nome.")

        instrutor = User(
            nome=nome,
            sobrenome=texto_ou_none(dados.get("sobrenome")),
            email=email,
            senha=InstrutorService._hash(dados.get("senha")),
            ativo=True,
        )
        return BaseService.salvar(instrutor)

    @staticmethod
    def atualizar_conta(instrutor: User, dados: dict) -> User:
        """
        Atualiza dados do próprio instrutor. Trocar a senha exige a senha atual.
        """
        email = normalizar_email(dados.get("email"))
        if InstrutorService.email_em_uso(email, ignorar_id=instrutor.id):
            raise BusinessError("Já existe uma conta com este e-mail.")

        nova_senha = dados.get("nova_senha")
        if nova_senha:
            senha_atual = dados.get("senha_atual") or ""
            if not bcrypt.check_password_hash(instrutor.senha, senha_atual):
                raise BusinessError("Senha atual incorreta.")
            instrutor.senha = InstrutorService._hash(nova_senha)

        instrutor.nome = (dados.get("nome") or "").strip() or instrutor.nome
        instrutor.sobrenome = texto_ou_none(dados.get("sobrenome"))
        instrutor.email = email

        return BaseService.salvar(instrutor)

    @staticmethod
    def _hash(senha):
        if not senha or len(senha) < TAMANHO_MINIMO_SENHA:
            raise BusinessError(f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")
        return bcrypt.generate_password_hash(senha).decode("utf-8")
