# Manutenção do front do Vale Tec — guia rápido

Para quem vai mexer numa tela (o Adauto, depois do lançamento). O objetivo é achar rápido **onde** mexer e **o que conferir** depois.
Escrito na `back-34-auditoria-front` (17/10/2026).

## 1. Onde fica cada coisa

| O quê | Onde | Observação |
|---|---|---|
| Layout das telas com login | `app/templates/base.html` | Menu lateral (`_cabecalho.html`), barra de baixo no celular (`_rodape.html`), gaveta (`_gaveta.html`), avisos (`_notificacao.html`) |
| Layout das telas sem login | `app/templates/base_auth.html` | Entrar, criar conta, esqueci a senha, termos, privacidade, conta bloqueada |
| Peças reutilizáveis | `app/templates/_macros/ui.html` | `avatar`, `chip_status`, `brl`, `campo`, `seletor`, `opcoes`, `kpi`, `vazio`, `paginador`, `dialog_head`, `stackbar`, `origem`, `gauge` |
| Ícones | `app/templates/_macros/icons.html` | `{{ icon('check', 18) }}`. Para um ícone novo, acrescente o desenho SVG (grade 24, traço 1,8) na lista `_ICONS` |
| Cores, fontes e tamanhos | `app/static/css/tokens.css` | Variáveis `--navy`, `--blue`, `--text`... e o tema escuro (`[data-tema="escuro"]` e `prefers-color-scheme`) |
| Componentes (card, botão, tabela, popup) | `app/static/css/app.css` | Use as classes que já existem antes de criar outra |
| Correções do iPhone | `app/static/css/ajustes-iphone.css` e `app/static/js/ajustes-iphone.js` | **Não remover** (ver `Correcao-iPhone-08-10.md`) |
| Comportamentos (popup, máscara, abas, copiar) | `app/static/js/app.js` | Ligados por atributos `data-*` no HTML (seção 3) |
| Gestos e transição entre páginas | `app/static/js/interacoes.js` | Deslizar, arrastar para fechar |
| Gráficos | `app/static/js/charts.js` | `data-chart` com os dados em JSON |
| Tema claro e escuro | `app/static/js/tema.js` | Roda no `<head>`, antes de pintar a tela |
| Enviar PDF pelo celular | `app/static/js/compartilhar-pdf.js` | `data-compartilhar-pdf` |
| O que o Google lê | `app/blueprints/seo.py` | Descrições, `robots.txt`, `sitemap.xml`, `llms.txt`, `noindex` |
| Cache dos arquivos | `app/helpers/estaticos.py` | Carimbo `?v=` automático (seção 5) |

**A fonte do design** é o front do Drive (`vale-tec-front`). Os templates daqui são cópias dele com ajustes marcados.
- `{# [back-NN-...] ... #}` num template = ajuste feito numa branch, que **precisa ir para o Drive** também.
- "ESTE TEMPLATE NÃO VEIO DO DRIVE" no topo = tela que nasceu no repositório: `assinatura/`, `admin/`, `perfil/`, `legal/pagina.html` e outras.
- A lista de cada branch está no `docs/mudancas/<branch>.md`, seção "Para o Drive".
- **Decisão pendente:** escolher uma fonte só (Drive **ou** repositório). Sugestão: o repositório. Ele tem testes, histórico e revisão do Diogo; o Drive passaria a ser só a referência visual antiga.

## 2. Como uma tela é montada

```jinja
{% extends 'base.html' %}
{% from '_macros/icons.html' import icon %}
{% from '_macros/ui.html' import kpi, campo %}
{% set nav_ativo = 'alunos' %}            {# qual item do menu fica aceso #}
{% set pagina_titulo = 'Alunos' %}        {# título no desktop e no celular #}
{% set pagina_sub = '42 ativos' %}        {# subtítulo (opcional) #}
{% set m_voltar = true %}                 {# celular: botão voltar no lugar do menu #}
{% block page_acoes %}...botões do topo no desktop...{% endblock %}
{% block content %}
  <section class="card card--pad">...</section>
{% endblock %}
{% block dialogs %}...popups (<dialog>)...{% endblock %}
{% block scripts %}<script src="{{ url_for('static', filename='js/arquivo.js') }}" defer></script>{% endblock %}
```

- Variáveis que **toda** tela recebe (`app/helpers/contexto.py`): `usuario` (nome, iniciais, papel, perfil), `academia` (nome, modelo, checkin_ativo...) e `csrf_token()`.
- Formulário que envia (POST) sempre leva `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- Avisos depois de salvar: `flash('texto', 'success' | 'error' | 'warning' | 'info')` na rota. Viram toast sozinhos.
- **Nada de `<script>` com código dentro do HTML:** a regra de segurança (CSP) bloqueia. JS novo vai num arquivo em `static/js/`. Dados para o JS vão em `<script type="application/json">` ou em atributos `data-*`.

## 3. Comportamentos prontos (só pôr o atributo)

| Atributo | O que faz |
|---|---|
| `data-open="id"` / `data-close` | Abre ou fecha um `<dialog>` (popup, gaveta) |
| `data-toast="texto"` | Mostra um aviso rápido |
| `data-copiar="texto"` (+ `data-copiar-msg`) | Copia para a área de transferência |
| `data-mask="telefone"` (cpf, cep, dinheiro...) | Máscara de digitação pt-BR |
| `data-validate` no `<form>` | Validação no navegador (o servidor valida de novo) |
| `data-toggle-senha="id"` | Botão do olho de mostrar a senha |
| `data-forca` | Medidor de força da senha |
| `data-opcoes` + `data-alvo` | Botões de escolha única que preenchem um campo escondido |
| `data-controla-forma` + `data-so-forma="pix"` | Mostra só o bloco da opção escolhida |
| `data-tabs` / `data-seg` | Abas segmentadas |
| `data-busca` / `data-filtro-grupo` | Busca e filtro numa lista |
| `data-auto-submit` | Interruptor que salva sozinho |
| `data-carregando` | Botão mostra "carregando" ao enviar |
| `data-voltar` | Volta à página anterior |
| `data-chart` | Gráfico (ver `charts.js`) |
| `data-fit` | Texto numa linha só, encolhendo a letra |
| `data-compartilhar-pdf` | Compartilhar o PDF no celular |

Antes de escrever JS novo, procure no `app.js` (`grep -n "data-" app/static/js/app.js`): quase sempre já existe.

## 4. Fazer uma tela nova, passo a passo

1. **Rota** no blueprint certo (`app/blueprints/<area>/routes.py`), com a regra em `app/services/<area>_service.py`.
   - Dados da conta sempre filtrados pela conta: `da_conta(Modelo)`.
   - Papel conferido no servidor: `papel_requerido(...)`.
2. **Template** em `app/templates/<area>/`, copiando a estrutura da seção 2 e usando as peças de `_macros/ui.html`.
3. **Menu:** item em `_cabecalho.html` (desktop) e em `_gaveta.html` (celular), se for uma tela nova de primeiro nível.
4. **Testes:**
   - `tests/test_<area>.py`: rota, papéis e isolamento entre contas;
   - um teste de navegador em `tests/navegador/<area>_navegador.py`, se tiver interação.
5. **Conferir** (seção 6) e levar o template para o Drive, se o Drive continuar sendo a fonte.

## 5. Cache dos arquivos (CSS, JS, imagens)

- Todo `url_for('static', ...)` sai com `?v=<carimbo>`, que muda quando o arquivo muda. O navegador guarda o arquivo por 1 ano e baixa a versão nova assim que você publica.
- **Não precisa renomear arquivo nem limpar cache.**
- **Exceção, as fontes** (`static/fonts/`): ficam sem carimbo, porque o CSS as chama por caminho relativo. Para trocar uma fonte, mude o **nome do arquivo** (ex.: `sora-latin-700-normal-v2.woff2`) no `tokens.css` e no `base.html`.
- **Rodando no seu computador** (`flask run --debug`), o cache fica desligado: a mudança aparece na hora.

## 6. Conferir antes de mandar (o mínimo)

1. `pytest` da área e o teste de navegador da tela.
2. A tela no celular (390 px, toque) e no computador (1440 px), nos temas claro e escuro: sem rolagem lateral, sem "None", console sem erro (skill `saas-qa-release`).
3. Para mudanças grandes de visual ou de peso: a skill **`auditoria-qualidade-web`** (`.claude/skills/auditoria-qualidade-web/`).
   - Script: `scripts/auditar_paginas.py --base http://127.0.0.1:5000 --paginas /login ... --axe`.
   - Compare peso e acessibilidade com a última auditoria (`docs/auditorias/`).

## 7. Orçamento de peso (para o site continuar leve)

Medido em 17/10/2026, sem compressão. O Render comprime, e o tamanho real na rede é de 3 a 4 vezes menor.

| Item | Hoje | Limite combinado |
|---|---|---|
| CSS por tela | 191 KB (`app.css` 95 KB + Bootstrap 88 KB + outros) | Não passar de 200 KB |
| JS por tela | 59 KB (login) a 102 KB (painel) | Não passar de 150 KB |
| Fontes | 7 arquivos `woff2`, 94 KB no total; cada tela baixa de 2 a 6 | Não acrescentar peso novo sem tirar outro |
| Imagens | Só ícones e favicons (SVG e PNG pequenos) | Foto nova: WebP, menos de 300 KB, com `width` e `height` |

**Oportunidade medida e ainda não feita:** as telas usam **8,4% do `bootstrap.custom.min.css`** (88 KB). Dá para cortar para uns 8 KB.
- Só vale fazer com a comparação de todas as telas e estados (popups, menus abertos) antes e depois, porque o arquivo vem do Drive.
- Com a compressão e o cache de 1 ano, o ganho real é de uns 11 KB na primeira visita.
