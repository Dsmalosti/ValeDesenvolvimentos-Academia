"""
[back-10-frequencia] Rotas da FREQUÊNCIA do front novo (templates/frequencia/).

Os nomes das funções e os endereços são os do contrato do front: 'frequencia.index',
'frequencia.checkin' e 'frequencia.exportar'. Antes desta branch, 'frequencia.index' era uma
tela "em construção" em blueprints/pendentes.py.

As regras ficam em services/frequencia_service.py. O check-in é um serviço que a conta liga ou
desliga (coluna contas.checkin_ativo): desligado, as rotas daqui avisam e voltam ao painel.
"""
from datetime import date
from functools import wraps

from flask import Blueprint, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user

from app.helpers.conta import DONO_E_RECEPCAO, da_conta, exigir_login_em, papel_requerido
from app.models import Aluno
from app.services import cobranca_service
from app.services import frequencia_service as frequencia
from app.services.situacao_service import linha_do_aluno

frequencia_blueprint = Blueprint('frequencia', __name__, url_prefix='/frequencia')
exigir_login_em(frequencia_blueprint)   # toda rota daqui exige login, inclusive as futuras


def com_checkin_ligado(funcao):
    """Só entra se a conta tem o serviço de check-in ligado; senão avisa e volta para o painel."""
    @wraps(funcao)
    def conferida(*args, **kwargs):
        if not current_user.conta.checkin_ativo:
            flash('O serviço de check-in está desligado nas configurações.', 'warning')
            return redirect(url_for('painel.index'))
        return funcao(*args, **kwargs)
    return conferida


@frequencia_blueprint.route('')
@com_checkin_ligado
def index():
    q = (request.args.get('q') or '').strip()
    if request.args.get('partial'):
        # busca ao vivo: o app.js pede só o pedaço de HTML com as sugestões
        return render_template('frequencia/_sugestoes.html', sugestoes=frequencia.sugestoes(q), q=q)
    return render_template('frequencia/index.html', **frequencia.contexto_da_tela(q))


@frequencia_blueprint.route('/checkin', methods=['POST'])
@com_checkin_ligado
def checkin():
    # Registrar entrada é o trabalho do dia a dia: recepção, dono e instrutor podem.
    aluno_id = request.form.get('aluno_id', type=int)
    aluno = da_conta(Aluno).filter_by(id=aluno_id).first() if aluno_id else None
    if aluno is None:
        flash('Aluno não encontrado.', 'error')    # inclui aluno de outra academia: como se não existisse
        return redirect(url_for('frequencia.index'))
    try:
        entrada, nova = frequencia.registrar(aluno, request.form.get('origem'))
    except frequencia.EntradaRecusada as recusa:
        flash(str(recusa), 'error')
        return redirect(url_for('frequencia.index'))
    hora = entrada.data_hora_entrada.strftime('%Hh%M')
    if not nova:
        flash(f'{aluno.nome} já tinha entrada registrada às {hora}.', 'info')
    elif _esta_pendente(aluno):
        # a entrada NÃO é barrada por mensalidade atrasada: quem decide bloquear é a recepção (botão "Bloquear")
        flash(f'Entrada de {aluno.nome} registrada. Mensalidade pendente: vale avisar na saída.', 'warning')
    else:
        flash(f'Entrada de {aluno.nome} registrada.', 'success')
    return redirect(url_for('frequencia.index'))


def _esta_pendente(aluno):
    """O aluno está com mensalidade em atraso? Usa a mesma regra do painel e da lista de alunos."""
    linha = linha_do_aluno(aluno, cobranca_service.vencimento_do(aluno), date.today(), cobranca_service.em_aberto_do(aluno))
    return linha['status'] == 'pendente'


@frequencia_blueprint.route('/exportar')
@com_checkin_ligado
@papel_requerido(*DONO_E_RECEPCAO)   # planilha com nomes e situação de pagamento: instrutor não exporta
def exportar():
    resposta = make_response(frequencia.exportar_csv())
    resposta.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resposta.headers['Content-Disposition'] = 'attachment; filename=checkins-hoje.csv'
    return resposta
