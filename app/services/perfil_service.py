"""
[back-30-meu-perfil] MEU PERFIL: cada pessoa (dono, recepção, instrutor ou personal) edita o próprio nome e e-mail
e troca a própria senha, na tela /perfil.

Antes não existia nas telas novas: só a tela antiga /instrutores/editar/<id> fazia isso, e ela saiu na back-27.
A senha só se trocava pelo "esqueci a senha". Decisão do Adauto (17/10/2026): precisa para o lançamento.

Regras:
  - trocar o NOME não pede senha;
  - trocar o E-MAIL (que é o login) pede a senha atual: quem pegar o celular desbloqueado de alguém não troca o login dele;
  - trocar a SENHA pede a senha atual. Depois disso os outros aparelhos saem da conta (a "marca da senha" guardada na
    sessão muda, ver User.get_id) e este continua logado (a rota faz o login de novo);
  - o admin do Vale Tec que entrou na conta de um cliente NÃO muda o perfil do dono (a rota recusa).
"""
from app.extensions.database import db
from app.extensions.security import bcrypt
from app.services.acesso_service import _email, _senha_guardada, _usuario_do_email, erro_da_senha

NOME_MAXIMO = 100           # tamanho das colunas instrutores.nome e instrutores.sobrenome


def _senha_confere(usuario, senha):
    """A senha digitada é a senha atual do usuário?"""
    if not usuario.senha or not senha:
        return False
    try:
        return bcrypt.check_password_hash(usuario.senha, senha)
    except ValueError:      # senha guardada num formato que o bcrypt não lê (dado antigo)
        return False


def valores_da_tela(usuario):
    """O que o formulário mostra ao abrir."""
    return {'nome': usuario.nome or '', 'sobrenome': usuario.sobrenome or '', 'email': usuario.email or ''}


def salvar_dados(usuario, formulario):
    """
    Confere e grava nome, sobrenome e e-mail. Devolve (valores, erros {campo: mensagem}).
    Com erro, nada é gravado. Sem erro, grava e devolve erros vazio.
    """
    valores = {'nome': ' '.join((formulario.get('nome') or '').split()),
               'sobrenome': ' '.join((formulario.get('sobrenome') or '').split()),
               'email': (formulario.get('email') or '').strip().lower()}
    erros = {}
    if not valores['nome']:
        erros['nome'] = 'Informe o seu nome.'
    elif len(valores['nome']) > NOME_MAXIMO:
        erros['nome'] = f'Use no máximo {NOME_MAXIMO} caracteres.'
    if len(valores['sobrenome']) > NOME_MAXIMO:
        erros['sobrenome'] = f'Use no máximo {NOME_MAXIMO} caracteres.'

    email_mudou = valores['email'] != (usuario.email or '').lower()
    if email_mudou:
        if not _email(valores['email']):
            erros['email'] = 'Confira o e-mail (ex.: voce@gmail.com).'
        else:
            dono_do_email = _usuario_do_email(valores['email'])
            if dono_do_email and dono_do_email.id != usuario.id:
                erros['email'] = 'Esse e-mail já é o login de outra pessoa.'
        if not _senha_confere(usuario, formulario.get('senha_atual')):
            erros['senha_atual'] = 'Para trocar o e-mail, digite a sua senha atual.'
    if erros:
        return valores, erros

    usuario.nome = valores['nome']
    usuario.sobrenome = valores['sobrenome'] or None
    usuario.email = valores['email']
    db.session.commit()
    return valores, {}


def trocar_senha(usuario, atual, nova):
    """Confere e troca a senha. Devolve erros {campo: mensagem}; vazio = trocou."""
    erros = {}
    if not _senha_confere(usuario, atual):
        erros['senha_atual'] = 'A senha atual não confere.'
    problema = erro_da_senha(nova)
    if problema:
        erros['senha_nova'] = problema
    elif not erros and atual == nova:
        erros['senha_nova'] = 'A nova senha é igual à atual.'
    if erros:
        return erros
    usuario.senha = _senha_guardada(nova)
    db.session.commit()
    return {}
