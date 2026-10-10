from app.models import Plano
from app.services.base_service import BaseService
from app.exceptions import BusinessError
from app.helpers.conta import conta_id, da_conta

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
            instrutor_id=instrutor_id,   # [back-06-contas-e-papeis] agora é só "quem cadastrou"
            conta_id=conta_id(),         # [back-06-contas-e-papeis] a academia dona do plano
        )

        return BaseService.salvar(plano)

    @staticmethod
    def listar_planos():
        """
        Lista somente os planos da conta (academia) de quem está logado.
        [back-06-contas-e-papeis] antes: filtrava por instrutor_id, recebido por parâmetro.
        """
        return da_conta(Plano).all()

    @staticmethod
    def editar_plano(plano_id: int, dados: dict) -> Plano:
        '''Regra de negocio para ediitar um plano'''

        plano = da_conta(Plano).filter_by(id=plano_id).first()  # [back-06-contas-e-papeis] antes: instrutor_id=instrutor_id

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
    def excluir_plano(plano_id: int):
        """
        Docstring for excluir_plano

        :param plano_id: Description
        :type plano_id: int
        """
        plano = da_conta(Plano).filter_by(id=plano_id).first()  # [back-06-contas-e-papeis] antes: instrutor_id=instrutor_id

        if not plano:
            raise BusinessError("Plano não encontrado")

        BaseService.deletar(plano)