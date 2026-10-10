"""
Isolamento entre contas (academias).

[back-03-isolamento] Criado nesta branch. Regra do sistema: uma academia NUNCA vê, edita ou
apaga dado de outra. Toda consulta que busca dado de negócio passa por uma das funções daqui,
em vez de usar Model.query direto. Assim o filtro fica num lugar só e ninguém esquece.

Hoje a "conta" é o próprio usuário logado (cada linha de `instrutores` é uma academia).
Quando a tabela `contas` existir (tarefa 3.2), só a função `conta_id()` muda: o resto do
sistema continua igual.

Quando o registro não é da conta, as rotas respondem 404 (e não 403): o 403 confirmaria
para um curioso que aquele id existe em outra academia.
"""
from flask_login import current_user, login_required

from app.models import Aluno, Ficha, Treino


def conta_id():
    """Id da conta (academia) de quem está logado."""
    return current_user.id


def da_conta(modelo):
    """
    Consulta já filtrada pela conta de quem está logado.

    Serve para os modelos que têm a coluna `instrutor_id` (Aluno, Plano, Pagamento).
    Uso:  da_conta(Aluno).filter_by(id=aluno_id).first_or_404()
    """
    return modelo.query.filter_by(instrutor_id=conta_id())


def fichas_da_conta():
    """
    Fichas da conta. A ficha não tem dono direto: ela é de um aluno, e o aluno é da conta.
    Por isso o filtro passa pelo aluno (join).
    """
    return Ficha.query.join(Aluno, Ficha.aluno_id == Aluno.id).filter(Aluno.instrutor_id == conta_id())


def treinos_da_conta():
    """Treinos da conta: o treino é de uma ficha, a ficha é de um aluno, o aluno é da conta."""
    return (Treino.query
            .join(Ficha, Treino.ficha_id == Ficha.id)
            .join(Aluno, Ficha.aluno_id == Aluno.id)
            .filter(Aluno.instrutor_id == conta_id()))


def exigir_login_em(blueprint):
    """
    Faz TODAS as rotas do blueprint exigirem login, inclusive as que forem criadas depois.

    O @login_required em cada rota continua valendo; isto é a segunda tranca, para o caso de
    alguém esquecer o decorator numa rota nova (foi o que aconteceu em duas rotas de fichas).
    Só usar em blueprint que não tem nenhuma página pública.
    """
    @blueprint.before_request
    @login_required
    def _exigir_login():
        return None
