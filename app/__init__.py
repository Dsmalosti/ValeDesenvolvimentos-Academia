from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from flask_login import LoginManager

from pathlib import Path
import os

# Carrega o .env
dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path)

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
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
bcrypt = Bcrypt(app)

# Chama a rota inicial
from app.routes import homepage

from app.models import Aluno
