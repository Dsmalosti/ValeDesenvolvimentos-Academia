from datetime import date, timedelta

from app.models import Pagamento, Aluno
from app.services.base_service import BaseService
from app.exceptions import BusinessError


class PagamentoService:

    @staticmethod
    def registrar_pagamento(aluno_id: int, dados: dict, instrutor_id: int) -> Pagamento:
        aluno = Aluno.query.filter_by(id=aluno_id, instrutor_id=instrutor_id).first()

        if not aluno:
            raise BusinessError("Aluno não encontrado")

        if not aluno.plano:
            raise BusinessError("Aluno não possui um plano vinculado")

        data_pagamento = dados["data_pagamento"]
        data_vencimento = data_pagamento + timedelta(days=aluno.plano.duracao_dias)

        pagamento = Pagamento(
            aluno_id=aluno.id,
            instrutor_id=instrutor_id,
            valor=dados["valor"],
            data_pagamento=data_pagamento,
            data_vencimento=data_vencimento,
            forma_pagamento=dados.get("forma_pagamento"),
            observacao=dados.get("observacao"),
        )

        return BaseService.salvar(pagamento)

    @staticmethod
    def listar_pagamentos_aluno(aluno_id: int, instrutor_id: int):
        return Pagamento.query.filter_by(
            aluno_id=aluno_id, instrutor_id=instrutor_id
        ).order_by(Pagamento.data_pagamento.desc()).all()

    @staticmethod
    def status_pagamento(aluno: Aluno) -> str:
        """
        Retorna 'em_dia', 'vencido' ou 'sem_pagamento', baseado no
        vencimento mais recente entre os pagamentos do aluno.
        """
        ultimo = Pagamento.query.filter_by(aluno_id=aluno.id).order_by(
            Pagamento.data_vencimento.desc()
        ).first()

        if not ultimo:
            return "sem_pagamento"

        if ultimo.data_vencimento < date.today():
            return "vencido"

        return "em_dia"

    @staticmethod
    def listar_status_alunos(instrutor_id: int):
        """
        Retorna uma lista de tuplas (aluno, status) para todos os
        alunos do instrutor logado.
        """
        alunos = Aluno.query.filter_by(instrutor_id=instrutor_id).all()
        return [(aluno, PagamentoService.status_pagamento(aluno)) for aluno in alunos]