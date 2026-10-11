---
name: "saas-qa-release"
description: "Use antes de entregar mudança de front de SaaS Flask/Jinja pro deploy na Vercel — varredura de rotas por perfil, diff de HTML, testes Playwright (inclusive toque), console limpo e checklist de entrega."
---

# QA e entrega de front (SaaS Flask + Jinja → Vercel)

"Funciona na minha máquina" não é critério. Critério é: **todas as rotas, todos os perfis,
só mudou o que foi pedido, nenhum erro no console**. Combine com `verification-before-completion`
(não declarar pronto sem evidência) e `playwright` (navegador real).

## 1. Varredura de rotas (rápida, sem navegador)

Test client do Flask, logando em cada perfil (recepção, instrutor, personal) e fazendo GET em todas
as rotas. Falha = status fora de 200/302 ou 302 inesperado.

```python
app = criar_app(); app.testing = True
for ident, senha, perfil in CONTAS:
    c = app.test_client(); c.post('/login', data={'identificador': ident, 'senha': senha, 'perfil': perfil})
    for u in URLS:
        r = c.get(u); assert r.status_code in (200, 302), (perfil, u, r.status_code)
```

## 2. Diff de HTML (prova de "só mexi no que foi pedido")

1. Antes de editar: salvar o HTML de todas as rotas × perfis em `antes.json`.
2. Depois: `depois.json`. Comparar linha a linha.
3. Só podem aparecer diferenças nas páginas do pedido. Diferença em outra página = regressão
   (ou mudança global intencional, ex. novo `<script>` no `base.html` — filtrar essa linha no diff).

Dica Jinja: com `trim_blocks/lstrip_blocks`, blocos `{% if %}` em linha própria não geram saída —
dá pra adicionar opção a macro sem mudar o HTML de quem não usa.

## 3. Playwright — fluxos por perfil

- Celular: 360 e 390 px (`has_touch=True, is_mobile=True`). Desktop: 1440 px.
- Esperar o popup automático (abre com atraso) antes de clicar: `wait_for_timeout(1600)` e fechar.
- Para cada card/link novo: clicar e conferir `page.url` ou `dialog[open]`.
- Layout: medir `getBoundingClientRect()` (ex. cards do mesmo grid com a mesma altura;
  `scrollWidth <= clientWidth` = texto não estoura).
- Texto dentro de SVG: `text_content()` (não `inner_text`).
- Gestos de toque: CDP `Input.dispatchTouchEvent` (ver skill `saas-interacoes-mobile`).
- Sempre: `page.on("pageerror")` e `console` tipo `error` → lista tem que terminar vazia.

## 4. Olhar de verdade

Screenshot das telas alteradas (celular e desktop) e **abrir a imagem**. Número quebrando linha,
botão centralizado errado, balão vazando do card — teste automático não pega.

## 5. Acessibilidade mínima

- Tudo clicável é `<a>` ou `<button>` (nada de `div` clicável sem papel).
- Alvo de toque ≥ 44 px no celular; foco visível; `aria-label` em botão só com ícone.
- `prefers-reduced-motion` respeitado (emular com `reduced_motion="reduce"`).

## 6. Entrega (pasta do Drive → git push → Vercel)

1. Listar só os arquivos alterados/novos (nunca reenviar o que não mudou).
2. Conferir data de modificação no Drive antes de sobrescrever (não pisar em edição do Adauto).
3. Gravar na mesma estrutura de pastas do projeto (`vale-tec-front/...`).
4. Relatório: o que mudou, por quê, como testar, limitações (navegador sem suporte etc.).
5. O Adauto faz o `git push`; a Vercel publica.