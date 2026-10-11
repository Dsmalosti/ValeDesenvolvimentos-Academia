"""
Isolamento entre contas (academias) e permissão por papel.

[back-03-isolamento] Criado. Regra do sistema: uma academia NUNCA vê, edita ou apaga dado de
outra. Toda consulta que busca dado de negócio passa por uma das funções daqui, em vez de usar
Model.query direto. Assim o filtro fica num lugar só e ninguém esquece.

[back-06-contas-e-papeis] A "conta" deixou de ser o próprio usuário logado e passou a ser a
academia dele (tabela `contas`, coluna `conta_id`). Antes: `conta_id()` devolvia
`current_user.id` e os filtros usavam a coluna `instrutor_id`. Com isso o dono, a recepção e os
instrutores de uma mesma academia passam a ver os mesmos alunos. Entrou também o
`papel_requerido`, que bloqueia no servidor o que cada papel não pode fazer.

Quando o registro não é da conta, as rotas respondem 404 (e não 403): o 403 confirmaria
para um curioso que aquele id existe em outra academia. O 403 fica para quando a pessoa É da
conta, mas o papel dela não permite a ação.
"""
from functools import wraps

from flask import abort
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.models import PAPEL_INSTRUTOR, PAPEL_PROPRIETARIO, PAPEL_RECEPCAO, Aluno, Exercicio, Ficha, Treino

# atalhos para os decorators das rotas
DONO = (PAPEL_PROPRIETARIO,)
DONO_E_RECEPCAO = (PAPEL_PROPRIETARIO, PAPEL_RECEPCAO)


def conta_id():
    """Id da conta (academia) de quem está logado."""
    return current_user.conta_id


def da_conta(modelo):
    """
    Consulta já filtrada pela conta de quem está logado.

    Serve para os modelos que têm a coluna `conta_id` (Aluno, Plano, Pagamento, User).
    Uso:  da_conta(Aluno).filter_by(id=aluno_id).first_or_404()
    """
    return modelo.query.filter_by(conta_id=conta_id())


def fichas_da_conta():
    """
    Fichas da conta. A ficha não tem dono direto: ela é de um aluno, e o aluno é da conta.
    Por isso o filtro passa pelo aluno (join).
    """
    return Ficha.query.join(Aluno, Ficha.aluno_id == Aluno.id).filter(Aluno.conta_id == conta_id())


def treinos_da_conta():
    """Treinos da conta: o treino é de uma ficha, a ficha é de um aluno, o aluno é da conta."""
    return (Treino.query
            .join(Ficha, Treino.ficha_id == Ficha.id)
            .join(Aluno, Ficha.aluno_id == Aluno.id)
            .filter(Aluno.conta_id == conta_id()))


def exercicios_visiveis():
    """Exercícios que a conta pode USAR: os do catálogo padrão (sem dono) e os que ela criou."""
    return Exercicio.query.filter(or_(Exercicio.conta_id.is_(None), Exercicio.conta_id == conta_id()))


def exercicios_proprios():
    """Exercícios que a conta pode EDITAR e EXCLUIR: só os que ela criou."""
    return Exercicio.query.filter(Exercicio.conta_id == conta_id())


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


def papel_requerido(*papeis):
    """
    Decorator: só deixa passar quem tem um dos papéis informados; os outros recebem 403.

    Uso:  @papel_requerido(*DONO_E_RECEPCAO)   ->  instrutor não entra
          @papel_requerido(*DONO)              ->  só o dono
    Esconder o botão no template é só aparência: quem bloqueia de verdade é a rota.
    Vai DEPOIS do @route e do @login_required (mais perto da função).
    """
    def decorador(funcao):
        @wraps(funcao)
        def protegida(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.papel not in papeis:
                abort(403)
            return funcao(*args, **kwargs)
        return protegida
    return decorador


def exigir_papel_em(blueprint, *papeis):
    """O mesmo que papel_requerido, para TODAS as rotas de um blueprint (ex.: o financeiro)."""
    @blueprint.before_request
    @login_required
    def _exigir_papel():
        if current_user.papel not in papeis:
            abort(403)
        return None
