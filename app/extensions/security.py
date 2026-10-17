from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
# [back-29-dependencias] antes: também importava e ligava o JWTManager (Flask-JWT-Extended). O sistema nunca usou
# token JWT (o login é por sessão, com o Flask-Login), e a dependência saiu do requirements.txt com o OK do Adauto.


bcrypt = Bcrypt()
csrf = CSRFProtect()

def init_app(app):
    bcrypt.init_app(app)
    csrf.init_app(app)
