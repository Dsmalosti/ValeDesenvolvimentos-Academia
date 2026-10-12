from app.extensions.database import db
from flask import Blueprint,render_template, url_for, request, redirect, flash, abort
from flask_login import login_user, logout_user, current_user, login_required
from app.blueprints.exercicios.form import ExercicioForm
from app.models import Exercicio
from app.services.exercicio_service import ExercicioService
from app.services import treino_service as treinos  # [back-14-treinos] regras das telas novas
from app.exceptions import BusinessError
from app.helpers.conta import exercicios_proprios, exercicios_visiveis, exigir_login_em

exercicios_blueprint = Blueprint('exercicios', __name__, url_prefix='/exercicios', template_folder='templates')
exigir_login_em(exercicios_blueprint)  # [back-03-isolamento] toda rota daqui exige login, mesmo as futuras
# [back-06-contas-e-papeis] O exercício agora tem dono. A conta USA os do catálogo padrão (sem dono) e os que ela
# criou; EDITA e EXCLUI só os que ela criou. Antes era um catálogo único, que qualquer academia
# logada editava e apagava.

# Rota criar exercicio
@exercicios_blueprint.route('/criar/', methods=['GET', 'POST'])
@login_required
def criarExercicio():
    form = ExercicioForm()
    if form.validate_on_submit():
        dados = {
            "nome":form.nome.data,
            "grupo_muscular":form.grupo_muscular.data,
            "descricao":form.descricao.data,
            "video_url":form.video_url.data,
            "ativo":form.ativo.data
        }
        try:
            ExercicioService.criar_exercicio(dados)
            flash('Exercicio criado com sucesso!', 'success')
            return redirect(url_for('exercicios.listarExercicios'))
        except BusinessError as e:
            flash(str(e), "danger")

        except Exception:
            flash("Erro inesperado ao criar exercicio", "danger")
    
    return render_template('exercicio_form.html', form=form, titulo='Criar exercicio')

# Rota listar
@exercicios_blueprint.route('/listar/')
@login_required
def listarExercicios():
    exercicios = exercicios_visiveis().all()  # [back-06-contas-e-papeis] antes: Exercicio.query.all()
    
    return render_template('exercicio-lista.html', exercicios=exercicios)

# Rota editar
@exercicios_blueprint.route('/editar/<int:exercicio_id>', methods=['GET', 'POST'])
@login_required
def editarExercicio(exercicio_id):
    # [back-06-contas-e-papeis] antes: Exercicio.query.get_or_404(exercicio_id). Exercício do catálogo padrão ou de
    # outra academia responde 404: não é editável por esta conta.
    exercicio = exercicios_proprios().filter_by(id=exercicio_id).first_or_404()
    form = ExercicioForm(obj=exercicio)

    if form.validate_on_submit():
        dados = {
            "nome": form.nome.data,
            "grupo_muscular": form.grupo_muscular.data,
            "descricao": form.descricao.data,
            "video_url": form.video_url.data,
            "ativo": form.ativo.data,
        }

        try:
            ExercicioService.editar_exercicio(exercicio_id,dados)
            flash('Exercicio atualizado com sucesso!')
            # [back-02-limpeza] antes: url_for('exercicios.listarPlanos'), endpoint que não existe.
            # Salvar a edição de um exercício dava BuildError (erro 500).
            return redirect(url_for('exercicios.listarExercicios'))
        except BusinessError as e:
            flash(str(e), "error")

    return render_template('exercicio_form.html', form=form, titulo=f'Editar Exercicio: {exercicio.nome}')

# Rota excluir
@exercicios_blueprint.route('/excluir/<int:exercicio_id>', methods=['POST'])
@login_required
def excluirExercicio(exercicio_id):
    try:
        ExercicioService.excluir_exercicio(exercicio_id)
        flash('Exercicio excluído com sucesso!', 'success')
    except BusinessError as e:
        flash(str(e), "error")
        
    return redirect(url_for('exercicios.listarExercicios'))


# ---------------------------------------------------------------------------
# [back-14-treinos] TELAS DE EXERCÍCIOS DO FRONT NOVO (templates/exercicios/).
# Os nomes das funções e os endereços são os do contrato do front: 'exercicios.lista',
# 'exercicios.detalhe', 'exercicios.novo' e 'exercicios.editar'.
# Antes (back-04), 'lista' era só uma ponte para a tela antiga (/exercicios/listar/); as outras
# três não existiam com estes nomes. As rotas ANTIGAS, lá em cima, continuam funcionando.
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
