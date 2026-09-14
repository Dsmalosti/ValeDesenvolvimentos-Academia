from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect


bcrypt = Bcrypt()
csrf = CSRFProtect()

def init_app(app):
    bcrypt.init_app(app)
    csrf.init_app(app)
