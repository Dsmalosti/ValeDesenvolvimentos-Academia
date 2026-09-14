from sqlalchemy import func

from app.models import Exercicio, GRUPOS_MUSCULARES, TreinoExercicio
from app.services.base_service import BaseService
from app.exceptions import BusinessError
from app.extensions.database import db
from app.helpers.validators import texto_ou_none

# Biblioteca inicial oferecida no onboarding (reduz o tempo até a primeira ficha)
EXERCICIOS_PADRAO = [
    ("Supino reto com barra", "peito"),
    ("Supino inclinado com halteres", "peito"),
    ("Crucifixo com halteres", "peito"),
    ("Crossover na polia", "peito"),
    ("Puxada frontal", "costas"),
    ("Remada curvada com barra", "costas"),
    ("Remada baixa na polia", "costas"),
    ("Levantamento terra", "costas"),
    ("Desenvolvimento com halteres", "ombro"),
    ("Elevação lateral", "ombro"),
    ("Elevação frontal", "ombro"),
    ("Rosca direta com barra", "biceps"),
    ("Rosca alternada com halteres", "biceps"),
    ("Rosca martelo", "biceps"),
    ("Tríceps na polia", "triceps"),
    ("Tríceps testa", "triceps"),
    ("Mergulho no banco", "triceps"),
    ("Agachamento livre", "pernas"),
    ("Leg press 45°", "pernas"),
    ("Cadeira extensora", "pernas"),
    ("Mesa flexora", "pernas"),
    ("Panturrilha em pé", "pernas"),
    ("Elevação pélvica", "gluteo"),
    ("Afundo com halteres", "gluteo"),
    ("Abdominal supra", "abdomen"),
    ("Prancha", "abdomen"),
]


class ExercicioService:

    @staticmethod
    def criar_exercicio(instrutor_id: int, dados: dict) -> Exercicio:
        exercicio = Exercicio(instrutor_id=instrutor_id)
        ExercicioService._aplicar(exercicio, dados)
        return BaseService.salvar(exercicio)

    @staticmethod
    def editar_exercicio(exercicio: Exercicio, dados: dict) -> Exercicio:
        ExercicioService._aplicar(exercicio, dados)
        return BaseService.salvar(exercicio)

    @staticmethod
    def excluir_exercicio(exercicio: Exercicio):
        if TreinoExercicio.query.filter_by(exercicio_id=exercicio.id).first():
            raise BusinessError(
                "Este exercício está em fichas de treino. Desative-o para esconder de novas fichas."
            )
        BaseService.deletar(exercicio)

    @staticmethod
    def importar_padrao(instrutor_id: int) -> int:
        """Adiciona a biblioteca padrão, pulando nomes que a academia já tem."""
        existentes = {
            nome.lower()
            for (nome,) in db.session.query(func.lower(Exercicio.nome))
            .filter(Exercicio.instrutor_id == instrutor_id)
            .all()
        }
        novos = [
            Exercicio(instrutor_id=instrutor_id, nome=nome, grupo_muscular=grupo, ativo=True)
            for nome, grupo in EXERCICIOS_PADRAO
            if nome.lower() not in existentes
        ]
        db.session.add_all(novos)
        BaseService.commit()
        return len(novos)

    @staticmethod
    def _aplicar(exercicio, dados):
        nome = (dados.get("nome") or "").strip()
        if not nome:
            raise BusinessError("Informe o nome do exercício.")

        grupo = dados.get("grupo_muscular")
        if grupo not in dict(GRUPOS_MUSCULARES):
            raise BusinessError("Selecione um grupo muscular válido.")

        exercicio.nome = nome
        exercicio.grupo_muscular = grupo
        exercicio.descricao = texto_ou_none(dados.get("descricao"))
        exercicio.video_url = texto_ou_none(dados.get("video_url"))
        exercicio.ativo = bool(dados.get("ativo", True))
