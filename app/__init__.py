from flask import Flask
import logging
import os
import time
from pathlib import Path
from dotenv import load_dotenv

from config import config_map
from app.extensions import admin, database, protecao, security

# Carrega o .env
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path)


def _acertar_o_fuso():
    """
    [back-20-producao] O sistema decide "hoje" pelo relógio do servidor (vencimento, aniversário, agenda, fila do dia).
    Servidor de hospedagem costuma estar em UTC: sem isto, depois das 21h de Brasília o sistema já estaria no dia
    seguinte. Antes: usava o fuso que a máquina tivesse. Agora, no servidor (Linux): horário de Brasília, a não ser
    que a variável TZ diga outro.

    No Windows (o computador de quem desenvolve) NADA muda: vale o relógio do próprio computador. Ali a variável TZ
    não pode nem existir: o Windows não entende "America/Sao_Paulo" e o Python passa a marcar o horário de Londres
    (3 horas a mais). Por isso, no Windows, o app só avisa se encontrar a variável.
    """
    if not hasattr(time, 'tzset'):      # Windows
        if os.environ.get('TZ'):
            logging.getLogger(__name__).warning(
                'A variável TZ está definida neste Windows: o relógio do sistema pode estar 3 horas adiantado. '
                'Tire a linha TZ do arquivo .env (ela só serve no servidor).')
        return
    os.environ.setdefault('TZ', 'America/Sao_Paulo')
    time.tzset()


def create_app():
    _acertar_o_fuso()
    app = Flask(__name__)

    # Ambiente
    config_name = os.getenv("FLASK_CONFIG", "development")
    app.config.from_object(config_map[config_name])

    # Variáveis sensíveis
    # [back-05-repo-e-config] antes: os.getenv("DATABASE_URI"), enquanto o ProductionConfig lia
    # "DATABASE_URL". Com dois nomes, o app não subia numa hospedagem que só cria DATABASE_URL
    # (o padrão da maioria). Agora o nome oficial é DATABASE_URL. O nome antigo ainda é aceito,
    # com aviso no log, só para ninguém ficar com o ambiente quebrado de um dia para o outro;
    # sai de vez na branch de produção.
    database_uri = os.getenv("DATABASE_URL")
    # [back-20-producao] em produção só vale o nome oficial, DATABASE_URL. Antes: o nome antigo (DATABASE_URI) era
    # aceito em qualquer ambiente; continua aceito, com aviso, só no computador de quem desenvolve.
    if not database_uri and os.getenv("DATABASE_URI") and config_name != "production":
        database_uri = os.getenv("DATABASE_URI")
        logging.getLogger(__name__).warning(
            "A variável DATABASE_URI mudou de nome para DATABASE_URL. Renomeie no seu .env.")
    secret_key = os.getenv("SECRET_KEY")

    if not database_uri:
        raise RuntimeError("DATABASE_URL não encontrada no .env")
    if not secret_key:
        raise RuntimeError("SECRET_KEY não encontrada no .env")

    # [back-20-producao] várias hospedagens entregam o endereço do banco começando com "postgres://", que o
    # SQLAlchemy 2 não aceita mais. Antes: o app não subia com esse endereço. Agora ele é lido como "postgresql://".
    if database_uri.startswith("postgres://"):
        database_uri = "postgresql://" + database_uri[len("postgres://"):]

    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = secret_key

    # [back-20-producao] Na hospedagem o app fica atrás de um proxy (quem recebe o HTTPS e repassa). Sem avisar o
    # Flask, todo mundo parece vir do IP do proxy: o limite de tentativas do login bloquearia todos de uma vez.
    # PROXIES_NA_FRENTE diz quantos proxies há (1 na maioria das hospedagens). Sem a variável, nada muda: confiar
    # nesses cabeçalhos sem ter proxy deixaria qualquer um inventar o próprio IP.
    proxies = os.getenv("PROXIES_NA_FRENTE", "").strip()
    if proxies.isdigit() and int(proxies) > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=int(proxies), x_proto=int(proxies), x_host=int(proxies))

    # [back-20-producao] em produção os avisos e erros vão para a saída do processo, que é onde a hospedagem recolhe
    # os registros. Antes: sem configuração, só os erros apareciam, sem data nem origem.
    if config_name == "production":
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Extensões
    database.init_app(app)
    admin.init_app(app)
    security.init_app(app)
    protecao.init_app(app)      # [back-18-seguranca] limite de tentativas e cabeçalhos de segurança

    # Blueprints
    # [back-27-telas-antigas] saíram os blueprints só das telas antigas: main (início antigo), instrutores (login, painel e equipe antigos),
    # fichas (fichas antigas) e pagamentos (redirecionamentos das telas antigas de pagamento).
    from app.blueprints.alunos.routes import alunos_blueprint
    from app.blueprints.planos.routes import planos_blueprint
    from app.blueprints.exercicios.routes import exercicios_blueprint
    from app.blueprints.auth.routes import auth_blueprint  # [back-01-auth-login] login/sair da tela nova


    app.register_blueprint(alunos_blueprint)
    app.register_blueprint(planos_blueprint)
    app.register_blueprint(exercicios_blueprint)
    app.register_blueprint(auth_blueprint)  # [back-01-auth-login]

    # [back-04-painel] painel do front novo, e as seções que ainda não têm backend
    # (cada uma responde "em construção" até a tela de verdade entrar).
    from app.blueprints.painel.routes import painel_blueprint
    from app.blueprints.cobrancas.routes import cobrancas_blueprint  # [back-09-cobranca]
    from app.blueprints.frequencia.routes import frequencia_blueprint  # [back-10-frequencia]
    from app.blueprints.relatorios.routes import relatorios_blueprint  # [back-11-relatorios]
    from app.blueprints.config.routes import config_blueprint  # [back-12-config]
    from app.blueprints.treinos.routes import treinos_blueprint  # [back-14-treinos]
    from app.blueprints.avaliacoes.routes import avaliacoes_blueprint  # [back-15-avaliacoes]
    from app.blueprints.mensagens.routes import mensagens_blueprint  # [back-16-mensagens]
    from app.blueprints.agenda.routes import agenda_blueprint  # [back-17-personal]
    from app.blueprints.legal.routes import legal_blueprint  # [back-19-lgpd] termos de uso e política de privacidade
    from app.blueprints.saude import saude_blueprint  # [back-20-producao] /saude: a hospedagem pergunta se o app está de pé
    from app.blueprints.assinatura.routes import assinatura_blueprint  # [back-24-assinatura] teste grátis, mensalidade e bloqueio
    from app.blueprints.admin.routes import admin_blueprint  # [back-25-admin] painel de administração do Vale Tec
    from app.blueprints.pendentes import blueprints_pendentes
    app.register_blueprint(painel_blueprint)
    app.register_blueprint(cobrancas_blueprint)  # [back-09-cobranca]
    app.register_blueprint(frequencia_blueprint)  # [back-10-frequencia]
    app.register_blueprint(relatorios_blueprint)  # [back-11-relatorios]
    app.register_blueprint(config_blueprint)  # [back-12-config]
    app.register_blueprint(treinos_blueprint)  # [back-14-treinos]
    app.register_blueprint(avaliacoes_blueprint)  # [back-15-avaliacoes]
    app.register_blueprint(mensagens_blueprint)  # [back-16-mensagens]
    app.register_blueprint(agenda_blueprint)  # [back-17-personal]
    app.register_blueprint(legal_blueprint)  # [back-19-lgpd]
    app.register_blueprint(saude_blueprint)  # [back-20-producao]
    app.register_blueprint(assinatura_blueprint)  # [back-24-assinatura]
    app.register_blueprint(admin_blueprint)  # [back-25-admin]
    for blueprint_pendente in blueprints_pendentes():
        app.register_blueprint(blueprint_pendente)

    # [back-04-painel] `usuario` e `academia` em todo template, e páginas de erro do front novo.
    from app.helpers.contexto import registrar_contexto
    from app.helpers.erros import registrar_paginas_de_erro
    registrar_contexto(app)
    registrar_paginas_de_erro(app)

    # [back-06-contas-e-papeis] comando `flask criar-conta` (o cadastro aberto pela internet foi fechado)
    from app.cli import registrar_comandos
    registrar_comandos(app)

    # Models (necessário para migrations)
    from app import models

    return app
