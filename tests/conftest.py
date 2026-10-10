"""
Configuração dos testes automáticos (pytest).

Como rodar, na raiz do projeto:
    .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests -q

Os testes NUNCA usam o banco de verdade. Este arquivo define DATABASE_URI apontando para um
SQLite descartável ANTES de importar o app; o load_dotenv do projeto não sobrescreve variável
que já existe, então o banco do .env fica intocado. Cada teste começa com as tabelas vazias.

As funções criar_* devolvem o ID do registro (um número), não o objeto. Motivo: cada uma abre
e fecha o seu próprio contexto do Flask. Se o contexto ficasse aberto o teste inteiro, o Flask
reaproveitaria entre as requisições coisas que são de UMA requisição só (o usuário logado e o
token CSRF ficam guardados no `g`), e um teste com duas contas daria resultado falso.
"""
import os
import sys
import tempfile
import re
from datetime import date, datetime

sys.dont_write_bytecode = True  # o repositório versiona .pyc; não gerar novos ao testar

_PASTA = tempfile.mkdtemp(prefix="vt-testes-")
os.environ["DATABASE_URI"] = "sqlite:///" + os.path.join(_PASTA, "testes.db").replace("\\", "/")
os.environ["SECRET_KEY"] = "chave-so-de-teste"
os.environ["FLASK_CONFIG"] = "testing"

import pytest  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions.database import db  # noqa: E402
from app.extensions.security import bcrypt  # noqa: E402
from app.models import Aluno, Exercicio, Ficha, Pagamento, Plano, Treino, User  # noqa: E402

SENHA_TESTE = "Senha-de-teste-123"
_APP = None  # app do teste em andamento; as funções criar_* abrem o contexto a partir dele


@pytest.fixture()
def app():
    global _APP
    app = create_app()
    # trava de segurança: se por algum motivo o banco não for o descartável, nenhum teste roda
    assert "vt-testes-" in app.config["SQLALCHEMY_DATABASE_URI"], "os testes só rodam em banco descartável"
    # CSRF desligado aqui para os testes postarem direto; o CSRF em si é testado em test_login.py
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.drop_all()
        db.create_all()
    _APP = app
    yield app
    _APP = None


@pytest.fixture()
def cliente(app):
    return app.test_client()


def _salvar(objeto):
    """Grava o objeto e devolve o id dele."""
    with _APP.app_context():
        db.session.add(objeto)
        db.session.commit()
        return objeto.id


def criar_usuario(email, nome="Usuario", ativo=True):
    """Cria um usuário (hoje cada usuário é uma academia). Devolve o id."""
    return _salvar(User(nome=nome, sobrenome="Teste", email=email, ativo=ativo,
                        senha=bcrypt.generate_password_hash(SENHA_TESTE).decode("utf-8")))


def logar(cliente, usuario_id):
    """Marca o cliente de teste como logado, sem passar pela tela de login."""
    with cliente.session_transaction() as sessao:
        sessao["_user_id"] = str(usuario_id)
        sessao["_fresh"] = True


def criar_plano(dono_id, nome="Mensal"):
    return _salvar(Plano(nome=nome, valor=100, duracao_dias=30, descricao="", ativo=True, instrutor_id=dono_id))


def criar_aluno(dono_id, plano_id, nome, email, cpf, ativo=True, cadastrado_em=None, nascimento=date(1990, 1, 1)):
    aluno = Aluno(nome=nome, email=email, cpf=cpf, telefone="11999990000", ativo=ativo,
                  data_nascimento=nascimento, plano_id=plano_id, instrutor_id=dono_id)
    if cadastrado_em:  # um `date`; sem isso o banco usa o momento atual
        aluno.data_cadastro = datetime(cadastrado_em.year, cadastrado_em.month, cadastrado_em.day)
    return _salvar(aluno)


def criar_pagamento(dono_id, aluno_id, valor, pago_em, vence_em):
    return _salvar(Pagamento(aluno_id=aluno_id, instrutor_id=dono_id, valor=valor, forma_pagamento="pix",
                             data_pagamento=pago_em, data_vencimento=vence_em))


def criar_exercicio(nome="Supino"):
    return _salvar(Exercicio(nome=nome, grupo_muscular="peito", ativo=True))


def criar_ficha(aluno_id, nome="Ficha A"):
    return _salvar(Ficha(nome=nome, aluno_id=aluno_id, ativo=True))


def criar_treino(ficha_id, dia="segunda"):
    return _salvar(Treino(ficha_id=ficha_id, dia_semana=dia))


def contar(modelo, **filtros):
    """Quantos registros existem no banco com esses filtros. Ex.: contar(Aluno, nome='Ana')."""
    with _APP.app_context():
        return modelo.query.filter_by(**filtros).count()


def campo(modelo, registro_id, nome_do_campo):
    """Valor atual de um campo no banco. Ex.: campo(Aluno, 3, 'nome'). None se o registro sumiu."""
    with _APP.app_context():
        registro = db.session.get(modelo, registro_id)
        return getattr(registro, nome_do_campo) if registro else None


def numero_do_card(html, rotulo):
    """Lê do painel novo o valor do card de indicador que tem esse rótulo. Ex.: numero_do_card(html, 'Alunos ativos')."""
    achado = re.search(r'kpi__val[^>]*>\s*([^<]*?)\s*</div>\s*<div class="kpi__lbl">\s*' + re.escape(rotulo), html)
    assert achado, f'não achei o card "{rotulo}" no painel'
    return achado.group(1)
