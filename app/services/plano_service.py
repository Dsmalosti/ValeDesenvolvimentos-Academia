from app.models import Plano
from app.services.base_service import BaseService
from app.exceptions import BusinessError

class PlanoService:

    @staticmethod
    def criar_plano(dados, instrutor_id):
        # [back-02-limpeza] antes: print("CRIANDO PLANO:", dados)

        """
        Docstring for criar_plano
        """
        plano = Plano(
            nome=dados["nome"],
            valor=dados["valor"],
            duracao_dias=dados["duracao_dias"],
            descricao=dados["descricao"],
            ativo=dados.get("ativo", True),
            instrutor_id=instrutor_id
        )

        return BaseService.salvar(plano)

    @staticmethod
    def listar_planos(instrutor_id: int):
        """
        Lista somente os planos do instrutor logado
        """
        return Plano.query.filter_by(instrutor_id=instrutor_id).all()

    @staticmethod
    def editar_plano(plano_id: int, dados: dict, instrutor_id: int) -> Plano:
        '''Regra de negocio para ediitar um plano'''

        plano = Plano.query.filter_by(id=plano_id, instrutor_id=instrutor_id).first()

        if not plano:
            raise BusinessError("Plano não encontrado")

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
    def excluir_plano(plano_id: int, instrutor_id: int):
        """
        Docstring for excluir_plano

        :param plano_id: Description
        :type plano_id: int
        """
        plano = Plano.query.filter_by(id=plano_id, instrutor_id=instrutor_id).first()

        if not plano:
            raise BusinessError("Plano não encontrado")

        BaseService.deletar(plano)