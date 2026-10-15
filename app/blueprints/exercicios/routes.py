# [back-27-telas-antigas] antes também importava db, flask_login, ExercicioForm, Exercicio e ExercicioService (só as telas antigas usavam)
from flask import Blueprint,render_template, url_for, request, redirect, flash, abort
from app.services import treino_service as treinos  # [back-14-treinos] regras das telas novas
from app.helpers.conta import exigir_login_em

exercicios_blueprint = Blueprint('exercicios', __name__, url_prefix='/exercicios')  # [back-27-telas-antigas] antes: template_folder='templates'
exigir_login_em(exercicios_blueprint)  # [back-03-isolamento] toda rota daqui exige login, mesmo as futuras
# [back-06-contas-e-papeis] O exercício agora tem dono. A conta USA os do catálogo padrão (sem dono) e os que ela
# criou; EDITA e EXCLUI só os que ela criou. Antes era um catálogo único, que qualquer academia
# logada editava e apagava.

# ---------------------------------------------------------------------------
# [back-14-treinos] TELAS DE EXERCÍCIOS DO FRONT NOVO (templates/exercicios/).
# Os nomes das funções e os endereços são os do contrato do front: 'exercicios.lista',
# 'exercicios.detalhe', 'exercicios.novo' e 'exercicios.editar'.
# Antes (back-04), 'lista' era só uma ponte para a tela antiga (/exercicios/listar/); as outras
# três não existiam com estes nomes. [back-27-telas-antigas] As rotas ANTIGAS (/exercicios/criar/, /listar/, /editar/<id>,
# /excluir/<id>) saíram junto com o layout antigo.
# As regras ficam em services/treino_service.py.
# ---------------------------------------------------------------------------
@exercicios_blueprint.route('')
def lista():
    return render_template('exercicios/lista.html', **treinos.contexto_da_lista_de_exercicios(request.args))


@exercicios_blueprint.route('/<int:id>')
def detalhe(id):
    exercicio = treinos.exercicio_visivel(id) or abort(404)
    return render_template('exercicios/detalhe.html', e=treinos.detalhe_do_exercicio(exercicio))


def _formulario(exercicio=None):
    """Tela e gravação do formulário de exercício (novo e editar)."""
    opcoes = [(g, g) for g in treinos.GRUPOS]
    modo = 'editar' if exercicio else 'novo'
    if request.method == 'POST':
        valores, erros = treinos.validar_exercicio(request.form)
        if erros:
            flash('Revise os campos destacados.', 'error')
            return render_template('exercicios/form.html', e=dict(valores, id=exercicio.id if exercicio else None), erros=erros,
                                   grupos_opcoes=opcoes, modo=modo)
        treinos.salvar_exercicio(valores, exercicio)
        flash('Exercício salvo.', 'success')
        return redirect(url_for('exercicios.lista'))
    dados = treinos.detalhe_do_exercicio(exercicio) if exercicio else {}
    if dados:
        dados['equipamento'] = exercicio.equipamento or ''
    return render_template('exercicios/form.html', e=dados, erros={}, grupos_opcoes=opcoes, modo=modo)


@exercicios_blueprint.route('/novo', methods=['GET', 'POST'])
def novo():
    return _formulario()


@exercicios_blueprint.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar(id):
    exercicio = treinos.exercicio_proprio(id)
    if exercicio is None:
        # Existe, mas é do catálogo padrão (que toda academia usa e ninguém altera)? Avisa. Senão, 404.
        if treinos.exercicio_visivel(id) is None:
            abort(404)
        flash('Este exercício é do catálogo padrão e não pode ser alterado. Crie um exercício seu em "Novo exercício".', 'info')
        return redirect(url_for('exercicios.detalhe', id=id))
    return _formulario(exercicio)
