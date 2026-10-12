"""
[back-15-avaliacoes] Rotas da AVALIAÇÃO FÍSICA do front novo (templates/avaliacoes/).

Os nomes das funções e os endereços são os do contrato do front: 'avaliacoes.agenda',
'avaliacoes.agendar', 'avaliacoes.aluno', 'avaliacoes.registrar' e 'avaliacoes.resultado'.
Antes desta branch, 'agenda', 'agendar' e 'registrar' eram telas "em construção"
(blueprints/pendentes.py) e as outras duas não existiam.

Quem pode o quê:
  - AGENDA e AGENDAR: dono, recepção e instrutor.
  - REGISTRAR, HISTÓRICO e RESULTADO (medidas, anamnese: dados de saúde): só dono e instrutor.
    A recepção que tocar num desses botões recebe um aviso e vai para a agenda; se tentar
    ENVIAR o formulário de avaliação, recebe 403.

As regras ficam em services/avaliacao_service.py.
"""
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.helpers.conta import da_conta, exigir_login_em
from app.models import Aluno
from app.services import avaliacao_service as avaliacoes
from app.services import treino_service

avaliacoes_blueprint = Blueprint('avaliacoes', __name__)
exigir_login_em(avaliacoes_blueprint)   # toda rota daqui exige login, inclusive as futuras


def _aluno(id):
    """O aluno, se for da conta de quem está logado; senão 404."""
    return da_conta(Aluno).filter_by(id=id).first_or_404()


def so_quem_avalia(funcao):
    """
    Dado de saúde: só dono e instrutor. Para os outros papéis: abrir a tela (GET) avisa e leva à
    agenda; enviar dado (POST) responde 403.
    """
    @wraps(funcao)
    def conferida(*args, **kwargs):
        if not avaliacoes.pode_avaliar():
            if request.method != 'GET':
                abort(403)
            flash('As medidas da avaliação são dados de saúde: só o dono e os instrutores abrem. Você pode agendar.', 'info')
            return redirect(url_for('avaliacoes.agenda'))
        return funcao(*args, **kwargs)
    return conferida


@avaliacoes_blueprint.route('/avaliacoes')
def agenda():
    return render_template('avaliacoes/agenda.html', **avaliacoes.contexto_da_agenda())


@avaliacoes_blueprint.route('/avaliacoes/agendar', methods=['GET', 'POST'])
def agendar():
    aluno_id = request.values.get('aluno_id', type=int) or request.args.get('aluno', type=int)
    if not aluno_id:
        if request.method == 'POST':
            abort(400)
        q = (request.args.get('q') or '').strip()
        return render_template('avaliacoes/agendar.html', aluno=None, achados=treino_service.alunos_para_atribuir(q, limite=6), q=q, erros={}, f={})

    aluno = _aluno(aluno_id)
    remarcar = avaliacoes.agendamento_em_aberto(request.values.get('remarcar', type=int), aluno)
    if request.method == 'POST':
        try:
            marcada = avaliacoes.agendar(aluno, request.form)
        except avaliacoes.AvaliacaoInvalida as erro:
            flash(str(erro), 'error')
            if not erro.erros:      # aluno inativo: não há o que corrigir no formulário
                return redirect(url_for('avaliacoes.agendar'))
            return render_template('avaliacoes/agendar.html', **avaliacoes.contexto_do_agendamento(aluno, erro.erros, request.form, remarcar))
        primeiro_nome = (aluno.nome or 'aluno').split()[0]
        flash(f"Avaliação de {primeiro_nome} agendada para {marcada.data.strftime('%d/%m/%Y')} às {marcada.hora}.", 'success')
        if marcada.cobranca == 'avulsa':
            flash('Avaliação avulsa: registre o recebimento pela diária avulsa do painel.', 'info')
        return redirect(url_for('avaliacoes.agenda'))
    if not aluno.ativo:
        flash('Este aluno está inativo. Reative o cadastro antes de agendar.', 'warning')
        return redirect(url_for('avaliacoes.agendar'))
    return render_template('avaliacoes/agendar.html', **avaliacoes.contexto_do_agendamento(aluno, remarcar=remarcar))


@avaliacoes_blueprint.route('/alunos/<int:id>/avaliacoes')
@so_quem_avalia
def aluno(id):
    return render_template('avaliacoes/aluno.html', **avaliacoes.contexto_do_historico(_aluno(id)))


@avaliacoes_blueprint.route('/alunos/<int:id>/avaliacoes/nova', methods=['GET', 'POST'])
@so_quem_avalia
def registrar(id):
    aluno = _aluno(id)
    if request.method == 'POST':
        try:
            feita = avaliacoes.registrar(aluno, request.form)
        except avaliacoes.AvaliacaoInvalida as erro:
            flash(str(erro), 'error')
            return render_template('avaliacoes/registrar.html', **avaliacoes.contexto_do_registro(aluno, request.form, request.form.get('ag', type=int)))
        return redirect(url_for('avaliacoes.resultado', id=feita.id))
    return render_template('avaliacoes/registrar.html', **avaliacoes.contexto_do_registro(aluno, ag=request.args.get('ag', type=int)))


@avaliacoes_blueprint.route('/avaliacoes/<int:id>')
@so_quem_avalia
def resultado(id):
    feita = avaliacoes.avaliacao_da_conta(id) or abort(404)
    return render_template('avaliacoes/resultado.html', **avaliacoes.contexto_do_resultado(feita))
