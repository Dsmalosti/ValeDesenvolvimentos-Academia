from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from flask_jwt_extended import JWTManager


bcrypt = Bcrypt()
csrf = CSRFProtect()
jwt = JWTManager()

def init_app(app):
    bcrypt.init_app(app)
    csrf.init_app(app)
    jwt.init_app(app)