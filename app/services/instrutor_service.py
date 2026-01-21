from app.models import User
from app.services.base_service import BaseService
from app.exceptions import BusinessError
from app.extensions.security import bcrypt


class InstrutorService:

    @staticmethod
    def criar_instrutor(dados):
        """
        Docstring for criar_instrutor
        
        :param dados: Description
        """
        instrutor = User(
            nome=dados["nome"],
            sobrenome=dados["sobrenome"],
            email=dados["email"],
            senha=dados["senha"]
        )

        return BaseService.salvar(instrutor)
    
    @staticmethod
    def editar_instrutor(instrutor_id: int, dados: dict) -> User:
        """
        Docstring for editar_instrutor
        
        :param instrutor_id: Description
        :type instrutor_id: int
        :param dados: Description
        :type dados: dict
        :return: Description
        :rtype: User
        """
        instrutor = User.query.get_or_404(instrutor_id)

        if not instrutor:
            raise BusinessError("Instrutor não encontrado")
        
        if "nome" in dados:
            instrutor.nome = dados["nome"]

        if "sobrenome" in dados:
            instrutor.sobrenome = dados["sobrenome"]

        if "email" in dados:
            instrutor.email = dados["email"]

         # Se a senha foi preenchida, altera
        if dados.get("senha"):
            instrutor.senha = bcrypt.generate_password_hash(
                dados["senha"]
            ).decode("utf-8")
        
        return BaseService.salvar(instrutor)
    
    @staticmethod
    def excluir_instrutor(instrutor_id: int):
        """
        Docstring for excluir_instrutor
        
        :param instrutor_id: Description
        :type instrutor_id: int
        """
        instrutor = User.query.get_or_404(instrutor_id)

        if not instrutor:
            raise BusinessError("Instrutor não encontrado!")
        
        return BaseService.deletar(instrutor)