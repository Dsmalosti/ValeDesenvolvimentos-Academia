"""
[back-17-personal] Rotas da AGENDA DE SESSÕES do front novo (templates/agenda/). Só na conta de personal trainer.

Os nomes das funções e os endereços são os do contrato do front: 'agenda.index', 'agenda.detalhe',
'agenda.nova', 'agenda.concluir' e 'agenda.cancelar'. Antes desta branch, 'agenda.index' era uma tela
"em construção" (blueprints/pendentes.py) e as outras não existiam.

Conta de academia que abrir qualquer endereço daqui recebe um aviso e volta ao painel.
As regras ficam em services/agenda_service.py.
"""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.helpers.conta import da_conta, exigir_login_em
from app.models import Aluno
from app.services import agenda_service as agenda
from app.services import pacote_service

agenda_blueprint = Blueprint('agenda', __name__, url_prefix='/agenda')
exigir_login_em(agenda_blueprint)   # toda rota daqui exige login, inclusive as futuras


@agenda_blueprint.before_request
def so_personal():
    """A agenda de sessões é da conta de personal. (O login já foi conferido pela trava acima.)"""
    from flask_login import current_user
    if current_user.is_authenticated and not pacote_service.e_personal():
        if request.method != 'GET':
            abort(404)
        flash('A agenda de sessões existe só na conta de personal trainer.', 'info')
        return redirect(url_for('painel.index'))
    return None


def _sessao(id):
    return agenda.sessao_da_conta(id) or abort(404)


@agenda_blueprint.route('')
def index():
    return render_template('agenda/index.html', **agenda.contexto_da_agenda())


@agenda_blueprint.route('/<int:id>')
def detalhe(id):
    sessao = agenda.para_a_tela(_sessao(id))
    return render_template('agenda/detalhe.html', s=sessao, telefone=agenda.telefone_do(sessao))


@agenda_blueprint.route('/nova', methods=['GET', 'POST'])
def nova():
    aluno_id = request.values.get('aluno_id', type=int) or request.args.get('aluno', type=int)
    if not aluno_id:
        if request.method == 'POST':
            abort(400)
        q = (request.args.get('q') or '').strip()
        return render_template('agenda/nova.html', aluno=None, achados=agenda.alunos_para_marcar(q), q=q)

    aluno = da_conta(Aluno).filter_by(id=aluno_id).first_or_404()
    remarcar = agenda.sessao_para_remarcar(request.values.get('remarcar', type=int), aluno)
    if request.method == 'POST':
        try:
            sessao, remarcou = agenda.marcar(aluno, request.form)
        except agenda.SessaoInvalida as erro:
            flash(str(erro), 'error')
            if not erro.erros:      # aluno inativo: não há o que corrigir no formulário
                return redirect(url_for('agenda.nova'))
            return render_template('agenda/nova.html', **agenda.contexto_do_formulario(aluno, erro.erros, request.form, remarcar))
        primeiro_nome = (aluno.nome or 'aluno').split()[0]
        quando = f"{sessao.data.strftime('%d/%m')} às {sessao.hora}"
        if remarcou:
            flash(f'Sessão de {primeiro_nome} remarcada para {quando}.', 'success')
        else:
            flash(f'Sessão de {primeiro_nome} marcada para {quando}' + (' (toda semana).' if sessao.repete == 'semanal' else '.'), 'success')
        if request.form.get('acao') == 'renovar':
            return redirect(url_for('alunos.renovar', id=aluno.id))
        return redirect(url_for('agenda.index'))
    if not aluno.ativo:
        flash('Este aluno está inativo. Reative o cadastro antes de marcar sessão.', 'warning')
        return redirect(url_for('agenda.nova'))
    return render_template('agenda/nova.html', **agenda.contexto_do_formulario(aluno, remarcar=remarcar))


@agenda_blueprint.route('/<int:id>/concluir', methods=['POST'])
def concluir(id):
    sessao = _sessao(id)
    try:
        pacote, ja_estava = agenda.concluir(sessao)
    except agenda.SessaoInvalida as erro:
        flash(str(erro), 'error')
        return redirect(url_for('agenda.detalhe', id=id))
    if ja_estava:
        flash('Essa sessão já estava fechada.', 'info')
        return redirect(url_for('agenda.detalhe', id=id))
    primeiro_nome = (sessao.aluno.nome or 'aluno').split()[0]
    if not sessao.abateu:
        flash(f'Presença marcada. {primeiro_nome} estava sem saldo: esta sessão ficou fora do pacote. Hora de renovar.', 'warning')
    else:
        acabando = pacote['saldo'] <= 1
        flash(f"Presença marcada. {primeiro_nome}: {pacote_service.saldo_txt(pacote['saldo'])} no {pacote['nome']}."
              + (' Hora de renovar o pacote.' if acabando else ''), 'warning' if acabando else 'success')
    return redirect(url_for('agenda.index'))


@agenda_blueprint.route('/<int:id>/cancelar', methods=['POST'])
def cancelar(id):
    sessao = _sessao(id)
    try:
        agenda.cancelar(sessao)
    except agenda.SessaoInvalida as erro:
        flash(str(erro), 'error')
        return redirect(url_for('agenda.detalhe', id=id))
    flash(f"Sessão de {(sessao.aluno.nome or 'aluno').split()[0]} cancelada. O saldo do pacote não muda.", 'success')
    return redirect(url_for('agenda.index'))
