"""
Testes da branch back-31-pdf-ficha-avaliacao: o gerador de PDF (helpers/pdf.py), o PDF da ficha de treino e o PDF da
avaliação física (services/pdf_service.py) e as duas rotas de download.
"""
import re
import zlib
from datetime import date, timedelta

import pytest

from app.extensions.database import db
from app.helpers.pdf import PDF
from app.models import Exercicio, Treino, TreinoExercicio
from tests import conftest
from tests.conftest import (conta_de, criar_aluno, criar_avaliacao, criar_ficha, criar_plano,
                            criar_usuario, logar)

HOJE = date.today()


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def desenho(pdf_bytes):
    """Junta o "desenho" (já descompactado) de todas as páginas: é onde estão os textos."""
    return b"".join(zlib.decompress(m) for m in re.findall(rb"stream\n(.*?)\nendstream", pdf_bytes, re.S))


def paginas(pdf_bytes):
    return int(re.search(rb"/Count (\d+)", pdf_bytes).group(1))


# ------------------------------------------------------------------ o gerador
def test_arquivo_bem_formado_com_tabela_de_posicoes_certa():
    pdf = PDF(titulo="Teste")
    pdf.nova_pagina()
    pdf.texto(40, 60, "Olá, avaliação (teste) \\ fim", tamanho=12)
    pdf.retangulo(40, 80, 100, 30, cor="#0B3456", raio=6)
    pdf.linha(40, 120, 200, 120)
    dados = pdf.gerar()
    assert dados.startswith(b"%PDF-1.4") and dados.rstrip().endswith(b"%%EOF")
    # cada posição da tabela xref aponta exatamente para o começo do objeto de mesmo número
    inicio = int(re.search(rb"startxref\n(\d+)", dados).group(1))
    posicoes = re.findall(rb"(\d{10}) 00000 n", dados[inicio:])
    for numero, pos in enumerate(posicoes, start=1):
        assert dados[int(pos):].startswith(f"{numero} 0 obj".encode())
    # acentos na tabela do Windows (cp1252) e parênteses/barra escapados
    assert b"(Ol\xe1, avalia\xe7\xe3o \\(teste\\) \\\\ fim) Tj" in desenho(dados)


def test_largura_quebra_e_corte():
    pdf = PDF()
    assert PDF.largura("iiii", 10) < PDF.largura("MMMM", 10)                   # letra fina ocupa menos
    assert PDF.largura("abc", 10, negrito=True) > PDF.largura("abc", 10)
    linhas = pdf.quebrar("um texto comprido que precisa quebrar em várias linhas", 80, 10)
    assert len(linhas) > 1 and all(PDF.largura(l, 10) <= 80 for l in linhas)
    cortado = pdf.cortar("Ana Beatriz Souza de Albuquerque Ferreira", 100, 12)
    assert cortado.endswith("…") and PDF.largura(cortado, 12) <= 100
    assert pdf.quebrar("linha 1\nlinha 2", 500) == ["linha 1", "linha 2"]


def test_letra_fora_da_tabela_vira_interrogacao_e_nao_quebra():
    pdf = PDF()
    pdf.nova_pagina()
    pdf.texto(40, 40, "Força 💪 − ok")
    assert b"(For\xe7a ? - ok) Tj" in desenho(pdf.gerar())


# ------------------------------------------------------------------ cenário
@pytest.fixture()
def academia(app):
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    plano = criar_plano(dono)
    ana = criar_aluno(dono, plano, "Ana Souza", "ana@exemplo.com", "111.222.333-96")
    return {"dono": dono, "conta": conta, "ana": ana, "plano": plano,
            "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
            "instrutor": criar_usuario("ivo@teste.local", nome="Ivo", conta=conta, papel="instrutor")}


def montar_ficha(academia, treinos=2, exercicios=4):
    ficha = criar_ficha(academia["ana"], nome="Hipertrofia")
    with conftest._APP.app_context():
        for t in range(treinos):
            treino = Treino(ficha_id=ficha, letra="ABCDE"[t], nome=f"Treino número {t + 1}")
            db.session.add(treino)
            db.session.flush()
            for i in range(exercicios):
                ex = Exercicio(nome=f"Exercício {t + 1}.{i + 1}", grupo_muscular="Peito", ativo=True)
                db.session.add(ex)
                db.session.flush()
                db.session.add(TreinoExercicio(treino_id=treino.id, exercicio_id=ex.id, series=3, repeticoes="12", carga="20 kg",
                                               descanso="60s", ordem=i))
        db.session.commit()
    return ficha


# ------------------------------------------------------------------ ficha
def test_pdf_da_ficha_tem_os_treinos_e_baixa_com_o_nome_certo(app, academia):
    montar_ficha(academia)
    resposta = como(app, academia["dono"]).get(f"/alunos/{academia['ana']}/ficha/pdf")
    assert resposta.status_code == 200 and resposta.headers["Content-Type"] == "application/pdf"
    assert resposta.headers["Content-Disposition"] == "attachment; filename=ficha-ana-souza.pdf"
    assert "no-store" in resposta.headers["Cache-Control"]                       # dado pessoal: nenhum cache guarda
    texto = desenho(resposta.data)
    for trecho in (b"FICHA DE TREINO", b"Academia de Diana", b"Ana Souza", b"Treino A \xb7 Treino n\xfamero 1",
                   b"Exerc\xedcio 2.4", b"20 kg", b"P\xe1gina 1 de 1"):
        assert trecho in texto, trecho


def test_ficha_comprida_quebra_pagina_e_repete_o_titulo(app, academia):
    montar_ficha(academia, treinos=5, exercicios=10)
    dados = como(app, academia["dono"]).get(f"/alunos/{academia['ana']}/ficha/pdf").data
    total = paginas(dados)
    assert total >= 3 and f"P\xe1gina {total} de {total}".encode("cp1252") in desenho(dados)
    # o treino que passou da página repete o título (no PDF, os parênteses do texto ficam escapados com barra)
    assert b"\\(continua\xe7\xe3o\\)" in desenho(dados)


@pytest.mark.parametrize("papel", ["recepcao", "instrutor"])
def test_toda_a_equipe_baixa_a_ficha(app, academia, papel):
    montar_ficha(academia)
    assert como(app, academia[papel]).get(f"/alunos/{academia['ana']}/ficha/pdf").status_code == 200


def test_ficha_de_outra_conta_ou_sem_ficha_da_404_e_sem_login_pede_login(app, academia):
    montar_ficha(academia)
    outro = criar_usuario("outro@teste.local", nome="Otto")
    assert como(app, outro).get(f"/alunos/{academia['ana']}/ficha/pdf").status_code == 404
    bia = criar_aluno(academia["dono"], academia["plano"], "Bia Lima", "bia@exemplo.com", "529.982.247-25")
    assert como(app, academia["dono"]).get(f"/alunos/{bia}/ficha/pdf").status_code == 404
    assert app.test_client().get(f"/alunos/{academia['ana']}/ficha/pdf").headers["Location"].startswith("/login")


# ------------------------------------------------------------------ avaliação
def test_pdf_da_avaliacao_com_comparacao(app, academia):
    criar_avaliacao(academia["dono"], academia["ana"], HOJE - timedelta(days=60), peso=72, cintura_cm=84, quadril_cm=100)
    nova = criar_avaliacao(academia["dono"], academia["ana"], HOJE, peso=69.5, cintura_cm=80, quadril_cm=100, anotacao="Manter o ritmo.")
    resposta = como(app, academia["dono"]).get(f"/avaliacoes/{nova}/pdf")
    assert resposta.status_code == 200 and resposta.headers["Content-Disposition"] == "attachment; filename=avaliacao-ana-souza.pdf"
    texto = desenho(resposta.data)
    for trecho in (b"AVALIA\xc7\xc3O F\xcdSICA", b"Ana Souza", b"69,5", b"72,0 kg", b"-2,5 kg", b"-4,0 cm", b"60 dias antes",
                   b"Manter o ritmo.", b"sem mudan\xe7a", b"n\xe3o um diagn\xf3stico"):
        assert trecho in texto, trecho


def test_primeira_avaliacao_sem_comparacao(app, academia):
    unica = criar_avaliacao(academia["dono"], academia["ana"], HOJE, peso=70)
    texto = desenho(como(app, academia["dono"]).get(f"/avaliacoes/{unica}/pdf").data)
    assert b"primeira avalia\xe7\xe3o" in texto and b"VARIA\xc7\xc3O" not in texto and b"Sem anota\xe7\xe3o." in texto


def test_avaliacao_de_outra_conta_da_404(app, academia):
    feita = criar_avaliacao(academia["dono"], academia["ana"], HOJE)
    outro = criar_usuario("outro@teste.local", nome="Otto")
    assert como(app, outro).get(f"/avaliacoes/{feita}/pdf").status_code == 404
    assert como(app, academia["recepcao"]).get(f"/avaliacoes/{feita}/pdf").status_code == 200    # a recepção vê o resultado (back-22)


# ------------------------------------------------------------------ telas
def test_telas_tem_os_botoes_do_pdf(app, academia):
    montar_ficha(academia)
    feita = criar_avaliacao(academia["dono"], academia["ana"], HOJE)
    dono = como(app, academia["dono"])
    envio = dono.get(f"/alunos/{academia['ana']}/ficha/enviar").get_data(as_text=True)
    assert "data-compartilhar-pdf" in envio and 'data-arquivo="ficha-ana-souza.pdf"' in envio and "js/compartilhar-pdf.js" in envio
    resultado = dono.get(f"/avaliacoes/{feita}").get_data(as_text=True)
    assert f'href="/avaliacoes/{feita}/pdf"' in resultado and "O PDF da avaliação é gerado pelo backend." not in resultado
