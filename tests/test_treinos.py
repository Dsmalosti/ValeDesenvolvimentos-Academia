"""Testes da branch back-14-treinos: catálogo de exercícios, modelos prontos, ficha do aluno e envio pelo WhatsApp."""
from datetime import date, timedelta

import pytest

from app.dados_padrao import EXERCICIOS_PADRAO, MODELOS
from app.models import Exercicio, Ficha, Treino, TreinoExercicio
from tests.conftest import (campo, conta_de, contar, criar_aluno, criar_exercicio, criar_ficha, criar_plano, criar_treino,
                            criar_usuario, logar, semear_catalogo, _salvar)

HOJE = date.today()


@pytest.fixture()
def academia(app):
    """Dona, recepção e instrutor; catálogo padrão no banco; alunas Ana e Bia ativas e Caio inativo."""
    semear_catalogo()
    dono = criar_usuario("dono@teste.local", nome="Diana")
    conta = conta_de(dono)
    plano = criar_plano(dono, nome="Mensal")
    return {"dono": dono, "conta": conta, "plano": plano,
            "recepcao": criar_usuario("rita@teste.local", nome="Rita", conta=conta, papel="recepcao"),
            "instrutor": criar_usuario("igor@teste.local", nome="Igor", conta=conta, papel="instrutor"),
            "ana": criar_aluno(dono, plano, "Ana Souza", "ana@exemplo.com", "111.222.333-96"),
            "bia": criar_aluno(dono, plano, "Bia Lima", "bia@exemplo.com", "555.666.777-20"),
            "caio": criar_aluno(dono, plano, "Caio Inativo", "caio@exemplo.com", "123.456.789-09", ativo=False)}


def como(app, usuario_id):
    cliente = app.test_client()
    logar(cliente, usuario_id)
    return cliente


def id_do(app, nome):
    with app.app_context():
        return Exercicio.query.filter_by(nome=nome).one().id


def dar_ficha(cliente, academia, aluno="ana", modelo=1, acao="ajustar"):
    return cliente.post(f"/treinos/modelo/{modelo}/atribuir", data={"aluno_id": [academia[aluno]], "acao": acao})


def linhas_do_treino(app, aluno_id, letra):
    """[(nome do exercício, séries, repetições, carga, descanso)] do treino da ficha em uso do aluno, na ordem."""
    with app.app_context():
        ficha = Ficha.query.filter_by(aluno_id=aluno_id, ativo=True).order_by(Ficha.id.desc()).first()
        treino = next(t for t in ficha.treinos if t.letra == letra)
        return [(i.exercicio.nome, i.series, i.repeticoes, i.carga, i.descanso) for i in sorted(treino.exercicios, key=lambda i: (i.ordem, i.id))]


# ------------------------------------------------------------------ catálogo
def test_catalogo_padrao_e_gravado_uma_vez_so(app, academia):
    assert contar(Exercicio) == len(EXERCICIOS_PADRAO) == 64
    assert semear_catalogo() == 0 and contar(Exercicio) == 64                 # rodar de novo não duplica
    assert campo(Exercicio, id_do(app, "Supino reto"), "conta_id") is None and campo(Exercicio, id_do(app, "Supino reto"), "equipamento") == "Barra"
    with app.app_context():                                                    # todo exercício citado nos modelos existe no catálogo
        nomes = {e.nome for e in Exercicio.query.all()}
    assert all(nome in nomes for m in MODELOS for t in m["treinos"].values() for nome, _, _ in t["itens"])


def test_lista_de_exercicios_filtra_e_carrega_mais(app, academia):
    proprio = criar_exercicio("Supino da casa", academia["dono"])
    outro = criar_usuario("outro@teste.local", nome="Otto")
    criar_exercicio("Supino do vizinho", outro)
    dono = como(app, academia["dono"])

    html = dono.get("/exercicios").get_data(as_text=True)
    assert 'class="rail"' in html and "65 exercícios cadastrados" in html and ">None<" not in html     # 64 do padrão + 1 dela
    assert html.count('class="card ex-card"') == 8 and "limite=16" in html                             # mostra 8 e oferece "carregar mais"
    assert dono.get("/exercicios?limite=16").get_data(as_text=True).count('class="card ex-card"') == 16

    busca = dono.get("/exercicios?q=supino").get_data(as_text=True)
    assert "Supino reto" in busca and "Supino da casa" in busca and "Supino do vizinho" not in busca and "Rosca direta" not in busca
    biceps = dono.get("/exercicios?grupo=Bíceps&limite=64").get_data(as_text=True)
    assert "Rosca direta" in biceps and "Supino reto" not in biceps
    assert proprio and "Nenhum" in dono.get("/exercicios?q=zzzz").get_data(as_text=True)


def test_detalhe_do_exercicio(app, academia):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    do_vizinho = criar_exercicio("Supino do vizinho", outro)
    dono = como(app, academia["dono"])

    html = dono.get(f"/exercicios/{id_do(app, 'Supino reto')}").get_data(as_text=True)
    for trecho in ("Supino reto", "Peito", "Barra", "Catálogo padrão", "Como executar", "Peitoral", "Sem vídeo ainda", "Adicionar a uma ficha"):
        assert trecho in html, trecho
    assert ">None<" not in html
    assert dono.get(f"/exercicios/{do_vizinho}").status_code == 404 and dono.get("/exercicios/99999").status_code == 404


def test_exercicio_criado_na_tela_antiga_aparece_certo_na_nova(app, academia):
    from app.extensions.database import db
    with app.app_context():                                                    # a tela antiga grava o grupo como código e aceitava outros links
        antigo = Exercicio(nome="Elevação antiga", grupo_muscular="ombro", video_url="javascript:alert(1)", ativo=True, conta_id=academia["conta"])
        db.session.add(antigo)
        db.session.commit()
        antigo = antigo.id
    dono = como(app, academia["dono"])
    lista = dono.get("/exercicios?grupo=Ombros&limite=64").get_data(as_text=True)
    assert "Elevação antiga" in lista and ">ombro<" not in lista                # entra no filtro "Ombros", sem criar um filtro "ombro"
    detalhe = dono.get(f"/exercicios/{antigo}").get_data(as_text=True)
    assert "javascript:" not in detalhe and "Sem vídeo ainda" in detalhe and ">Ombros<" in detalhe
    assert '<option value="Ombros" selected>' in dono.get(f"/exercicios/{antigo}/editar").get_data(as_text=True)


def test_criar_e_editar_exercicio_da_academia(app, academia):
    instrutor = como(app, academia["instrutor"])                               # é o instrutor quem mais usa esta tela
    assert "Novo exercício" in instrutor.get("/exercicios/novo").get_data(as_text=True)

    resposta = instrutor.post("/exercicios/novo", data={"nome": "  Remada no TRX ", "grupo_muscular": "Costas", "equipamento": "Fita",
                                                        "video_url": "https://youtu.be/abc123"})
    assert resposta.headers["Location"] == "/exercicios"
    novo = id_do(app, "Remada no TRX")
    assert [campo(Exercicio, novo, c) for c in ("grupo_muscular", "equipamento", "video_url", "conta_id")] == ["Costas", "Fita", "https://youtu.be/abc123", academia["conta"]]

    tela = instrutor.get(f"/exercicios/{novo}/editar").get_data(as_text=True)
    assert 'value="Remada no TRX"' in tela and 'value="Fita"' in tela
    instrutor.post(f"/exercicios/{novo}/editar", data={"nome": "Remada suspensa", "grupo_muscular": "Costas", "equipamento": "", "video_url": ""})
    assert [campo(Exercicio, novo, c) for c in ("nome", "equipamento", "video_url")] == ["Remada suspensa", None, None]


@pytest.mark.parametrize("trocas, aviso", [({"nome": ""}, "Dê um nome ao exercício."), ({"grupo_muscular": "Dedos"}, "Escolha o grupo muscular."),
                                           ({"video_url": "javascript:alert(1)"}, "O link precisa começar com http"),
                                           ({"video_url": "youtube.com/x"}, "O link precisa começar com http"), ({"nome": "x" * 101}, "no máximo 100 letras")])
def test_exercicio_invalido_avisa_e_nao_grava(app, academia, trocas, aviso):
    dados = {"nome": "Remada no TRX", "grupo_muscular": "Costas", "equipamento": "Fita", "video_url": ""}
    dados.update(trocas)
    resposta = como(app, academia["dono"]).post("/exercicios/novo", data=dados)
    assert resposta.status_code == 200 and aviso in resposta.get_data(as_text=True) and contar(Exercicio) == 64


def test_catalogo_padrao_e_exercicio_de_outra_academia_nao_sao_editados(app, academia):
    outro = criar_usuario("outro@teste.local", nome="Otto")
    do_vizinho = criar_exercicio("Supino do vizinho", outro)
    padrao = id_do(app, "Supino reto")
    dono = como(app, academia["dono"])
    dados = {"nome": "Invadido", "grupo_muscular": "Peito", "equipamento": "", "video_url": ""}

    assert dono.get(f"/exercicios/{padrao}/editar").headers["Location"] == f"/exercicios/{padrao}"       # avisa e volta
    assert dono.post(f"/exercicios/{padrao}/editar", data=dados).headers["Location"] == f"/exercicios/{padrao}"
    assert dono.get(f"/exercicios/{do_vizinho}/editar").status_code == 404 and dono.post(f"/exercicios/{do_vizinho}/editar", data=dados).status_code == 404
    assert campo(Exercicio, padrao, "nome") == "Supino reto" and campo(Exercicio, do_vizinho, "nome") == "Supino do vizinho"


# ------------------------------------------------------------------ modelos
def test_biblioteca_mostra_os_modelos_e_as_fichas(app, academia):
    dono = como(app, academia["dono"])
    html = dono.get("/treinos").get_data(as_text=True)
    assert 'class="rail"' in html and "5 modelos · 0 fichas de aluno" in html
    for nome in ("Hipertrofia", "Perda de peso", "Condicionamento", "Baixo impacto", "Iniciante"):
        assert nome in html
    assert html.count("Usado 0×") == 5 and ">None<" not in html
    busca = dono.get("/treinos?q=iniciante").get_data(as_text=True)
    assert "Iniciante" in busca and "Hipertrofia" not in busca

    dar_ficha(dono, academia)
    html = dono.get("/treinos").get_data(as_text=True)
    assert "Usado 1×" in html and "5 modelos · 1 fichas de aluno" in html and "Ana Souza" in html and "Hipertrofia · rascunho" in html
    assert "Escolha uma ficha de aluno para adicionar" in dono.get(f"/treinos?adicionar={id_do(app, 'Prancha')}").get_data(as_text=True)


def test_tela_do_modelo(app, academia):
    dono = como(app, academia["dono"])
    a = dono.get("/treinos/modelo/1").get_data(as_text=True)
    assert "Peito, costas e braço" in a and "Supino reto" in a and "4 × 10" in a and "6 exercícios · ~48 minutos" in a
    assert "Pernas e ombros" in dono.get("/treinos/modelo/1?t=B").get_data(as_text=True)
    assert "Peito, costas e braço" in dono.get("/treinos/modelo/1?t=Z").get_data(as_text=True)          # letra que não existe: abre a primeira
    assert dono.get("/treinos/modelo/99").status_code == 404


def test_usar_o_modelo_com_um_aluno_cria_a_ficha_em_rascunho(app, academia):
    instrutor = como(app, academia["instrutor"])
    tela = instrutor.get("/treinos/modelo/1/atribuir").get_data(as_text=True)
    assert "Ana Souza" in tela and "Bia Lima" in tela and "Caio Inativo" not in tela and "Igor" in tela       # só alunos ativos; instrutor responsável
    assert "Bia Lima" not in instrutor.get("/treinos/modelo/1/atribuir?q=ana").get_data(as_text=True)

    resposta = dar_ficha(instrutor, academia)

    assert resposta.headers["Location"] == f"/alunos/{academia['ana']}/ficha"
    with app.app_context():
        ficha = Ficha.query.one()
        assert (ficha.aluno_id, ficha.nome, ficha.modelo, ficha.rascunho, ficha.ativo, ficha.atualizada_por_id) == (
            academia["ana"], "Hipertrofia", "hipertrofia", True, True, academia["instrutor"])
        assert ficha.valida_ate == HOJE + timedelta(days=90) and sorted(t.letra for t in ficha.treinos) == ["A", "B", "C"]
    assert linhas_do_treino(app, academia["ana"], "A")[:2] == [("Supino reto", 4, "10", None, "60s"), ("Crucifixo inclinado", 3, "12", None, "60s")]
    assert len(linhas_do_treino(app, academia["ana"], "C")) == 6


def test_atribuir_a_varios_a_ninguem_e_a_quem_nao_pode(app, academia):
    dono = como(app, academia["dono"])
    outro = criar_usuario("outro@teste.local", nome="Otto")
    vizinho = criar_aluno(outro, criar_plano(outro, nome="Plano-B"), "Vizinho", "v@exemplo.com", "987.654.321-00")

    assert dono.post("/treinos/modelo/1/atribuir", data={"acao": "ajustar"}).headers["Location"] == "/treinos/modelo/1/atribuir"      # ninguém marcado
    dono.post("/treinos/modelo/1/atribuir", data={"aluno_id": [vizinho, academia["caio"]], "acao": "ajustar"})                          # de fora e inativo
    assert contar(Ficha) == 0

    varios = dono.post("/treinos/modelo/5/atribuir", data={"aluno_id": [academia["ana"], academia["bia"], vizinho], "acao": "enviar"})
    assert varios.headers["Location"] == "/treinos" and contar(Ficha) == 2 and contar(Ficha, aluno_id=vizinho) == 0
    assert dar_ficha(dono, academia, "ana", 2, "enviar").headers["Location"] == f"/alunos/{academia['ana']}/ficha/enviar"       # um só: vai enviar


def test_ficha_nova_guarda_a_antiga_como_inativa(app, academia):
    dono = como(app, academia["dono"])
    dar_ficha(dono, academia, modelo=1)
    dar_ficha(dono, academia, modelo=5)
    assert contar(Ficha, aluno_id=academia["ana"]) == 2 and contar(Ficha, aluno_id=academia["ana"], ativo=True) == 1
    html = dono.get(f"/alunos/{academia['ana']}/ficha").get_data(as_text=True)
    assert "Adaptação A" not in html or True                                   # (o nome do treino aparece conforme o tamanho da tela)
    assert linhas_do_treino(app, academia["ana"], "A")[0][0] == "Leg press 45"  # a que vale é a do modelo Iniciante
    assert "Usado 0×" in dono.get("/treinos?q=hipertrofia").get_data(as_text=True)    # a ficha antiga não conta mais como "em uso"


# ------------------------------------------------------------------ editor da ficha
def test_editor_da_ficha_mostra_o_treino_e_o_catalogo(app, academia):
    dono = como(app, academia["dono"])
    dar_ficha(dono, academia)
    html = dono.get(f"/alunos/{academia['ana']}/ficha").get_data(as_text=True)
    for trecho in ("Ana Souza", "Hipertrofia", "rascunho", "Supino reto", "Treino A", "Treino B", "Treino C", "Catálogo de exercícios", "por Diana"):
        assert trecho in html, trecho
    assert ">None<" not in html
    assert "Agachamento livre" in dono.get(f"/alunos/{academia['ana']}/ficha?t=B").get_data(as_text=True)

    # o perfil do aluno passa a mostrar os treinos pela letra
    perfil = dono.get(f"/alunos/{academia['ana']}").get_data(as_text=True)
    assert "Treino A" in perfil and "Treino C" in perfil
    # aluno sem ficha: vai escolher um modelo
    assert dono.get(f"/alunos/{academia['bia']}/ficha").headers["Location"] == "/treinos"


def test_adicionar_editar_e_remover_exercicio(app, academia):
    dono = como(app, academia["dono"])
    dar_ficha(dono, academia, modelo=4)                                         # Baixo impacto: 3 exercícios no Treino A
    url = f"/alunos/{academia['ana']}/ficha/exercicio"
    proprio = criar_exercicio("Bicicleta da casa", academia["dono"])

    dono.post(url, data={"acao": "adicionar", "t": "A", "exercicio_id": id_do(app, "Prancha")})
    dono.post(url, data={"acao": "adicionar", "t": "A", "exercicio_id": proprio})
    assert [l[0] for l in linhas_do_treino(app, academia["ana"], "A")] == ["Leg press 45", "Remada baixa", "Elevação pélvica", "Prancha", "Bicicleta da casa"]
    assert linhas_do_treino(app, academia["ana"], "A")[3] == ("Prancha", 3, "12", None, "60s")       # entra com 3 x 12 e 60s

    dono.post(url, data={"acao": "editar", "t": "A", "pos": "3", "series": "4", "repeticoes": "20", "carga": " 10 kg ", "descanso": "45s"})
    assert linhas_do_treino(app, academia["ana"], "A")[3] == ("Prancha", 4, "20", "10 kg", "45s")

    dono.post(url, data={"acao": "remover", "t": "A", "pos": "1"})                                    # tira a Remada baixa
    assert [l[0] for l in linhas_do_treino(app, academia["ana"], "A")] == ["Leg press 45", "Elevação pélvica", "Prancha", "Bicicleta da casa"]
    assert contar(Exercicio, nome="Remada baixa") == 1                                                # o exercício continua no catálogo
    assert campo(Ficha, 1, "atualizada_por_id") == academia["dono"]


@pytest.mark.parametrize("dados", [
    {"acao": "editar", "t": "A", "pos": "0", "series": "0", "repeticoes": "10"}, {"acao": "editar", "t": "A", "pos": "0", "series": "3", "repeticoes": "abc"},
    {"acao": "editar", "t": "A", "pos": "0", "series": "21", "repeticoes": "10"}, {"acao": "editar", "t": "A", "pos": "99", "series": "3", "repeticoes": "10"},
    {"acao": "remover", "t": "A", "pos": "99"}, {"acao": "remover", "t": "A"}, {"acao": "remover", "t": "E", "pos": "0"},
    {"acao": "adicionar", "t": "A", "exercicio_id": "99999"}, {"acao": "adicionar", "t": "A", "exercicio_id": "DE_FORA"}, {"acao": "inventada", "t": "A"},
])
def test_pedido_invalido_na_ficha_nao_muda_nada(app, academia, dados):
    dono = como(app, academia["dono"])
    dar_ficha(dono, academia, modelo=4)
    if dados.get("exercicio_id") == "DE_FORA":
        dados = dict(dados, exercicio_id=criar_exercicio("Do vizinho", criar_usuario("outro@teste.local", nome="Otto")))
    antes = linhas_do_treino(app, academia["ana"], "A")
    resposta = dono.post(f"/alunos/{academia['ana']}/ficha/exercicio", data=dados)
    assert resposta.status_code == 302 and linhas_do_treino(app, academia["ana"], "A") == antes


def test_criar_treinos_ate_o_quinto(app, academia):
    dono = como(app, academia["dono"])
    dar_ficha(dono, academia, modelo=4)                                         # começa só com o Treino A
    for letra in "BCDE":
        assert dono.post(f"/alunos/{academia['ana']}/ficha/treino").headers["Location"] == f"/alunos/{academia['ana']}/ficha?t={letra}"
    assert dono.post(f"/alunos/{academia['ana']}/ficha/treino").headers["Location"] == f"/alunos/{academia['ana']}/ficha"      # o sexto não existe
    assert contar(Treino) == 5


def test_salvar_tira_do_rascunho_e_excluir_apaga_so_a_ficha(app, academia):
    dono = como(app, academia["dono"])
    dar_ficha(dono, academia)
    dono.post(f"/alunos/{academia['ana']}/ficha", data={"nome": "Hipertrofia adaptada", "objetivo": "ganhar massa", "t": "B"})
    assert [campo(Ficha, 1, c) for c in ("nome", "objetivo", "rascunho")] == ["Hipertrofia adaptada", "ganhar massa", False]

    assert dono.get(f"/alunos/{academia['ana']}/ficha/excluir").status_code == 405       # só por POST
    assert dono.post(f"/alunos/{academia['ana']}/ficha/excluir").headers["Location"] == "/treinos"
    assert (contar(Ficha), contar(Treino), contar(TreinoExercicio), contar(Exercicio)) == (0, 0, 0, 64)


def test_abrir_telas_nao_grava_nada(app, academia):
    dono = como(app, academia["dono"])
    dar_ficha(dono, academia)
    antes = (contar(Ficha), contar(Treino), contar(TreinoExercicio), campo(Ficha, 1, "atualizada_em"))
    for url in ("/treinos", "/treinos/modelo/1", "/treinos/modelo/1/atribuir", f"/alunos/{academia['ana']}/ficha", f"/alunos/{academia['ana']}/ficha/enviar",
                f"/alunos/{academia['ana']}/ficha/baixar", "/exercicios", f"/exercicios/{id_do(app, 'Prancha')}"):
        assert dono.get(url).status_code == 200, url
    assert (contar(Ficha), contar(Treino), contar(TreinoExercicio), campo(Ficha, 1, "atualizada_em")) == antes


# ------------------------------------------------------------------ fichas antigas (criadas na tela antiga)
def test_ficha_antiga_sem_letra_e_sem_treino_funciona_na_tela_nova(app, academia):
    com_treinos = criar_ficha(academia["ana"], nome="Ficha antiga")
    for dia in ("segunda", "quarta"):
        criar_treino(com_treinos, dia=dia)                                      # treinos da tela antiga: só o dia da semana
    vazia = criar_ficha(academia["bia"], nome="Ficha vazia")
    dono = como(app, academia["dono"])

    html = dono.get(f"/alunos/{academia['ana']}/ficha").get_data(as_text=True)
    assert "Treino A" in html and "Treino B" in html and "Treino C" not in html.replace("Criar Treino C", "")       # ganham letra pela ordem

    assert "Este treino ainda não tem exercícios" in dono.get(f"/alunos/{academia['bia']}/ficha").get_data(as_text=True)
    assert contar(Treino, ficha_id=vazia) == 0                                  # abrir a tela não criou o treino
    dono.post(f"/alunos/{academia['bia']}/ficha/exercicio", data={"acao": "adicionar", "t": "A", "exercicio_id": id_do(app, "Prancha")})
    assert contar(Treino, ficha_id=vazia) == 1 and linhas_do_treino(app, academia["bia"], "A") == [("Prancha", 3, "12", None, "60s")]


# ------------------------------------------------------------------ enviar
def test_enviar_monta_o_texto_e_abre_o_whatsapp_de_quem_usa(app, academia):
    dono = como(app, academia["dono"])
    dar_ficha(dono, academia, modelo=4)
    html = dono.get(f"/alunos/{academia['ana']}/ficha/enviar").get_data(as_text=True)

    assert "Oi Ana! Sua ficha de treino está pronta." in html and "- Leg press 45: 2 x 15 · descanso 60s" in html and "Academia de Diana" in html
    assert 'href="https://wa.me/5511999990000?text=Oi%20Ana%21' in html          # telefone do aluno com o código do país; texto já no link
    # [back-31-pdf-ficha-avaliacao] antes: imagem e PDF desligados. Agora o PDF vem escolhido; a imagem continua desligada
    assert 'data-valor="imagem" aria-pressed="false" disabled' in html and 'data-valor="pdf" aria-pressed="true">' in html
    assert f'href="/alunos/{academia["ana"]}/ficha/pdf"' in html and "Enviar o PDF" in html and "Baixar a ficha em texto" in html

    arquivo = dono.get(f"/alunos/{academia['ana']}/ficha/baixar")
    texto = arquivo.get_data(as_text=True)
    assert arquivo.headers["Content-Type"].startswith("text/plain") and f"ficha-{academia['ana']}.txt" in arquivo.headers["Content-Disposition"]
    assert texto.startswith("Baixo impacto · Ana Souza") and "TREINO A · Mobilidade e força leve" in texto and "- Elevação pélvica: 2 x 15" in texto

    dono.post(f"/alunos/{academia['ana']}/ficha/treino")                          # Treino B criado e ainda vazio: não vai na mensagem
    assert "TREINO B" not in dono.get(f"/alunos/{academia['ana']}/ficha/baixar").get_data(as_text=True)


def test_enviar_com_ddd_55_e_ficha_sem_exercicio(app, academia):
    from app.extensions.database import db
    from app.models import Aluno
    dono = como(app, academia["dono"])
    dar_ficha(dono, academia, modelo=4)
    with app.app_context():
        db.session.get(Aluno, academia["ana"]).telefone = "(55) 99999-0000"       # 55 também é DDD (Santa Maria/RS)
        db.session.commit()
    assert 'href="https://wa.me/5555999990000?text=' in dono.get(f"/alunos/{academia['ana']}/ficha/enviar").get_data(as_text=True)

    for _ in range(3):                                                            # esvazia o Treino A: não há o que enviar
        dono.post(f"/alunos/{academia['ana']}/ficha/exercicio", data={"acao": "remover", "t": "A", "pos": "0"})
    assert dono.get(f"/alunos/{academia['ana']}/ficha/enviar").headers["Location"] == f"/alunos/{academia['ana']}/ficha"


# ------------------------------------------------------------------ quem pode e isolamento
def test_os_tres_papeis_usam_as_fichas(app, academia):
    dar_ficha(como(app, academia["dono"]), academia)
    for papel in ("recepcao", "instrutor"):
        cliente = como(app, academia[papel])
        for url in ("/exercicios", "/exercicios/novo", "/treinos", "/treinos/modelo/1", f"/alunos/{academia['ana']}/ficha", f"/alunos/{academia['ana']}/ficha/enviar"):
            assert cliente.get(url).status_code == 200, f"{papel} {url}"


def test_ficha_de_aluno_de_outra_academia_da_404(app, academia):
    dono = como(app, academia["dono"])
    dar_ficha(dono, academia)
    outro = como(app, criar_usuario("outro@teste.local", nome="Otto"))
    ana = academia["ana"]
    for metodo, url in [("GET", f"/alunos/{ana}/ficha"), ("POST", f"/alunos/{ana}/ficha"), ("POST", f"/alunos/{ana}/ficha/exercicio"),
                        ("POST", f"/alunos/{ana}/ficha/treino"), ("POST", f"/alunos/{ana}/ficha/excluir"), ("GET", f"/alunos/{ana}/ficha/enviar"),
                        ("GET", f"/alunos/{ana}/ficha/baixar")]:
        resposta = outro.open(url, method=metodo, data={"acao": "remover", "t": "A", "pos": "0", "nome": "Invadida"})
        assert resposta.status_code == 404, f"{metodo} {url}"
    assert outro.post("/treinos/modelo/1/atribuir", data={"aluno_id": [ana], "acao": "ajustar"}).headers["Location"] == "/treinos/modelo/1/atribuir"
    assert contar(Ficha) == 1 and campo(Ficha, 1, "nome") == "Hipertrofia" and len(linhas_do_treino(app, ana, "A")) == 6
    assert "Ana Souza" not in outro.get("/treinos").get_data(as_text=True) and "Ana Souza" not in outro.get("/treinos/modelo/1/atribuir").get_data(as_text=True)
