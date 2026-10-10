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
    ('config',     'index',          '/configuracoes',                         ['GET'],  'Configurações'),
    ('relatorios', 'index',          '/relatorios',                            ['GET'],  'Relatórios'),
    ('relatorios', 'admin',          '/relatorios/painel',                     ['GET'],  'Administrativo'),
    ('mensagens',  'index',          '/mensagens',                             ['GET'],  'Mensagens'),
    ('frequencia', 'index',          '/frequencia',                            ['GET'],  'Frequência'),
    ('avaliacoes', 'agenda',         '/avaliacoes',                            ['GET'],  'Avaliações físicas'),
    ('avaliacoes', 'agendar',        '/avaliacoes/agendar',                    ['GET'],  'Agendar avaliação'),
    ('avaliacoes', 'registrar',      '/alunos/<int:id>/avaliacoes/nova',       ['GET'],  'Registrar avaliação'),
    ('agenda',     'index',          '/agenda',                                ['GET'],  'Agenda'),
    # ações que o painel envia por formulário (POST): avisam e voltam para o painel
    ('cobrancas',  'diaria',         '/cobrancas/diaria',                      ['POST'], 'Diária avulsa'),
    ('cobrancas',  'lembrete_lote',  '/cobrancas/lembrete',                    ['POST'], 'Cobrança pelo WhatsApp'),
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
PONTES = [
    ('treinos', 'biblioteca', '/treinos', 'fichas.listarFichas'),
]


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
