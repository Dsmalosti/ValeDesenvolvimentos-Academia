from datetime import date, timedelta

from app.models import Pagamento, Aluno
from app.services.base_service import BaseService
from app.exceptions import BusinessError
from app.helpers.conta import conta_id, da_conta


class PagamentoService:

    @staticmethod
    def registrar_pagamento(aluno_id: int, dados: dict, instrutor_id: int) -> Pagamento:
        aluno = da_conta(Aluno).filter_by(id=aluno_id).first()  # [back-06-contas-e-papeis] antes: instrutor_id=instrutor_id

        if not aluno:
            raise BusinessError("Aluno não encontrado")

        if not aluno.plano:
            raise BusinessError("Aluno não possui um plano vinculado")

        data_pagamento = dados["data_pagamento"]
        data_vencimento = data_pagamento + timedelta(days=aluno.plano.duracao_dias)

        pagamento = Pagamento(
            aluno_id=aluno.id,
            instrutor_id=instrutor_id,   # [back-06-contas-e-papeis] agora é só "quem registrou"
            conta_id=conta_id(),         # [back-06-contas-e-papeis] a academia dona do pagamento
            valor=dados["valor"],
            data_pagamento=data_pagamento,
            data_vencimento=data_vencimento,
            forma_pagamento=dados.get("forma_pagamento"),
            observacao=dados.get("observacao"),
        )

        return BaseService.salvar(pagamento)

    @staticmethod
    def listar_pagamentos_aluno(aluno_id: int):
        # [back-06-contas-e-papeis] antes: Pagamento.query.filter_by(aluno_id=..., instrutor_id=instrutor_id)
        return da_conta(Pagamento).filter_by(
            aluno_id=aluno_id
        ).order_by(Pagamento.data_pagamento.desc()).all()

    @staticmethod
    def status_pagamento(aluno: Aluno) -> str:
        """
        Retorna 'em_dia', 'vencido' ou 'sem_pagamento', baseado no
        vencimento mais recente entre os pagamentos do aluno.
        """
        ultimo = da_conta(Pagamento).filter_by(aluno_id=aluno.id).order_by(
            Pagamento.data_vencimento.desc()
        ).first()

        if not ultimo:
            return "sem_pagamento"

        if ultimo.data_vencimento < date.today():
            return "vencido"

        return "em_dia"

    @staticmethod
    def listar_status_alunos():
        """
        Retorna uma lista de tuplas (aluno, status) para todos os
        alunos da conta (academia) de quem está logado.
        """
        alunos = da_conta(Aluno).all()  # [back-06-contas-e-papeis] antes: filter_by(instrutor_id=instrutor_id)
        return [(aluno, PagamentoService.status_pagamento(aluno)) for aluno in alunos]