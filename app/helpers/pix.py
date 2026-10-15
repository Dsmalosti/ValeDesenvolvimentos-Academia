"""
[back-24-assinatura] O código "PIX copia e cola" (o BR Code do Banco Central) com valor fixo.

Sem biblioteca nova: o código é só texto no formato EMV ("campo, tamanho, valor", um atrás do outro),
terminado por um número de conferência (CRC16). O formato está no "Manual de Padrões para Iniciação do
Pix", do Banco Central.

O código é ESTÁTICO: o dinheiro cai direto na chave informada e o sistema NÃO fica sabendo sozinho que
o pagamento chegou. Quem confirma é uma pessoa (o administrador), conferindo no aplicativo do banco.
Para o sistema confirmar sozinho seria preciso uma empresa de pagamento (gateway), o que fica para depois.
"""
import unicodedata

ARRANJO_PIX = 'br.gov.bcb.pix'


def _campo(numero, valor):
    """Um campo do código: número de 2 dígitos, tamanho de 2 dígitos e o valor."""
    return f'{numero}{len(valor):02d}{valor}'


def _so_letras(texto, limite):
    """Nome e cidade vão sem acento e em maiúsculas (é o que os bancos aceitam sem reclamar)."""
    sem_acento = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode('ascii')
    return ' '.join(''.join(c for c in sem_acento.upper() if c.isalnum() or c == ' ').split())[:limite]


def _identificador(texto):
    """O identificador da cobrança (txid): só letras e números, até 25. Sem ele, o padrão é "***"."""
    so_alfanumerico = ''.join(c for c in (texto or '') if c.isascii() and c.isalnum())[:25]
    return so_alfanumerico or '***'


def crc16(texto):
    """CRC16-CCITT (polinômio 0x1021, começando em 0xFFFF), como o Banco Central pede. 4 letras hexadecimais."""
    crc = 0xFFFF
    for byte in texto.encode('utf-8'):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f'{crc:04X}'


def copia_e_cola(chave, nome, cidade, valor=None, identificador=''):
    """
    Monta o código. `chave` é a chave PIX de quem recebe (CNPJ, e-mail, telefone ou chave aleatória),
    `valor` em reais (Decimal ou float; sem valor, quem paga digita), `identificador` aparece no extrato.
    """
    conta = _campo('00', ARRANJO_PIX) + _campo('01', chave.strip())
    texto = (_campo('00', '01')                                  # versão do formato
             + _campo('26', conta)                               # para onde vai o dinheiro
             + _campo('52', '0000')                              # categoria do comércio (não informada)
             + _campo('53', '986')                               # moeda: real
             + (_campo('54', f'{valor:.2f}') if valor else '')   # valor
             + _campo('58', 'BR')
             + _campo('59', _so_letras(nome, 25) or 'VALE TEC')
             + _campo('60', _so_letras(cidade, 15) or 'BRASIL')
             + _campo('62', _campo('05', _identificador(identificador)))
             + '6304')                                           # o CRC vem a seguir, calculado sobre tudo até aqui
    return texto + crc16(texto)
