"""
Configuração dos testes automáticos (pytest).

Como rodar, na raiz do projeto:
    .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests -q

Os testes NUNCA usam o banco de verdade. Este arquivo define DATABASE_URL (e o nome antigo, DATABASE_URI) apontando para um
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
from datetime import date, datetime, timedelta

sys.dont_write_bytecode = True  # o repositório versiona .pyc; não gerar novos ao testar

_PASTA = tempfile.mkdtemp(prefix="vt-testes-")
os.environ["DATABASE_URL"] = os.environ["DATABASE_URI"] = "sqlite:///" + os.path.join(_PASTA, "testes.db").replace("\\", "/")
os.environ["SECRET_KEY"] = "chave-so-de-teste"
os.environ["FLASK_CONFIG"] = "testing"

import pytest  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions.database import db  # noqa: E402
from app.extensions.security import bcrypt  # noqa: E402
from app.models import (Aluno, AvaliacaoAgendada, AvaliacaoFisica, Cobranca, Conta, Custo, Exercicio, Ficha, Frequencia, Pagamento, Plano,  # noqa: E402
                        Sessao, Treino, User)

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


def criar_conta(nome="Academia Teste", modelo="academia"):
    """Cria uma conta (academia) vazia. Devolve o id."""
    return _salvar(Conta(nome=nome, modelo=modelo))


def criar_usuario(email, nome="Usuario", ativo=True, conta=None, papel="proprietario"):
    """
    Cria um usuário. Sem `conta`, cria também uma academia nova só para ele (é o dono).
    Com `conta` (um id), o usuário entra na equipe daquela academia, com o `papel` informado.
    Devolve o id do usuário.
    """
    if conta is None:
        conta = criar_conta(nome=f"Academia de {nome}")
    return _salvar(User(nome=nome, sobrenome="Teste", email=email, ativo=ativo, conta_id=conta, papel=papel,
                        senha=bcrypt.generate_password_hash(SENHA_TESTE).decode("utf-8")))


def conta_de(usuario_id):
    """Id da conta (academia) de um usuário."""
    with _APP.app_context():
        return db.session.get(User, usuario_id).conta_id


def logar(cliente, usuario_id):
    """Marca o cliente de teste como logado, sem passar pela tela de login."""
    # [back-18-seguranca] a sessão guarda "id|marca da senha" (User.get_id); com o id puro o sistema não reconhece mais
    with _APP.app_context():
        identificacao = db.session.get(User, usuario_id).get_id()
    with cliente.session_transaction() as sessao:
        sessao["_user_id"] = identificacao
        sessao["_fresh"] = True


def criar_plano(dono_id, nome="Mensal"):
    return _salvar(Plano(nome=nome, valor=100, duracao_dias=30, descricao="", ativo=True, instrutor_id=dono_id,
                         conta_id=conta_de(dono_id)))


def criar_aluno(dono_id, plano_id, nome, email, cpf, ativo=True, cadastrado_em=None, nascimento=date(1990, 1, 1), whatsapp=True):
    # [back-22-ajustes-de-produto] `whatsapp`: o aluno autorizou avisos pelo WhatsApp? Antes não havia o parâmetro e o campo ficava vazio, o que
    # bastava para entrar na fila de Mensagens. Agora só entra quem autorizou, então os alunos de teste nascem autorizados.
    aluno = Aluno(nome=nome, email=email, cpf=cpf, telefone="11999990000", ativo=ativo, aceita_whatsapp=whatsapp,
                  data_nascimento=nascimento, plano_id=plano_id, instrutor_id=dono_id, conta_id=conta_de(dono_id))
    if cadastrado_em:  # um `date`; sem isso o banco usa o momento atual
        aluno.data_cadastro = datetime(cadastrado_em.year, cadastrado_em.month, cadastrado_em.day)
    return _salvar(aluno)


def criar_pagamento(dono_id, aluno_id, valor, pago_em, vence_em, forma="pix"):
    """
    Um pagamento já recebido: cria a cobrança (paga, do plano atual do aluno, cobrindo de `pago_em`
    até `vence_em`) e o pagamento que a quitou, confirmado por `dono_id`. Devolve o id do pagamento.
    """
    with _APP.app_context():
        aluno = db.session.get(Aluno, aluno_id)
        cobranca = Cobranca(conta_id=aluno.conta_id, aluno_id=aluno_id, plano_id=aluno.plano_id, tipo="renovacao", valor=valor,
                            data_inicio=pago_em, data_vencimento=vence_em, status="paga", instrutor_id=dono_id)
        db.session.add(cobranca)
        db.session.flush()
        pagamento = Pagamento(conta_id=aluno.conta_id, cobranca_id=cobranca.id, forma=forma, valor_pago=valor,
                              data_pagamento=datetime(pago_em.year, pago_em.month, pago_em.day, 12, 0),
                              origem_confirmacao="manual", confirmado_por_instrutor_id=dono_id)
        db.session.add(pagamento)
        db.session.commit()
        return pagamento.id


def criar_cobranca_em_aberto(dono_id, aluno_id, valor, inicio, fim, tipo="matricula"):
    """Uma cobrança ainda não paga (o "cobrar depois"). Devolve o id da cobrança."""
    with _APP.app_context():
        aluno = db.session.get(Aluno, aluno_id)
        return _salvar(Cobranca(conta_id=aluno.conta_id, aluno_id=aluno_id, plano_id=aluno.plano_id, tipo=tipo, valor=valor,
                                data_inicio=inicio, data_vencimento=fim, status="pendente", instrutor_id=dono_id))


def criar_entrada(dono_id, aluno_id, quando, origem="recepcao"):
    """Uma entrada (check-in) do aluno em `quando` (um datetime). Devolve o id."""
    return _salvar(Frequencia(conta_id=conta_de(dono_id), aluno_id=aluno_id, data_hora_entrada=quando, origem=origem, instrutor_id=dono_id))


def criar_custo(dono_id, descricao, valor):
    """Um custo fixo mensal da academia de `dono_id`. Devolve o id."""
    return _salvar(Custo(conta_id=conta_de(dono_id), descricao=descricao, valor=valor))


def ligar_checkin(conta_id, ligado=True):
    """Liga ou desliga o serviço de check-in de uma conta (nos testes as contas nascem com ele desligado)."""
    with _APP.app_context():
        db.session.get(Conta, conta_id).checkin_ativo = ligado
        db.session.commit()


def semear_catalogo():
    """Grava o catálogo padrão de exercícios (os modelos de ficha dependem dele). Devolve quantos criou."""
    from app.services.treino_service import semear_catalogo_padrao
    with _APP.app_context():
        return semear_catalogo_padrao()


def criar_exercicio(nome="Supino", dono_id=None):
    """Sem `dono_id`, o exercício é do catálogo padrão (todo mundo usa, ninguém edita)."""
    return _salvar(Exercicio(nome=nome, grupo_muscular="peito", ativo=True,
                             conta_id=conta_de(dono_id) if dono_id else None))


def criar_ficha(aluno_id, nome="Ficha A"):
    return _salvar(Ficha(nome=nome, aluno_id=aluno_id, ativo=True))


def criar_treino(ficha_id, dia="segunda"):
    return _salvar(Treino(ficha_id=ficha_id, dia_semana=dia))


def criar_agendamento(dono_id, aluno_id, dia, hora="09:00", avaliador_id=None, status="confirmada", tipo="primeira"):
    """Um horário de avaliação física marcado para `dia` (um date). Devolve o id."""
    return _salvar(AvaliacaoAgendada(conta_id=conta_de(dono_id), aluno_id=aluno_id, data=dia, hora=hora, tipo=tipo, status=status,
                                     avaliador_id=avaliador_id or dono_id, cobranca="inclusa", criado_por_id=dono_id))


def criar_avaliacao(dono_id, aluno_id, dia, peso=70, altura=170, **medidas):
    """Uma avaliação física FEITA em `dia` (um date), com IMC e RCQ calculados como o sistema calcula. Devolve o id."""
    from app.services.avaliacao_service import calcular_imc, calcular_rcq
    return _salvar(AvaliacaoFisica(conta_id=conta_de(dono_id), aluno_id=aluno_id, data=dia, avaliador_id=dono_id, peso_kg=peso, altura_cm=altura,
                                   imc=calcular_imc(peso, altura), rcq=calcular_rcq(medidas.get("cintura_cm"), medidas.get("quadril_cm")), **medidas))


def criar_personal(email="paulo@teste.local", nome="Paulo"):
    """Um personal trainer: a conta (modelo 'personal') e o usuário dono dela. Devolve o id do usuário."""
    return criar_usuario(email, nome=nome, conta=criar_conta(nome=f"{nome} Rocha", modelo="personal"))


def criar_pacote(dono_id, nome="Pacote 8", sessoes=8, valor=960, ativo=True):
    """Um pacote de sessões (na conta de personal, o "plano"). Devolve o id."""
    return _salvar(Plano(nome=nome, valor=valor, duracao_dias=90, quantidade_sessoes=sessoes, descricao="", ativo=ativo,
                         instrutor_id=dono_id, conta_id=conta_de(dono_id)))


def criar_compra(dono_id, aluno_id, pacote_id, paga=True, quando=None):
    """A compra de um pacote pelo aluno: a cobrança (com as sessões) e, se `paga`, o pagamento. `quando` é um datetime. Devolve o id da cobrança."""
    with _APP.app_context():
        pacote = db.session.get(Plano, pacote_id)
        quando = quando or datetime.utcnow()
        cobranca = Cobranca(conta_id=conta_de(dono_id), aluno_id=aluno_id, plano_id=pacote_id, tipo="matricula", valor=pacote.valor,
                            data_inicio=quando.date(), data_vencimento=quando.date() + timedelta(days=90), status="paga" if paga else "pendente",
                            instrutor_id=dono_id, quantidade_sessoes=pacote.quantidade_sessoes, data_geracao=quando)
        db.session.add(cobranca)
        db.session.flush()
        if paga:
            db.session.add(Pagamento(conta_id=cobranca.conta_id, cobranca_id=cobranca.id, forma="pix", valor_pago=pacote.valor, data_pagamento=quando,
                                     origem_confirmacao="manual", confirmado_por_instrutor_id=dono_id))
        db.session.commit()
        return cobranca.id


def criar_sessao(dono_id, aluno_id, dia, hora="09:00", status="agendada", abateu=None, repete="unica", local="estudio", duracao=60):
    """Uma sessão na agenda do personal em `dia` (um date). Concluída abate do saldo, a não ser que `abateu=False`. Devolve o id."""
    concluida = status == "concluida"
    return _salvar(Sessao(conta_id=conta_de(dono_id), aluno_id=aluno_id, instrutor_id=dono_id, data=dia, hora=hora, duracao=duracao, local=local,
                          repete=repete, status=status, abateu=concluida if abateu is None else abateu,
                          concluida_em=datetime.utcnow() if concluida else None))


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
