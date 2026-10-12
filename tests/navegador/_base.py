"""
Ajudantes dos testes de navegador (tests/navegador/*_navegador.py).

Só funções: quem define o banco descartável e sobe o app é cada teste, antes de importar isto.
"""
from datetime import datetime


CENARIOS = [
    ("celular-390-claro", dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2), "light"),
    ("desktop-1440-escuro", dict(viewport={"width": 1440, "height": 900}), "dark"),
]


def abrir_pagina(navegador, opcoes, tema):
    """Abre uma página no cenário dado. Devolve (contexto, página, erros do console, respostas 4xx/5xx)."""
    contexto = navegador.new_context(color_scheme=tema, **opcoes)
    pagina = contexto.new_page()
    erros, falhas_rede = [], []
    pagina.on("pageerror", lambda e: erros.append(str(e)))
    pagina.on("console", lambda m: m.type == "error" and erros.append(m.text))
    pagina.on("response", lambda r: r.status >= 400 and falhas_rede.append(f"{r.status} {r.url}"))
    return contexto, pagina, erros, falhas_rede


def entrar(pagina, base, email, senha, celular):
    """Faz o login pela tela e fecha o popup de avisos do painel, se ele abrir."""
    acionar = pagina.tap if celular else pagina.click
    pagina.goto(base + "/")
    pagina.wait_for_selector("#dlg-perfil[open]", timeout=5000)
    acionar('#dlg-perfil [data-valor="recepcao"]')
    pagina.wait_for_timeout(400)
    pagina.fill("#f-identificador", email)
    pagina.fill("#f-senha", senha)
    acionar("button[type=submit]")
    pagina.wait_for_url(base + "/", timeout=8000)
    try:
        pagina.wait_for_selector("#pop-avisos[open]", timeout=3500)
        acionar("#pop-avisos [data-close]")
        pagina.wait_for_timeout(400)
    except Exception:
        pass


def conferir_console_e_rede(checa, nome, erros, falhas_rede):
    """As duas checagens que todo teste de navegador termina fazendo."""
    esperadas = [f for f in falhas_rede if not f.endswith("/favicon.ico")]
    checa(f"[{nome}] nenhum arquivo 404/500", not esperadas, esperadas[:5])
    # ao ir de uma tela nova para uma antiga o Chromium cancela a animação de troca de página e avisa: é esperado
    de_verdade = [e for e in erros if "Transition was aborted" not in e and "Transition was skipped" not in e]
    checa(f"[{nome}] console sem erro", not de_verdade, de_verdade[:3])


def sem_none_nem_rolagem(pagina, seletor="#conteudo"):
    """A tela não mostra "None" e não tem rolagem lateral."""
    return ("None" not in pagina.inner_text(seletor)
            and pagina.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))


def pagamento_recebido(db, aluno, quem, valor, pago_em, vence_em, forma="pix"):
    """
    Semeia um pagamento já recebido de `aluno`: a cobrança paga (do plano atual dele, cobrindo de
    `pago_em` até `vence_em`) e o pagamento que a quitou, confirmado por `quem`. Não dá commit.
    """
    from app.models import Cobranca, Pagamento
    cobranca = Cobranca(conta_id=aluno.conta_id, aluno_id=aluno.id, plano_id=aluno.plano_id, tipo="renovacao", valor=valor,
                        data_inicio=pago_em, data_vencimento=vence_em, status="paga", instrutor_id=quem.id)
    db.session.add(cobranca)
    db.session.flush()
    db.session.add(Pagamento(conta_id=aluno.conta_id, cobranca_id=cobranca.id, forma=forma, valor_pago=valor,
                             data_pagamento=datetime(pago_em.year, pago_em.month, pago_em.day, 12, 0),
                             origem_confirmacao="manual", confirmado_por_instrutor_id=quem.id))
    return cobranca
