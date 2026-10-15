"""
[back-11-relatorios] Rotas do PAINEL ADMINISTRATIVO do front novo (templates/relatorios/admin.html).

Os nomes das funções e os endereços são os do contrato do front: 'relatorios.admin',
'relatorios.exportar', 'relatorios.custo_salvar' e 'relatorios.custo_excluir'. Antes desta
branch, 'relatorios.admin' e 'relatorios.index' eram telas "em construção" em pendentes.py.

Só dono e recepção: instrutor recebe 403 em qualquer rota daqui. As contas ficam em
services/relatorio_service.py.
"""
from flask import Blueprint, flash, make_response, redirect, render_template, request, url_for

from app.helpers.conta import DONO_E_RECEPCAO, exigir_papel_em
from app.services import relatorio_service as relatorios

relatorios_blueprint = Blueprint('relatorios', __name__, url_prefix='/relatorios')
exigir_papel_em(relatorios_blueprint, *DONO_E_RECEPCAO)   # toda rota daqui, inclusive as futuras


@relatorios_blueprint.route('')
def index():
    # A tela "Relatórios" foi incorporada ao painel administrativo no próprio front (o botão dela
    # saiu do menu). O endereço continua existindo e leva para lá, com o mesmo período e filtro.
    return redirect(url_for('relatorios.admin', **{k: v for k, v in request.args.items() if k in ('periodo', 'forma', 'situacao')}))


@relatorios_blueprint.route('/painel')
def admin():
    return render_template('relatorios/admin.html', **relatorios.contexto_do_painel(request.args))


@relatorios_blueprint.route('/exportar')
def exportar():
    if request.args.get('formato', 'csv') != 'csv':
        # Excel e PDF pedem bibliotecas novas; ficaram para depois do primeiro cliente (roadmap).
        flash('Por enquanto o fechamento sai em CSV, que o Excel abre. Excel e PDF ainda não estão disponíveis.', 'info')
        return redirect(url_for('relatorios.admin'))
    texto, nome = relatorios.exportar_csv(request.args)
    resposta = make_response(texto)
    resposta.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resposta.headers['Content-Disposition'] = f'attachment; filename={nome}'
    return resposta


@relatorios_blueprint.route('/custos', methods=['POST'])
def custo_salvar():
    try:
        relatorios.salvar_custo(request.form.get('id'), request.form.get('descricao'), request.form.get('valor'))
        flash('Custo salvo. O ponto de equilíbrio foi recalculado.', 'success')
    except relatorios.CustoInvalido as erro:
        flash(str(erro), 'error')
    return redirect(url_for('relatorios.admin') + '#custos')


@relatorios_blueprint.route('/custos/<int:id>/excluir', methods=['POST'])
def custo_excluir(id):
    if relatorios.excluir_custo(id):
        flash('Custo removido.', 'success')
    else:
        flash('Custo não encontrado.', 'error')    # inclui custo de outra academia: como se não existisse
    return redirect(url_for('relatorios.admin') + '#custos')
