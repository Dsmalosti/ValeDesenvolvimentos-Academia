"""
Variáveis que TODO template do front novo usa (cabeçalho, menu, rodapé).

[back-04-painel] Criado. É o `context_processor` do contrato front <-> back
(Integracao-Front-Back.md, §3.3): `usuario`, `academia` e `oferecer_digital` chegam em toda
página sem cada rota precisar passar. O `csrf_token()` o Flask-WTF já fornece sozinho.

[back-06-contas-e-papeis] Antes, `academia` vinha de valores fixos ("Minha academia") e todo
usuário era tratado como dono, porque o banco não tinha onde guardar isso. Agora os dois vêm
do banco: `academia` é a conta do usuário (tabela `contas`) e o papel é a coluna `papel`.
"""
from flask_login import current_user

from app.models import PAPEL_INSTRUTOR

# Como o papel aparece escrito no menu do front
ROTULO_DO_PAPEL = {'proprietario': 'proprietário', 'recepcao': 'recepção', 'instrutor': 'instrutor'}

# Usada só nas telas sem login (entrar, páginas de erro), que não têm conta para consultar.
ACADEMIA_SEM_LOGIN = {
    'nome': 'Vale Tec', 'razao': '', 'cnpj': '', 'telefone': '', 'email': '',
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
        # `papel` é o texto mostrado no menu. `perfil` é o que os templates testam para esconder
        # o Administrativo do instrutor (usuario.perfil != 'instrutor'); os outros dois papéis
        # usam o layout completo, que no front se chama 'recepcao'.
        'papel': ROTULO_DO_PAPEL.get(current_user.papel, current_user.papel),
        'perfil': 'instrutor' if current_user.papel == PAPEL_INSTRUTOR else 'recepcao',
    }


def _academia():
    conta = current_user.conta
    return {
        'nome': conta.nome, 'razao': conta.razao or '', 'cnpj': conta.cnpj or '',
        'telefone': conta.telefone or '', 'email': conta.email or '',
        'cidade': conta.cidade or '', 'endereco': conta.endereco or '',
        'pix_ligado': conta.pix_ligado, 'checkin_ativo': conta.checkin_ativo, 'modelo': conta.modelo,
    }


def registrar_contexto(app):
    """Liga o context_processor no app. Chamado uma vez, no create_app()."""

    @app.context_processor
    def globais():
        if not current_user.is_authenticated:
            # Telas sem login (entrar, páginas de erro) não usam `usuario`.
            return {'academia': dict(ACADEMIA_SEM_LOGIN), 'oferecer_digital': False}
        return {
            'usuario': _usuario(),
            'academia': _academia(),
            # O login com digital (passkey) ainda não existe no backend; nunca oferecer.
            'oferecer_digital': False,
        }
