"""[back-31-pdf-ficha-avaliacao] Respostas de download de arquivo (por enquanto, só PDF)."""
from flask import make_response


def resposta_em_pdf(dados, nome_do_arquivo):
    """
    [back-31-pdf-ficha-avaliacao] O PDF como resposta: baixa com o nome certo. `no-store`: tem dado pessoal do aluno (medidas, treino);
    nenhum cache no caminho (nem o do navegador) guarda uma cópia.
    """
    resposta = make_response(dados)
    resposta.headers['Content-Type'] = 'application/pdf'
    resposta.headers['Content-Disposition'] = f'attachment; filename={nome_do_arquivo}'
    resposta.headers['Cache-Control'] = 'private, no-store'
    return resposta
