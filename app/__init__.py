from flask import Flask
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from config import config_map
from app.extensions import admin, database, security

# Carrega o .env
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path)


def create_app():
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
    if not database_uri and os.getenv("DATABASE_URI"):
        database_uri = os.getenv("DATABASE_URI")
        logging.getLogger(__name__).warning(
            "A variável DATABASE_URI mudou de nome para DATABASE_URL. Renomeie no seu .env.")
    secret_key = os.getenv("SECRET_KEY")

    if not database_uri:
        raise RuntimeError("DATABASE_URL não encontrada no .env")
    if not secret_key:
        raise RuntimeError("SECRET_KEY não encontrada no .env")

    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = secret_key

    # Extensões
    database.init_app(app)
    admin.init_app(app)
    security.init_app(app)

    # Blueprints
    from app.routes import main_blueprint
    from app.blueprints.alunos.routes import alunos_blueprint
    from app.blueprints.instrutores.routes import instrutores_blueprint
    from app.blueprints.planos.routes import planos_blueprint
    from app.blueprints.exercicios.routes import exercicios_blueprint
    from app.blueprints.fichas.routes import fichas_blueprint
    from app.blueprints.pagamentos.routes import pagamentos_blueprint
    from app.blueprints.auth.routes import auth_blueprint  # [back-01-auth-login] login/sair da tela nova


    app.register_blueprint(main_blueprint)
    app.register_blueprint(alunos_blueprint)
    app.register_blueprint(instrutores_blueprint)
    app.register_blueprint(planos_blueprint)
    app.register_blueprint(exercicios_blueprint)
    app.register_blueprint(fichas_blueprint)
    app.register_blueprint(pagamentos_blueprint)
    app.register_blueprint(auth_blueprint)  # [back-01-auth-login]

    # [back-04-painel] painel do front novo, e as seções que ainda não têm backend
    # (cada uma responde "em construção" até a tela de verdade entrar).
    from app.blueprints.painel.routes import painel_blueprint
    from app.blueprints.pendentes import blueprints_pendentes
    app.register_blueprint(painel_blueprint)
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
