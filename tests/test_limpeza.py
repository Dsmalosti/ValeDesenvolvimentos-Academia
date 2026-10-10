"""Testes da branch back-02-limpeza: os defeitos que quebravam telas ou sujavam o log."""
from app.models import Ficha, Plano
from tests.conftest import (contar, criar_aluno, criar_exercicio, criar_ficha, criar_plano,
                            criar_usuario, logar, numero_do_card)


def test_editar_exercicio_volta_para_a_lista(cliente):
    """Antes dava erro 500: o redirect apontava para 'exercicios.listarPlanos', que não existe."""
    logar(cliente, criar_usuario("dono@teste.local"))
    exercicio_id = criar_exercicio("Supino")

    resposta = cliente.post(f"/exercicios/editar/{exercicio_id}",
                            data={"nome": "Supino reto", "grupo_muscular": "peito", "ativo": "y"})

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/exercicios/listar/")


def test_excluir_ficha_usa_a_url_certa(cliente):
    """A rota era /fichas/excuir/<id> (erro de digitação). Agora é /fichas/excluir/<id>."""
    dono = criar_usuario("dono@teste.local")
    logar(cliente, dono)
    ficha_id = criar_ficha(criar_aluno(dono, criar_plano(dono), "Ana", "ana@teste.local", "111"))

    assert cliente.post(f"/fichas/excuir/{ficha_id}").status_code == 404
    assert cliente.post(f"/fichas/excluir/{ficha_id}").status_code == 302
    assert contar(Ficha, id=ficha_id) == 0


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


def test_criar_plano_nao_imprime_dados_do_formulario(cliente, capsys):
    """Os print() jogavam os dados digitados no log do servidor."""
    logar(cliente, criar_usuario("dono@teste.local"))

    resposta = cliente.post("/planos/criar/", data={"nome": "Plano Secreto", "valor": "150.00",
                                                    "duracao_dias": "30", "descricao": "x", "ativo": "y"})

    assert resposta.status_code == 302
    assert contar(Plano, nome="Plano Secreto") == 1
    saida = capsys.readouterr()
    assert saida.out == ""
    assert "Plano Secreto" not in saida.err
