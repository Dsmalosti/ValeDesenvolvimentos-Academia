from app.models import Aluno
from app.services.base_service import BaseService
from app.exceptions import BusinessError
from app.helpers.validators import validar_email, validar_cpf
from app.extensions.database import db
from app.helpers.conta import conta_id, da_conta


class AlunoService:

    @staticmethod
    def criar_aluno(dados, instrutor_id):
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
            plano_id=dados["plano_id"],
            instrutor_id=instrutor_id,   # [back-06-contas-e-papeis] agora é só "quem cadastrou"
            conta_id=conta_id(),         # [back-06-contas-e-papeis] a academia dona do aluno
        )

        return BaseService.salvar(aluno)

    @staticmethod
    def listar_alunos():
        """
        Lista somente os alunos da conta (academia) de quem está logado.
        [back-06-contas-e-papeis] antes: filtrava por instrutor_id, recebido por parâmetro.
        """
        return da_conta(Aluno).all()

    @staticmethod
    def editar_aluno(aluno_id: int, dados: dict) -> Aluno:
        """
        Regra de negócio para editar um aluno
        """

        aluno = da_conta(Aluno).filter_by(id=aluno_id).first()  # [back-06-contas-e-papeis] antes: instrutor_id=instrutor_id

        if not aluno:
            raise BusinessError("Aluno não encontrado")

        # ===== Regras de negócio =====

        if "email" in dados:
            validar_email(dados["email"])

            # garante unicidade
            # [back-06-contas-e-papeis] antes: Aluno.query, que olhava todas as academias e, pela mensagem de erro,
            # revelava que o e-mail existia em outra. Agora a checagem é só dentro da conta.
            email_existente = da_conta(Aluno).filter(
                Aluno.email == dados["email"],
                Aluno.id != aluno.id
            ).first()

            if email_existente:
                raise BusinessError("E-mail já cadastrado para outro aluno")

            aluno.email = dados["email"]

        if "cpf" in dados:
            validar_cpf(dados["cpf"])
            aluno.cpf = dados["cpf"]

        if "nome" in dados:
            aluno.nome = dados["nome"]

        if "telefone" in dados:
            aluno.telefone = dados["telefone"]

        if "data_nascimento" in dados:
            aluno.data_nascimento = dados["data_nascimento"]

        if "ativo" in dados:
            aluno.ativo = dados["ativo"]

        if "plano_id" in dados:
            aluno.plano_id = dados["plano_id"]

        return BaseService.salvar(aluno)

    @staticmethod
    def excluir_aluno(aluno_id: int):
        """
        Docstring for excluir_aluno

        :param aluno_id: id do aluno
        :type aluno_id: int
        """
        aluno = da_conta(Aluno).filter_by(id=aluno_id).first()  # [back-06-contas-e-papeis] antes: instrutor_id=instrutor_id

        if not aluno:
            raise BusinessError("Aluno não encontrado")

        BaseService.deletar(aluno)

    @staticmethod
    def salvar(aluno):
        try:
            db.session.add(aluno)
            db.session.commit()
            return aluno
        except Exception:
            db.session.rollback()
            raise BusinessError("Erro ao salvar aluno")

    @staticmethod
    def excluir(aluno):
        try:
            db.session.delete(aluno)
            db.session.commit()
            return aluno
        except Exception:
            db.session.rollback()
            raise BusinessError("Erro ao excluir aluno")

    @staticmethod
    def alternar_status(aluno_id: int) -> Aluno:
        """
        Ativa ou desativa um aluno (inverte o status atual)
        """
        aluno = da_conta(Aluno).filter_by(id=aluno_id).first()  # [back-06-contas-e-papeis] antes: instrutor_id=instrutor_id

        if not aluno:
            raise BusinessError("Aluno não encontrado")

        aluno.ativo = not aluno.ativo

        return BaseService.salvar(aluno)