from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from dotenv import load_dotenv
from pathlib import Path
import os

# Carrega o .env
dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path)

# Inicializa as extensões (sem app ainda)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)

    # Pega as variáveis
    database_uri = os.getenv('DATABASE_URI')
    secret_key = os.getenv('SECRET_KEY')

    if not database_uri:
        raise RuntimeError("DATABASE_URI não encontrada no .env")
    if not secret_key:
        raise RuntimeError("SECRET_KEY não encontrada no .env")

    # Configurações do Flask
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = secret_key

    # Inicializa extensões
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'login'

    # Importa e registra os blueprints aqui dentro
    from app.alunos.routes import alunos_blueprint
    app.register_blueprint(alunos_blueprint)

    # Outras rotas
    from app.routes import main_blueprint
    app.register_blueprint(main_blueprint)

    # Importa modelos
    from app.models import Aluno

    return app
