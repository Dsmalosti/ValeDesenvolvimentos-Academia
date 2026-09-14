from app.models import Aluno, Plano
from app.services.base_service import BaseService
from app.exceptions import BusinessError
from app.helpers.validators import texto_ou_none


class PlanoService:

    @staticmethod
    def criar_plano(instrutor_id: int, dados: dict) -> Plano:
        plano = Plano(instrutor_id=instrutor_id)
        PlanoService._aplicar(plano, dados)
        return BaseService.salvar(plano)

    @staticmethod
    def editar_plano(plano: Plano, dados: dict) -> Plano:
        PlanoService._aplicar(plano, dados)
        return BaseService.salvar(plano)

    @staticmethod
    def excluir_plano(plano: Plano):
        if Aluno.query.filter_by(plano_id=plano.id).first():
            raise BusinessError(
                "Este plano tem alunos vinculados. Desative-o para parar de oferecer sem perder o histórico."
            )
        BaseService.deletar(plano)

    @staticmethod
    def _aplicar(plano, dados):
        nome = (dados.get("nome") or "").strip()
        if not nome:
            raise BusinessError("Informe o nome do plano.")

        valor = dados.get("valor")
        if valor is None or valor < 0:
            raise BusinessError("Informe um valor válido.")

        duracao = dados.get("duracao_dias")
        if not duracao or duracao < 1:
            raise BusinessError("A duração precisa ser de pelo menos 1 dia.")

        plano.nome = nome
        plano.valor = valor
        plano.duracao_dias = int(duracao)
        plano.descricao = texto_ou_none(dados.get("descricao"))
        plano.ativo = bool(dados.get("ativo", True))
