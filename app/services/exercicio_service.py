from app.models import Exercicio
from app.services.base_service import BaseService
from app.exceptions import BusinessError
from app.helpers.conta import conta_id, exercicios_proprios


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
            ativo=dados.get("ativo", True),
            conta_id=conta_id(),   # [back-06-contas-e-papeis] o exercício nasce como da academia que o criou
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
        # [back-06-contas-e-papeis] antes: Exercicio.query.get_or_404(id). Qualquer academia editava ou apagava o exercício
        # de qualquer outra. Agora só os que a própria conta criou; o resto responde 404.
        exercicio = exercicios_proprios().filter_by(id=exercicio_id).first_or_404()

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
        # [back-06-contas-e-papeis] antes: Exercicio.query.get_or_404(id). Qualquer academia editava ou apagava o exercício
        # de qualquer outra. Agora só os que a própria conta criou; o resto responde 404.
        exercicio = exercicios_proprios().filter_by(id=exercicio_id).first_or_404()

        if not exercicio:
            raise BusinessError("Exercicio nao encontrado")
        
        BaseService.deletar(exercicio)

