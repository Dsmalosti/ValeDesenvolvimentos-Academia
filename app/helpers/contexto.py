"""
Variáveis que TODO template do front novo usa (cabeçalho, menu, rodapé).

[back-04-painel] Criado nesta branch. É o `context_processor` do contrato front <-> back
(Integracao-Front-Back.md, §3.3): `usuario`, `academia` e `oferecer_digital` chegam em toda
página sem cada rota precisar passar. O `csrf_token()` o Flask-WTF já fornece sozinho.

PROVISÓRIO: o banco ainda não tem a tabela da academia (`contas`) nem a coluna `papel`
(tarefas 3.2 e 3.6, que pedem migration). Enquanto isso:
  - `academia` vem de valores fixos, definidos em ACADEMIA_PROVISORIA abaixo;
  - todo usuário é tratado como dono da própria conta.
Quando a tabela existir, só as duas funções `_usuario()` e `_academia()` mudam.
"""
from flask_login import current_user

# Valores fixos até existir a tela de Configurações (tabela `contas`).
#   checkin_ativo=False: o módulo de frequência ainda não existe, então o menu não mostra
#       "Frequência" e o painel não mostra o card de ausentes (que daria um número falso).
#   pix_ligado=False: a cobrança por PIX ainda não existe.
ACADEMIA_PROVISORIA = {
    'nome': 'Minha academia', 'razao': '', 'cnpj': '', 'telefone': '', 'email': '',
    'cidade': '', 'endereco': '', 'pix_ligado': False, 'checkin_ativo': False, 'modelo': 'academia',
}


def _iniciais(nome):
    """'Ana Paula Ramos' -> 'AR' (primeira letra do primeiro e do último nome)."""
    partes = (nome or '').split()
    if not partes:
        return '?'
    return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else '')).upper()


def _usuario():
    nome = ' '.join(p for p in (current_user.nome, current_user.sobrenome) if p).strip()
    nome = nome or (current_user.email or 'Usuário')
    return {
        'nome': nome,
        'iniciais': _iniciais(nome),
        'email': current_user.email,
        # PROVISÓRIO: sem a coluna `papel`, todo mundo é dono. No front, `perfil` diferente de
        # 'instrutor' é quem enxerga o Administrativo; `papel` é só o texto mostrado no menu.
        'papel': 'proprietário',
        'perfil': 'recepcao',
    }


def _academia():
    return dict(ACADEMIA_PROVISORIA)


def registrar_contexto(app):
    """Liga o context_processor no app. Chamado uma vez, no create_app()."""

    @app.context_processor
    def globais():
        if not current_user.is_authenticated:
            # Telas sem login (entrar, páginas de erro) não usam `usuario`.
            return {'academia': _academia(), 'oferecer_digital': False}
        return {
            'usuario': _usuario(),
            'academia': _academia(),
            # O login com digital (passkey) ainda não existe no backend; nunca oferecer.
            'oferecer_digital': False,
        }
