import logging
import os

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config_map
from app.extensions import admin, database, security
from app.helpers import filters
from app.helpers.navegacao import url_segura


def create_app(config_name=None):
    app = Flask(__name__)

    # Ambiente
    config_name = config_name or os.getenv("FLASK_CONFIG", "development")
    if config_name not in config_map:
        raise RuntimeError(f"FLASK_CONFIG inválido: {config_name}")
    app.config.from_object(config_map[config_name])
    _validar_configuracao(app, config_name)

    if config_name == "production":
        # Necessário atrás de proxy (Render, Railway, Nginx) para HTTPS/IP corretos
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
        logging.basicConfig(level=logging.INFO)

    # Extensões
    database.init_app(app)
    admin.init_app(app)
    security.init_app(app)

    # Models (necessário para migrations)
    from app import models  # noqa: F401

    _registrar_blueprints(app)
    _registrar_erros(app)
    _registrar_cabecalhos_seguranca(app)
    filters.init_app(app)

    return app


def _validar_configuracao(app, config_name):
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URI não encontrada no .env")

    secret_key = app.config.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY não encontrada no .env")
    if config_name == "production" and len(secret_key) < 32:
        raise RuntimeError("Use uma SECRET_KEY com pelo menos 32 caracteres em produção")


def _registrar_blueprints(app):
    from app.routes import main_blueprint
    from app.blueprints.alunos.routes import alunos_blueprint
    from app.blueprints.instrutores.routes import instrutores_blueprint
    from app.blueprints.planos.routes import planos_blueprint
    from app.blueprints.exercicios.routes import exercicios_blueprint
    from app.blueprints.fichas.routes import fichas_blueprint

    app.register_blueprint(main_blueprint)
    app.register_blueprint(alunos_blueprint)
    app.register_blueprint(instrutores_blueprint)
    app.register_blueprint(planos_blueprint)
    app.register_blueprint(exercicios_blueprint)
    app.register_blueprint(fichas_blueprint)


def _registrar_erros(app):
    from app.extensions.database import db

    def pagina_erro(codigo, titulo, mensagem):
        return render_template(
            "errors/erro.html", codigo=codigo, titulo=titulo, mensagem=mensagem
        ), codigo

    @app.errorhandler(403)
    def acesso_negado(_erro):
        return pagina_erro(403, "Acesso negado", "Você não tem permissão para acessar esta página.")

    @app.errorhandler(404)
    def nao_encontrado(_erro):
        return pagina_erro(404, "Página não encontrada", "O endereço pode estar errado ou o registro foi removido.")

    @app.errorhandler(405)
    def metodo_nao_permitido(_erro):
        return pagina_erro(405, "Ação não permitida", "Esta ação não pode ser feita por este caminho.")

    @app.errorhandler(500)
    def erro_interno(_erro):
        db.session.rollback()
        return pagina_erro(500, "Algo deu errado", "Tivemos um problema inesperado. Tente novamente em instantes.")

    @app.errorhandler(CSRFError)
    def csrf_invalido(_erro):
        flash("Sua sessão expirou. Envie o formulário novamente.", "danger")
        destino = request.referrer
        if destino and destino.startswith(request.host_url):
            destino = "/" + destino[len(request.host_url):]
        return redirect(destino if url_segura(destino) else url_for("main.homepage"))


def _registrar_cabecalhos_seguranca(app):
    politica = "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data:",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
    ])

    @app.after_request
    def aplicar_cabecalhos(resposta):
        resposta.headers.setdefault("Content-Security-Policy", politica)
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        resposta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return resposta
