from datetime import date

def hoje():
    return date.today()


def is_aniversariante(data_nascimento):
    if not data_nascimento:
        return False

    hoje_data = hoje()
    return (
        data_nascimento.day == hoje_data.day
        and data_nascimento.month == hoje_data.month
    )
