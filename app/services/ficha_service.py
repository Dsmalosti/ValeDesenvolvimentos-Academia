from app.models import Aluno, DIAS_SEMANA, Exercicio, Ficha, Treino, TreinoExercicio
from app.services.base_service import BaseService
from app.exceptions import BusinessError
from app.extensions.database import db
from app.helpers.validators import texto_ou_none


class FichaService:

    # ===== Ficha =====

    @staticmethod
    def criar_ficha(instrutor_id: int, dados: dict) -> Ficha:
        aluno = FichaService._validar_aluno(instrutor_id, dados.get("aluno_id"))
        ficha = Ficha(instrutor_id=instrutor_id, aluno_id=aluno.id)
        FichaService._aplicar(ficha, dados)
        return BaseService.salvar(ficha)

    @staticmethod
    def editar_ficha(ficha: Ficha, dados: dict) -> Ficha:
        aluno = FichaService._validar_aluno(ficha.instrutor_id, dados.get("aluno_id"))
        ficha.aluno_id = aluno.id
        FichaService._aplicar(ficha, dados)
        return BaseService.salvar(ficha)

    @staticmethod
    def excluir_ficha(ficha: Ficha):
        BaseService.deletar(ficha)

    # ===== Treinos (um por dia da semana) =====

    @staticmethod
    def adicionar_treino(ficha: Ficha, dia_semana: str) -> Treino:
        FichaService._validar_dia(ficha, dia_semana)
        return BaseService.salvar(Treino(ficha_id=ficha.id, dia_semana=dia_semana))

    @staticmethod
    def editar_treino(treino: Treino, dia_semana: str) -> Treino:
        FichaService._validar_dia(treino.ficha, dia_semana, ignorar=treino)
        treino.dia_semana = dia_semana
        return BaseService.salvar(treino)

    @staticmethod
    def excluir_treino(treino: Treino):
        BaseService.deletar(treino)

    # ===== Exercícios do treino =====

    @staticmethod
    def adicionar_exercicio(treino: Treino, dados: dict) -> TreinoExercicio:
        exercicio = db.session.get(Exercicio, dados.get("exercicio_id")) if dados.get("exercicio_id") else None
        if exercicio is None or exercicio.instrutor_id != treino.ficha.instrutor_id:
            raise BusinessError("Selecione um exercício válido.")

        series = dados.get("series")
        if not series or not 1 <= series <= 20:
            raise BusinessError("Informe entre 1 e 20 séries.")

        repeticoes = (dados.get("repeticoes") or "").strip()
        if not repeticoes:
            raise BusinessError("Informe as repetições.")

        item = TreinoExercicio(
            treino_id=treino.id,
            exercicio_id=exercicio.id,
            series=series,
            repeticoes=repeticoes,
            carga=texto_ou_none(dados.get("carga")),
            observacoes=texto_ou_none(dados.get("observacoes")),
        )
        return BaseService.salvar(item)

    @staticmethod
    def remover_exercicio(item: TreinoExercicio):
        BaseService.deletar(item)

    # ===== Regras internas =====

    @staticmethod
    def _aplicar(ficha, dados):
        nome = (dados.get("nome") or "").strip()
        if not nome:
            raise BusinessError("Informe o nome da ficha.")
        ficha.nome = nome
        ficha.observacoes = texto_ou_none(dados.get("observacoes"))
        ficha.ativo = bool(dados.get("ativo", True))

    @staticmethod
    def _validar_aluno(instrutor_id, aluno_id):
        aluno = db.session.get(Aluno, aluno_id) if aluno_id else None
        if aluno is None or aluno.instrutor_id != instrutor_id:
            raise BusinessError("Selecione um aluno válido.")
        return aluno

    @staticmethod
    def _validar_dia(ficha, dia_semana, ignorar=None):
        if dia_semana not in dict(DIAS_SEMANA):
            raise BusinessError("Selecione um dia da semana válido.")
        for treino in ficha.treinos:
            if treino is not ignorar and treino.dia_semana == dia_semana:
                raise BusinessError("Esta ficha já tem um treino nesse dia.")
