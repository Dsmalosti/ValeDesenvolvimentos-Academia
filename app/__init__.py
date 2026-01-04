from flask import Flask
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
    database_uri = os.getenv("DATABASE_URI")
    secret_key = os.getenv("SECRET_KEY")

    if not database_uri:
        raise RuntimeError("DATABASE_URI não encontrada no .env")
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


    app.register_blueprint(main_blueprint)
    app.register_blueprint(alunos_blueprint)
    app.register_blueprint(instrutores_blueprint)
    app.register_blueprint(planos_blueprint)
    app.register_blueprint(exercicios_blueprint)
    app.register_blueprint(fichas_blueprint)

    # Models (necessário para migrations)
    from app import models

    return app
