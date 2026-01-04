from app.models import Aluno
from app.services.base_service import BaseService


class AlunoService:

    @staticmethod
    def criar_aluno(dados):
        """
        Regra de negocio para criar alunos
        """

        if not dados.get("plano_id"):
            raise ValueError("Aluno precisa estar vinculado a um plano")
        aluno = Aluno(
            nome=dados["nome"],
            email=dados["email"],
            telefone=dados.get("telefone"),
            data_nascimento=dados.get("data_nascimento"),
            cpf=dados.get("cpf"),
            ativo=dados.get("ativo", True),
            plano_id=dados["plano_id"]
        )

        return AlunoService.salvar(aluno)