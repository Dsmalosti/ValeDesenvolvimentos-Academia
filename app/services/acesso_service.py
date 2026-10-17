"""
Quem entra no sistema e como: criar conta, convite da equipe e troca de senha.

[back-13-equipe] Criado nesta branch. As rotas ficam em blueprints/auth/routes.py (telas
públicas) e em blueprints/config/routes.py (aba Equipe das configurações).

Como cada pessoa ganha acesso (docs do projeto, "Acesso e mensagens"):
  - o DONO cria a própria conta em /criar-conta;
  - RECEPÇÃO e INSTRUTOR entram por convite: o dono informa o e-mail e o papel, o sistema gera
    um link que vale 7 dias e só pode ser usado uma vez, e a pessoa cria a própria senha;
  - quem esqueceu a senha recebe um link que vale 1 hora, também de uso único.

Sobre os links (convite e troca de senha): o banco guarda só o HASH do código do link. Se o
banco vazar, os links não vazam junto. Por isso o link completo só existe no momento em que é
criado: ele vai por e-mail e, no convite, fica disponível para o dono copiar.
"""
import hashlib
import re
import secrets
from datetime import datetime, timedelta

from flask import url_for
from flask_login import current_user
from sqlalchemy import func

from app.extensions.database import db
from app.extensions.security import bcrypt
from app.helpers.conta import da_conta
from app.helpers.email import enviar_email
from app.models import PAPEL_INSTRUTOR, PAPEL_PROPRIETARIO, PAPEL_RECEPCAO, Conta, Convite, RedefinicaoSenha, User

VALIDADE_DO_CONVITE = timedelta(days=7)
VALIDADE_DA_TROCA_DE_SENHA = timedelta(hours=1)
SENHA_MINIMA = 8
SENHA_MAXIMA = 72                 # o bcrypt ignora o que passa de 72 bytes: melhor recusar do que cortar calado
PAPEIS_DE_CONVITE = {PAPEL_RECEPCAO: 'Recepção', PAPEL_INSTRUTOR: 'Instrutor'}
MAX_CONVITES_ABERTOS = 20         # por conta: evita usar o sistema para disparar e-mail em massa
_EMAIL = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')


class AcessoInvalido(Exception):
    """O pedido não pode ser atendido. A mensagem é mostrada ao usuário."""


def _hash(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _email(texto):
    email = (texto or '').strip().lower()
    return email if (len(email) <= 120 and _EMAIL.fullmatch(email)) else None


def _usuario_do_email(email):
    return User.query.filter(func.lower(User.email) == email).first()


def erro_da_senha(senha):
    """A mensagem de erro para esta senha, ou None se ela serve."""
    if len(senha or '') < SENHA_MINIMA:
        return f'A senha precisa de pelo menos {SENHA_MINIMA} caracteres.'
    if len(senha.encode('utf-8')) > SENHA_MAXIMA:
        return f'A senha pode ter no máximo {SENHA_MAXIMA} caracteres.'
    return None


def _senha_guardada(senha):
    return bcrypt.generate_password_hash(senha).decode('utf-8')


# ------------------------------------------------------------------ criar conta (o dono)
def validar_conta_nova(formulario):
    """Confere o formulário de /criar-conta. Devolve (valores, erros {campo: mensagem})."""
    valores = {'tipo': 'personal' if formulario.get('tipo') == 'personal' else 'academia',
               'nome': ' '.join((formulario.get('nome') or '').split())[:100],
               'email': (formulario.get('email') or '').strip().lower()}
    erros = {}
    if not valores['nome']:
        erros['nome'] = 'Diga seu nome.'
    if not _email(valores['email']):
        erros['email'] = 'Confira o e-mail (ex.: voce@gmail.com).'
    elif _usuario_do_email(valores['email']):
        # não diz mais do que isto: só que o e-mail já tem conta
        erros['email'] = 'Esse e-mail já tem conta. Entre ou recupere a senha.'
    senha = formulario.get('senha') or ''
    if erro_da_senha(senha):
        erros['senha'] = erro_da_senha(senha)
    return valores, erros


def criar_conta(valores, senha):
    """Cria a conta (academia ou personal) e o usuário dono dela. Devolve o usuário."""
    partes = valores['nome'].split()
    academia = valores['tipo'] == 'academia'
    # O nome da academia é pedido depois, em Configurações (cadastro com poucos campos).
    conta = Conta(nome=(f'Academia de {partes[0]}' if academia else valores['nome'])[:120], modelo=valores['tipo'], checkin_ativo=academia)
    # [back-28-precos-e-promocao] se ainda há vaga, a conta nova ganha o desconto da promoção de lançamento (antes: sempre preço cheio)
    from app.services import assinatura_service
    assinatura_service.entrar_na_promocao(conta)
    db.session.add(conta)
    db.session.flush()
    # [back-19-lgpd] a tela diz "Ao criar a conta você aceita os termos de uso e a política de privacidade": fica gravado
    # qual versão dos textos estava no ar e quando. Antes não ficava registro nenhum do aceite.
    from app.services import legal_service
    usuario = User(nome=partes[0], sobrenome=' '.join(partes[1:]) or None, email=valores['email'], conta_id=conta.id,
                   papel=PAPEL_PROPRIETARIO, ativo=True, senha=_senha_guardada(senha),
                   termos_versao=legal_service.VERSAO, termos_aceitos_em=datetime.now())
    db.session.add(usuario)
    db.session.commit()
    return usuario


# ------------------------------------------------------------------ convite da equipe
def convites_abertos():
    """Convites da conta que ainda valem (não usados e não vencidos), do mais novo para o mais antigo."""
    return (da_conta(Convite).filter(Convite.usado_em.is_(None), Convite.expira_em > datetime.now())
            .order_by(Convite.id.desc()).all())


def convidar(email_txt, papel):
    """
    Cria o convite e tenta mandar o e-mail. Devolve (convite, link, enviou_email).
    O link só existe aqui: no banco fica o hash.
    """
    email = _email(email_txt)
    if not email:
        raise AcessoInvalido('Informe um e-mail válido para enviar o convite.')
    if papel not in PAPEIS_DE_CONVITE:
        raise AcessoInvalido('Escolha o papel: recepção ou instrutor.')
    conta = current_user.conta
    existente = _usuario_do_email(email)
    if existente and (existente.conta_id != conta.id or existente.ativo):
        # mesma frase para "já é da sua equipe" e "é de outra academia": não revela onde a pessoa tem conta
        raise AcessoInvalido('Este e-mail já tem acesso ao sistema e não pode ser convidado.')
    abertos = convites_abertos()
    if len(abertos) >= MAX_CONVITES_ABERTOS:
        raise AcessoInvalido('Há convites demais esperando resposta. Cancele os que não valem mais.')
    for antigo in abertos:                       # convidar de novo o mesmo e-mail troca o convite anterior
        if antigo.email == email:
            db.session.delete(antigo)
    token = secrets.token_urlsafe(32)
    convite = Convite(conta_id=conta.id, email=email, papel=papel, token_hash=_hash(token), criado_por_id=current_user.id,
                      expira_em=datetime.now() + VALIDADE_DO_CONVITE)
    db.session.add(convite)
    db.session.commit()
    link = url_for('auth.convite', token=token, _external=True)
    enviou = enviar_email(email, f'Convite para a equipe da {conta.nome}',
                          f'Olá!\n\n{current_user.nome} convidou você para a equipe da {conta.nome} no Vale Tec, como '
                          f'{PAPEIS_DE_CONVITE[papel].lower()}.\n\nCrie a sua senha neste link (vale 7 dias e só pode ser usado uma vez):\n{link}\n\n'
                          'Se você não esperava este convite, é só ignorar este e-mail.')
    return convite, link, enviou


def convite_do_link(token):
    """O convite deste link, se ainda vale; senão None (não existe, venceu ou já foi usado)."""
    convite = Convite.query.filter_by(token_hash=_hash(token or '')).first()
    if convite is None or convite.usado_em is not None or convite.expira_em <= datetime.now():
        return None
    return convite


def convite_para_a_tela(convite):
    """O convite no formato que auth/convite.html espera."""
    quem = db.session.get(User, convite.criado_por_id)
    return {'academia': convite.conta.nome, 'email': convite.email, 'papel': convite.papel,
            'papel_rotulo': PAPEIS_DE_CONVITE.get(convite.papel, convite.papel), 'quem_convidou': (quem.nome if quem else None) or 'O dono'}


def aceitar_convite(convite, nome, senha):
    """
    A pessoa convidada cria o acesso. Devolve o usuário. Marca o convite como usado na mesma
    transação, o que garante o uso único.
    """
    nome = ' '.join((nome or '').split())[:100]
    partes = nome.split()
    usuario = _usuario_do_email(convite.email)
    if usuario is None:
        usuario = User(email=convite.email, conta_id=convite.conta_id)
        db.session.add(usuario)
    elif usuario.conta_id != convite.conta_id or usuario.ativo:
        raise AcessoInvalido('Este e-mail já tem acesso ao sistema.')
    # (quem já foi da equipe e tinha sido removido volta com o mesmo cadastro, reativado)
    usuario.nome, usuario.sobrenome = partes[0], ' '.join(partes[1:]) or None
    usuario.papel, usuario.ativo, usuario.senha = convite.papel, True, _senha_guardada(senha)
    convite.usado_em = datetime.now()
    db.session.commit()
    return usuario


def cancelar_convite(id):
    convite = da_conta(Convite).filter_by(id=id).first()
    if convite is None:
        raise AcessoInvalido('Convite não encontrado.')
    db.session.delete(convite)
    db.session.commit()
    return convite


def _membro(id):
    """Alguém da equipe da conta que NÃO é o dono nem a própria pessoa logada."""
    membro = da_conta(User).filter_by(id=id, ativo=True).first()
    if membro is None or membro.papel == PAPEL_PROPRIETARIO or membro.id == current_user.id:
        raise AcessoInvalido('Pessoa não encontrada na equipe.')
    return membro


def trocar_papel(id, papel):
    if papel not in PAPEIS_DE_CONVITE:
        raise AcessoInvalido('Escolha o papel: recepção ou instrutor.')
    membro = _membro(id)
    membro.papel = papel
    db.session.commit()
    return membro


def remover_da_equipe(id):
    """
    Tira o acesso da pessoa. O cadastro NÃO é apagado (o nome dela continua nos pagamentos e nas
    entradas que confirmou): ela fica desativada, some da lista da equipe e não consegue mais entrar.
    """
    membro = _membro(id)
    membro.ativo = False
    db.session.commit()
    return membro


# ------------------------------------------------------------------ troca de senha
def pedir_troca_de_senha(email_txt, enviar=True):
    """
    Gera o link de troca de senha de quem tem conta ativa com este e-mail e, se `enviar`, manda
    por e-mail. Devolve o link, ou None se não há conta. QUEM CHAMA A PARTIR DE UMA TELA PÚBLICA
    NÃO PODE MOSTRAR A DIFERENÇA: a resposta ao usuário tem de ser a mesma nos dois casos.
    """
    email = _email(email_txt)
    usuario = _usuario_do_email(email) if email else None
    if usuario is None or not usuario.ativo:
        return None
    RedefinicaoSenha.query.filter_by(usuario_id=usuario.id, usado_em=None).delete()      # um pedido novo cancela os anteriores
    token = secrets.token_urlsafe(32)
    db.session.add(RedefinicaoSenha(usuario_id=usuario.id, token_hash=_hash(token), expira_em=datetime.now() + VALIDADE_DA_TROCA_DE_SENHA))
    db.session.commit()
    link = url_for('auth.nova_senha', token=token, _external=True)
    if enviar:
        enviar_email(usuario.email, 'Troca de senha do Vale Tec',
                     f'Olá, {usuario.nome}!\n\nPara criar uma senha nova, abra este link (vale 1 hora e só pode ser usado uma vez):\n{link}\n\n'
                     'Se você não pediu a troca, ignore este e-mail: a sua senha continua a mesma.')
    return link


def pedido_de_troca_do_link(token):
    """O pedido de troca de senha deste link, se ainda vale; senão None."""
    pedido = RedefinicaoSenha.query.filter_by(token_hash=_hash(token or '')).first()
    if pedido is None or pedido.usado_em is not None or pedido.expira_em <= datetime.now():
        return None
    usuario = db.session.get(User, pedido.usuario_id)
    return pedido if (usuario and usuario.ativo) else None


def trocar_senha(pedido, senha):
    """Grava a senha nova e marca o link como usado. Devolve o usuário."""
    usuario = db.session.get(User, pedido.usuario_id)
    usuario.senha = _senha_guardada(senha)
    pedido.usado_em = datetime.now()
    db.session.commit()
    return usuario
