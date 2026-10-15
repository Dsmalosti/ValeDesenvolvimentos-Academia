"""
[back-15-avaliacoes] Endereço que abre o WhatsApp de quem está usando, já na conversa do aluno e
com o texto escrito (decisão D14: mensagem gratuita).

O sistema NÃO envia mensagem. Ele só monta o endereço `https://wa.me/<número>?text=<texto>`: a
pessoa toca, o WhatsApp abre com tudo pronto e ela toca em enviar. Funciona no celular e no
WhatsApp Web, sem API paga.

Antes desta branch, a conta do código do país estava dentro do treino_service (back-14). Veio
para cá porque a avaliação física (e, depois, as mensagens) usam a mesma regra.
"""
import re
from urllib.parse import quote


def so_numeros(telefone):
    """Só os dígitos do telefone: '(12) 98211-4400' -> '12982114400'."""
    return re.sub(r'\D', '', telefone or '')


def numero_com_pais(telefone):
    """
    O telefone no formato do wa.me: só dígitos, com o código do Brasil (55) na frente.

    DDD + número tem 10 ou 11 dígitos e ganha o 55. Olhar o TAMANHO, e não se "começa com 55":
    55 também é DDD (Santa Maria/RS), e o número de lá ficaria sem o código do país.
    Telefone vazio devolve '' (o WhatsApp abre para a pessoa escolher o contato).
    """
    numero = so_numeros(telefone)
    return '55' + numero if numero and len(numero) <= 11 else numero


def link_do_whatsapp(telefone, texto=''):
    """Endereço wa.me para o telefone, com o texto já codificado."""
    endereco = f'https://wa.me/{numero_com_pais(telefone)}'
    return f'{endereco}?text={quote(texto)}' if texto else endereco
