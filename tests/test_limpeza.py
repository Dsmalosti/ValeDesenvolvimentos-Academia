"""Testes da branch back-02-limpeza: os defeitos que quebravam telas ou sujavam o log."""
from app.models import Ficha, Plano
from tests.conftest import (contar, criar_aluno, criar_exercicio, criar_ficha, criar_plano,
                            criar_usuario, logar, numero_do_card)


def test_painel_conta_os_alunos_ativos(cliente):
    """Antes comparava o booleano com o texto 'ativo' e o total dava sempre zero."""
    dono = criar_usuario("dono@teste.local")
    plano = criar_plano(dono)
    criar_aluno(dono, plano, "Ana", "ana@teste.local", "111", ativo=True)
    criar_aluno(dono, plano, "Bia", "bia@teste.local", "222", ativo=True)
    criar_aluno(dono, plano, "Caio", "caio@teste.local", "333", ativo=False)
    logar(cliente, dono)

    pagina = cliente.get("/")

    assert pagina.status_code == 200
    assert numero_do_card(pagina.get_data(as_text=True), 'Alunos ativos') == '2'

# [back-27-telas-antigas] saíram três testes de defeitos das telas antigas (editar exercício, excluir ficha, criar plano): as telas saíram.
