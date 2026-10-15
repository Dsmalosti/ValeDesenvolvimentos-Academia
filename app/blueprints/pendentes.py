"""
Telas do front novo que AINDA não existem no backend.

[back-04-painel] Criado nesta branch. O menu e o painel do front novo chamam url_for() para
todas as seções do sistema. Se um endpoint não existe, o Flask dá BuildError e a página
inteira vira erro 500. Este arquivo cria esses endpoints, com os nomes e os endereços do
contrato do front, respondendo uma página "em construção".

É TEMPORÁRIO: cada linha de PENDENTES sai daqui na branch que criar a tela de verdade.
Quando a lista ficar vazia, este arquivo e o templates/em_construcao.html são apagados.

A página responde com status 200: é uma página válida, que só avisa que a tela ainda não
foi ligada. (Com 501 o navegador registraria um erro no console a cada clique no menu.)
Para saber o que falta, a lista é a PENDENTES abaixo.
"""
from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import PAPEL_INSTRUTOR


def tela_em_construcao(titulo):
    """Página "em construção" no layout novo. Usada aqui e por blueprints que já existem."""
    return render_template('em_construcao.html', titulo_tela=titulo)


# (blueprint, função, endereço, métodos, nome da tela)
PENDENTES = [
    # [back-12-config] 'config.index' saiu daqui: agora é rota de verdade em blueprints/config/routes.py.
    # [back-11-relatorios] 'relatorios.index' e 'relatorios.admin' saíram daqui: agora são rotas de verdade em
    # blueprints/relatorios/routes.py.
    # [back-16-mensagens] 'mensagens.index' saiu daqui: agora é rota de verdade em blueprints/mensagens/routes.py.
    # [back-10-frequencia] 'frequencia.index' saiu daqui: agora é rota de verdade em blueprints/frequencia/routes.py.
    # [back-15-avaliacoes] 'avaliacoes.agenda', 'avaliacoes.agendar' e 'avaliacoes.registrar' saíram daqui: agora são
    # rotas de verdade em blueprints/avaliacoes/routes.py.
    # [back-17-personal] 'agenda.index' saiu daqui: agora é rota de verdade em blueprints/agenda/routes.py.
    # ações que o painel envia por formulário (POST): avisam e voltam para o painel
    # [back-09-cobranca] 'cobrancas.diaria' e 'cobrancas.lembrete_lote' saíram daqui: agora são rotas de
    # verdade em blueprints/cobrancas/routes.py.
]


# [back-06-contas-e-papeis] Seções de dinheiro e de dono: o instrutor recebe 403 desde já, mesmo com a tela ainda
# "em construção". Assim, quando a tela de verdade entrar no lugar, a regra já está testada.
SO_DONO_E_RECEPCAO = {'relatorios', 'cobrancas'}


def _barra_instrutor(nome_bp):
    if nome_bp in SO_DONO_E_RECEPCAO and current_user.papel == PAPEL_INSTRUTOR:
        abort(403)


def _visao(nome_bp, nome_da_tela, metodos):
    """Cria a função que responde por uma linha de PENDENTES."""
    if metodos == ['POST']:
        @login_required
        def acao(**_):
            _barra_instrutor(nome_bp)
            # categoria 'info': é uma das quatro que o front conhece (success|error|warning|info)
            flash(f'{nome_da_tela}: esta função ainda não está disponível.', 'info')
            return redirect(url_for('painel.index'))
        return acao

    @login_required
    def pagina(**_):
        _barra_instrutor(nome_bp)
        return tela_em_construcao(nome_da_tela)
    return pagina


# Seções que já têm tela ANTIGA com outro nome: o endpoint do front leva para ela.
# (blueprint, função, endereço, endpoint antigo de destino)
# [back-14-treinos] a última ponte daqui ('treinos.biblioteca' -> tela antiga de fichas) virou tela de verdade,
# em blueprints/treinos/routes.py. A lista fica vazia, pronta para uma próxima.
PONTES = []


def _ponte(destino):
    @login_required
    def ir(**_):
        return redirect(url_for(destino))
    return ir


def blueprints_pendentes():
    """Um blueprint por seção, com os endpoints de PENDENTES e PONTES. Registrados no create_app()."""
    blueprints = {}
    for nome_bp, funcao, endereco, metodos, nome_da_tela in PENDENTES:
        bp = blueprints.setdefault(nome_bp, Blueprint(nome_bp, __name__ + '_' + nome_bp))
        bp.add_url_rule(endereco, funcao, _visao(nome_bp, nome_da_tela, metodos), methods=metodos)
    for nome_bp, funcao, endereco, destino in PONTES:
        bp = blueprints.setdefault(nome_bp, Blueprint(nome_bp, __name__ + '_' + nome_bp))
        bp.add_url_rule(endereco, funcao, _ponte(destino), methods=['GET'])
    return list(blueprints.values())
