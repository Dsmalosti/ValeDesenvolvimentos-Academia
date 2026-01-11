from app.models import Plano
from app.services.base_service import BaseService
from app.exceptions import BusinessError

class PlanoService:

    @staticmethod
    def criar_plano(dados):
        print("CRIANDO PLANO:", dados)

        """
        Docstring for criar_plano
        """
        plano = Plano(
            nome=dados["nome"],
            valor=dados["valor"],
            duracao_dias=dados["duracao_dias"],
            descricao=dados["descricao"],
            ativo=dados.get("ativo", True)
        )

        return BaseService.salvar(plano)
    
    @staticmethod
    def editar_plano(plano_id: int, dados: dict) -> Plano:
        '''Regra de negocio para ediitar um plano'''
        
        plano = Plano.query.get_or_404(plano_id)

        if not plano:
            raise BusinessError("Aluno não encontrado")
        
        if "nome" in dados:
            plano.nome = dados["nome"]

        if "valor" in dados:
            plano.valor = dados["valor"]

        if "duracao_dias" in dados:
            plano.duracao_dias = dados["duracao_dias"]

        if "descricao" in dados:
            plano.descricao = dados["descricao"]

        if "ativo" in dados:
            plano.ativo = dados["ativo"]
        
        return BaseService.salvar(plano)
    
    @staticmethod
    def excluir_plano(plano_id: int):
        """
        Docstring for excluir_plano
        
        :param plano_id: Description
        :type plano_id: int
        """
        plano = Plano.query.get_or_404(plano_id)

        if not plano:
            raise BusinessError("Plano não encontrado")
        
        BaseService.deletar(plano)

    