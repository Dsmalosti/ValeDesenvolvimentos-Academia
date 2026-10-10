---
name: "saas-interacoes-mobile"
description: "Use ao criar ou revisar interações de app em SaaS web (Flask/Jinja ou HTML puro) — deslizar entre páginas, arrastar pra fechar popup, transição entre páginas, linha/card clicável, feedback de toque."
---

# Interações de app em SaaS web (padrão Vale Tec)

Objetivo: o sistema web parecer app nativo (Instagram/WhatsApp) sem framework, só com
`data-*` no HTML + um JS de melhoria progressiva. Se o JS falhar, tudo continua funcionando.

Arquivos de referência no projeto: `static/js/interacoes.js`, `static/css/app.css` seção 9,
`templates/base.html` (script no `<head>`).

## 1. Regra de ouro: quem decide o que é clicável é o HTML

| Quer que... | Use | Por quê |
|---|---|---|
| card/KPI leve a outra tela | `<a class="card kpi" href>` | link de verdade: abrir em nova aba, leitor de tela |
| card abra popup | `<button data-open="id">` | botão = ação na mesma tela |
| linha de lista inteira clicável | `stretched-link` no nome (`::after` cobre o `li` com `position:relative`) | sem JS, continua `<a>` |
| linha de tabela clicável | `<tr data-href>` + nome como `<a>` dentro | `position:relative` em `tr` é instável; JS ignora clique em `a/button` internos |
| gráfico clicável | opção `link` no `data-json` + link "Ver …" no cabeçalho do card | gráfico não é acessível por teclado; o link do cabeçalho é |

Nunca: `div onclick`, ícone de olho só pra "ver" quando a linha inteira pode ser o link.

## 2. Gestos (celular, `max-width: 991.98px`, só toque)

- **Trava de direção**: só vira gesto depois de 10 px e se `|dx| > |dy| * 1.4`. Senão é rolagem — solte.
- **Exclusões**: `input, textarea, select, dialog, .chart, .stackbar, [data-no-swipe]` e qualquer
  ancestral com `overflow-x: auto|scroll` que realmente rola (`scrollWidth > clientWidth`).
- **Borda da tela** (24 px): no navegador é do gesto nativo de voltar do iOS/Android. Só use a borda
  quando instalado (`display-mode: standalone`).
- **Limiar**: distância ≥ 80 px **ou** peteleco: velocidade > 0,4 px/ms com ≥ 30 px.
  Velocidade = últimas 5 amostras; se o dedo parou > 80 ms antes de soltar, velocidade = 0.
- **Feedback durante o arraste**: elemento segue o dedo 1:1 (sem `transition`), lado errado com
  resistência (× 0,15–0,2); indicador muda de estado ao atingir o limiar + `navigator.vibrate(6)`.
- **Destino**: tela com botão voltar → deslizar → volta. Tela de aba → ← próxima aba, → anterior.
- `touchmove` com `{passive:false}` e `preventDefault()` **só depois** da trava horizontal.

### Popup (bottom sheet) e gaveta
- Arraste começa na alça/cabeçalho (`touch-action:none`) ou no corpo **se** `scrollTop === 0`.
- Fecha com 30 % da altura ou peteleco; senão volta com `transform 280ms var(--ease-out)`.
- Saída na velocidade do dedo: `dur = clamp(140, resto / (vel*1.6), 260)`.
- Fundo acompanha: variável `--fundo` no `<dialog>` → `::backdrop{opacity:var(--fundo,1)}`.
- Popup obrigatório (`data-obrigatorio`) nunca arrasta.
- Use `transform` no arraste; a animação de abrir usa `translate` — as duas propriedades somam sem brigar.

## 3. Transição entre páginas (View Transitions entre documentos)

```css
@view-transition{navigation:auto;}
.tabbar{view-transition-name:tabbar;}        /* fica parada; só o conteúdo desliza */
html:active-view-transition-type(forward)::view-transition-new(root){animation:entra-dir 300ms var(--ease-out) both;}
html:active-view-transition-type(back)::view-transition-new(root){animation:entra-esq 300ms var(--ease-out) both;}
@media (prefers-reduced-motion:reduce){@view-transition{navigation:none;}}
```

- O ouvinte `pagereveal` precisa existir antes do 1º quadro → script no `<head>` **sem defer**;
  o resto do JS roda no `DOMContentLoaded`.
- Decida a direção na página **antiga** (clique na aba, botão voltar, gesto) e grave em
  `sessionStorage('vt-dir')`; a nova só lê. Fallback: `navigation.activation` (traverse → compara índices).
- `reload` → `skipTransition()`. Desktop → só `fade` curto (120–180 ms).
- Suporte: Chrome/Edge 126+, Safari 18.2+. Firefox navega normal (melhoria progressiva).

## 4. Movimento (resumo das skills design-motion + emil-design-eng)

- Só `transform`/`opacity`/`filter`. Nunca animar `width/height/top`.
- Entrada 220–320 ms `cubic-bezier(.16,1,.3,1)`; saída mais curta (120–200 ms, `ease-in`).
- Frequência: o que o usuário vê 50×/dia (painel abrindo, números) **não anima**.
- `:active{transform:scale(.94–.98)}` em tudo que é tocável; `-webkit-tap-highlight-color:transparent`.
- `prefers-reduced-motion`: sem deslocamento; a ação acontece direto.
- Vibração: só Android (`navigator.vibrate`), 6–10 ms, nunca em loop. iOS não tem API.

## 5. Como testar (Playwright + CDP)

```python
ctx = b.new_context(viewport={"width":390,"height":844}, has_touch=True, is_mobile=True)
cdp = ctx.new_cdp_session(pg)
cdp.send("Input.dispatchTouchEvent", {"type":"touchStart","touchPoints":[{"x":300,"y":600}]})
for i in range(1,13): cdp.send("Input.dispatchTouchEvent", {"type":"touchMove","touchPoints":[{"x":300-15*i,"y":600}]})
cdp.send("Input.dispatchTouchEvent", {"type":"touchEnd","touchPoints":[]})
```
Casos obrigatórios: swipe longo navega · curto e lento não · peteleco navega · vertical só rola ·
borda (navegador) não · dentro de filtro rolável não · sheet: curto volta, longo fecha, corpo rolado não fecha.
View Transition: `add_init_script` ouvindo `pagereveal` e lendo `e.viewTransition.types`.