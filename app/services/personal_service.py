"""
[back-17-personal] O que só a conta de PERSONAL TRAINER tem nas telas de painel e de configurações.

O painel do personal usa os mesmos números do painel da academia (services/painel_service.py) e
acrescenta o que é dele: pacotes acabando, ticket por pacote e sessões de hoje. Saldo e pacotes ficam
em services/pacote_service.py; a agenda, em services/agenda_service.py.
"""
import re

from flask_login import current_user

from app.extensions.database import db
from app.helpers.conta import da_conta
from app.models import Plano
from app.services import agenda_service, pacote_service
from app.services.painel_service import montar_painel

ABAS = [('perfil', 'Perfil'), ('locais', 'Locais'), ('mensagens', 'Mensagens'), ('cobranca', 'Cobrança'), ('metas', 'Metas')]
# Texto padrão das mensagens que mudam na conta de personal: ele fala na primeira pessoa e cobra PACOTE, não mensalidade.
MODELOS_PADRAO = {
    'cobranca': 'Oi [nome], tudo certo? Seu pacote ([plano]) de [valor] está em aberto. Quer que eu mande o PIX?',
    'aniversario': 'Parabéns, [nome]! Que seu dia seja ótimo. Bora comemorar com um treino caprichado essa semana?',
}


class PerfilInvalido(Exception):
    """O que foi enviado não pode ser gravado. A mensagem é mostrada ao usuário."""


# ------------------------------------------------------------------ painel
def _ticket(k, planos_fat):
    """Popup "Ticket médio": quanto cada aluno ativo rende, no geral e por pacote (o que rende mais primeiro)."""
    por_pacote = [{'plano_id': p['plano_id'], 'nome': p['nome'], 'alunos': p['alunos'], 'cor': p['cor'], 'avulso': p.get('avulso', False),
                   'por_aluno': (p['valor'] / p['alunos']) if p['alunos'] else 0.0} for p in planos_fat]
    return {'valor': k['ticket'], 'faturamento': k['faturamento'], 'ativos': k['ativos'],
            'por_pacote': sorted(por_pacote, key=lambda p: -p['por_aluno'])}


def contexto_do_painel():
    """Variáveis de personal/painel.html."""
    contexto = montar_painel()
    acabando = pacote_service.acabando(pacote_service.ACABANDO_NO_PAINEL)
    contexto['k']['pacotes_acabando'] = len(acabando)
    contexto['acabando'] = acabando
    contexto['sessoes_hoje'] = agenda_service.sessoes_de_hoje()
    avulsos = {p.id for p in da_conta(Plano).all() if pacote_service.e_avulso(p)}
    for p in contexto['planos_fat']:
        p['avulso'] = p['plano_id'] in avulsos
    contexto['ticket'] = _ticket(contexto['k'], contexto['planos_fat'])
    # "em risco" do personal: quem está na última sessão do pacote, antes de quem está com pagamento atrasado
    ultima = [{'nome': a['nome'], 'tipo': 'pacote', 'tom': 'yellow', 'telefone': a['telefone'],
               'motivo': 'Pacote acaba na próxima sessão' if a['pacote']['saldo'] == 1 else 'Pacote sem saldo'}
              for a in acabando if a['pacote']['saldo'] <= 1]
    contexto['alertas']['risco'] = ultima + contexto['alertas']['risco']
    return contexto


# ------------------------------------------------------------------ configurações
def contexto_das_configuracoes(contexto, aba):
    """Completa o contexto de config (services/config_service.py) com o que personal/config.html usa."""
    contexto.update({'aba': aba if aba in dict(ABAS) else None, 'abas': ABAS, 'locais': agenda_service.locais(),
                     'pacotes_ativos': da_conta(Plano).filter(Plano.ativo.is_(True)).count()})
    return contexto


def _cpf_valido(numeros):
    """Confere os dois dígitos verificadores do CPF (11 números)."""
    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(numeros[i]) * (tamanho + 1 - i) for i in range(tamanho))
        if (soma * 10 % 11) % 10 != int(numeros[tamanho]):
            return False
    return True


def salvar_perfil(formulario):
    """Dados do profissional (aba Perfil): nome, CPF, CREF, telefone, e-mail e cidade. Só o nome é obrigatório."""
    conta = current_user.conta
    nome = ' '.join((formulario.get('nome') or '').split())
    if not nome or len(nome) > 120:
        raise PerfilInvalido('Informe o seu nome (até 120 letras).')
    cpf = re.sub(r'\D', '', formulario.get('cpf') or '')
    if cpf and not _cpf_valido(cpf):
        raise PerfilInvalido('CPF inválido. Confira os números.')
    cref = ' '.join((formulario.get('cref') or '').split()).upper()
    if len(cref) > 20:
        raise PerfilInvalido('CREF longo demais (até 20 letras e números).')
    email = (formulario.get('email') or '').strip().lower()
    if email and (len(email) > 120 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email)):
        raise PerfilInvalido('E-mail inválido.')
    conta.nome = nome
    conta.cpf = f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}' if cpf else None
    conta.cref = cref or None
    conta.telefone = (formulario.get('telefone') or '').strip()[:20] or None
    conta.email = email or None
    conta.cidade = ' '.join((formulario.get('cidade') or '').split())[:80] or None
    db.session.commit()
    return conta
