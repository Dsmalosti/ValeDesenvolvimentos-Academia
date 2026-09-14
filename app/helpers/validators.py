import re

from app.exceptions import BusinessError


def somente_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def cpf_valido(cpf):
    digitos = somente_digitos(cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False

    for posicao in (9, 10):
        soma = sum(int(digitos[i]) * (posicao + 1 - i) for i in range(posicao))
        verificador = (soma * 10 % 11) % 10
        if verificador != int(digitos[posicao]):
            return False
    return True


def normalizar_email(email):
    email = (email or "").strip().lower()
    if not email:
        raise BusinessError("E-mail é obrigatório.")
    return email


def normalizar_cpf(cpf):
    """Retorna o CPF no formato 000.000.000-00 ou None se não informado."""
    if not (cpf or "").strip():
        return None
    if not cpf_valido(cpf):
        raise BusinessError("CPF inválido.")
    d = somente_digitos(cpf)
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def normalizar_telefone(telefone):
    """Retorna o telefone no formato (00) 00000-0000 ou None se não informado."""
    d = somente_digitos(telefone)
    if not d:
        return None
    if len(d) not in (10, 11):
        raise BusinessError("Telefone inválido. Informe DDD + número.")
    return f"({d[:2]}) {d[2:-4]}-{d[-4:]}"


def texto_ou_none(valor):
    valor = (valor or "").strip()
    return valor or None
