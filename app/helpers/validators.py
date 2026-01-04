from app.exceptions import BusinessError

def validar_plano(plano_id):
    if not plano_id:
        raise BusinessError("Aluno precisa estar vinculado a um plano")

def validar_email(email):
    if not email:
        raise BusinessError("Email é obrigatório")

def validar_cpf(cpf):
    if not cpf:
        raise BusinessError("CPF é obrigatório")
