from app.models import Aluno, Plano
from app.services.base_service import BaseService
from app.exceptions import BusinessError
from app.extensions.database import db
from app.helpers.date_helper import hoje
from app.helpers.validators import normalizar_cpf, normalizar_email, normalizar_telefone


class AlunoService:

    @staticmethod
    def criar_aluno(instrutor_id: int, dados: dict) -> Aluno:
        """
        Regra de negocio para criar alunos
        """
        aluno = Aluno(instrutor_id=instrutor_id)
        AlunoService._aplicar(aluno, dados)
        return BaseService.salvar(aluno)

    @staticmethod
    def editar_aluno(aluno: Aluno, dados: dict) -> Aluno:
        """
        Regra de negócio para editar um aluno
        """
        AlunoService._aplicar(aluno, dados)
        return BaseService.salvar(aluno)

    @staticmethod
    def renovar_plano(aluno: Aluno) -> Aluno:
        """
        Inicia um novo ciclo do plano. Renovação antecipada não perde os dias restantes.
        """
        if not aluno.plano:
            raise BusinessError("Este aluno não tem plano para renovar.")

        vencimento = aluno.data_vencimento
        aluno.data_inicio_plano = max(hoje(), vencimento) if vencimento else hoje()
        aluno.ativo = True
        return BaseService.salvar(aluno)

    @staticmethod
    def excluir_aluno(aluno: Aluno):
        BaseService.deletar(aluno)

    @staticmethod
    def excluir_varios(instrutor_id: int, aluno_ids: list[int]) -> int:
        """
        Exclui vários alunos de uma vez, apenas os que pertencem à academia
        """
        if not aluno_ids:
            return 0

        alunos = Aluno.query.filter(
            Aluno.instrutor_id == instrutor_id,
            Aluno.id.in_(aluno_ids),
        ).all()
        for aluno in alunos:
            db.session.delete(aluno)
        BaseService.commit()
        return len(alunos)

    @staticmethod
    def _aplicar(aluno, dados):
        nome = (dados.get("nome") or "").strip()
        if not nome:
            raise BusinessError("Informe o nome do aluno.")

        email = normalizar_email(dados.get("email"))
        cpf = normalizar_cpf(dados.get("cpf"))
        telefone = normalizar_telefone(dados.get("telefone"))

        data_nascimento = dados.get("data_nascimento")
        if data_nascimento and data_nascimento > hoje():
            raise BusinessError("A data de nascimento não pode estar no futuro.")

        plano = AlunoService._validar_plano(aluno.instrutor_id, dados.get("plano_id"))
        # valida antes de alterar o objeto para o autoflush não gravar dados inválidos
        AlunoService._validar_unicidade(aluno, email, cpf)

        aluno.nome = nome
        aluno.email = email
        aluno.cpf = cpf
        aluno.telefone = telefone
        aluno.data_nascimento = data_nascimento
        aluno.plano_id = plano.id
        aluno.data_inicio_plano = dados.get("data_inicio_plano") or aluno.data_inicio_plano or hoje()
        aluno.ativo = bool(dados.get("ativo", True))

    @staticmethod
    def _validar_plano(instrutor_id, plano_id):
        plano = db.session.get(Plano, plano_id) if plano_id else None
        if plano is None or plano.instrutor_id != instrutor_id:
            raise BusinessError("Selecione um plano válido.")
        return plano

    @staticmethod
    def _validar_unicidade(aluno, email, cpf):
        query = Aluno.query.filter(Aluno.instrutor_id == aluno.instrutor_id)
        if aluno.id:
            query = query.filter(Aluno.id != aluno.id)

        with db.session.no_autoflush:
            if query.filter(Aluno.email == email).first():
                raise BusinessError("Já existe um aluno com este e-mail.")
            if cpf and query.filter(Aluno.cpf == cpf).first():
                raise BusinessError("Já existe um aluno com este CPF.")
