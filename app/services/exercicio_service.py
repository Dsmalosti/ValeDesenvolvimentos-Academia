from app.models import Exercicio
from app.services.base_service import BaseService
from app.exceptions import BusinessError


class ExercicioService:

    @staticmethod
    def criar_exercicio(dados):
        """
        Docstring for criar_exercicio
        
        :param dados: Description
        """

        exercicio = Exercicio(
            nome=dados["nome"],
            grupo_muscular=dados["grupo_muscular"],
            descricao=dados.get("descricao"),
            video_url=dados.get("video_url"),
            ativo=dados.get("ativo", True)
        )

        return BaseService.salvar(exercicio)
    
    @staticmethod
    def editar_exercicio(exercicio_id:int, dados: dict) -> Exercicio:
        """
        Docstring for editar_exercicio
        
        :param id_exercicio: Description
        :type id_exercicio: int
        :param dados: Description
        :type dados: dict
        :return: Description
        :rtype: Exercicio
        """
        exercicio = Exercicio.query.get_or_404(exercicio_id)

        if not exercicio:
            raise BusinessError("Exercicio não encontrado")
        
        if "nome" in dados:
            exercicio.nome = dados["nome"]

        if "grupo_muscular" in dados:
            exercicio.grupo_muscular = dados["grupo_muscular"]

        if "descricao" in dados:
            exercicio.descricao = dados["descricao"]

        if "video_url" in dados:
            exercicio.video_url = dados["video_url"]

        if "ativo" in dados:
            exercicio.ativo = dados["ativo"]
        
        return BaseService.salvar(exercicio)
    
    @staticmethod
    def excluir_exercicio(exercicio_id: int):
        """
        Docstring for excluir_exercicio
        
        :param exercicio_id: Description
        :type exercicio_id: int
        """
        exercicio = Exercicio.query.get_or_404(exercicio_id)

        if not exercicio:
            raise BusinessError("Exercicio nao encontrado")
        
        BaseService.deletar(exercicio)

