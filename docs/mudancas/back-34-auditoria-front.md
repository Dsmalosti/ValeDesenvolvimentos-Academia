# back-34-auditoria-front — skill de auditoria, auditoria do site, otimizações e guia de manutenção do front

| | |
|---|---|
| **Branch** | `back-34-auditoria-front` |
| **Sai de** | `back-33-deploy-render` |
| **Data** | 17/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Pedido** | Adauto, 17/10/2026: otimização e manutenção do front ("deixar imagens leves e ícones leves, site leve, cookies"), com o prompt de auditor sênior de qualidade web, "e faça disso uma skill para projetos futuros e coloque nas skills desse projeto"; "facilitar a manutenção do Frontend" |
| **Tem migration** | Não |
| **Dependência nova** | Não |

## O que mudou

### 1. Skill nova: `auditoria-qualidade-web`

Pasta `.claude/skills/auditoria-qualidade-web/`. É o prompt do Adauto transformado em processo:

| Parte | O que é |
|---|---|
| `SKILL.md` | O papel de auditor; status aprovado/reprovado/não verificado com evidência; gravidade P0 a P3; o fluxo (inventário → medição → inspeção → relatório → correção → medir de novo); como conferir cada uma das 10 áreas do pedido; o modelo de relatório; como combinar com as outras skills do projeto |
| `references/criterios.md` | Números de referência: WCAG 2.2 AA, Core Web Vitals, peso, imagens, vídeo, SEO, GEO, LGPD/cookies, HTTPS; exemplos de reescrita de texto com cara de IA |
| `references/flask-jinja.md` | Receitas para projetos Flask: carimbo de versão, `robots.txt`/`sitemap.xml`, metadados no template-base, compressão, arquivo sem uso |
| `scripts/auditar_paginas.py` | Medição automática com Playwright: peso, requisições, imagens, metadados, cabeçalhos, rolagem lateral, toque, fontes, console, axe-core, `robots.txt`/`sitemap.xml`/HTTPS/certificado. Serve para qualquer site |

A skill entrou na lista de skills do `CLAUDE.md`.

### 2. A auditoria, feita com a skill

`docs/auditorias/2026-10-17-auditoria-local.md`: 31 itens com status, gravidade, evidência e correção.
- Ambiente local: a produção ainda não existe.
- 14 páginas em 4 larguras, num total de 56 combinações.

### 3. O que foi corrigido (achados da auditoria)

| Achado | Antes | Depois | Onde |
|---|---|---|---|
| Tabela rolável dos termos e da política sem foco pelo teclado (axe-core, **gravidade séria**) | 2 violações sérias, e depois 4 moderadas (nomes repetidos) | **0 violações** em 56 combinações | `app/services/legal_service.py`: `tabindex="0"`, `role="region"`, nome único |
| Telas de acesso sem link para a política (LGPD) | Entrar, Esqueci a senha, Convite e Nova senha pediam e-mail e senha sem o link | Rodapé "Termos de uso · Privacidade", com 44 px de toque | `auth/login.html`, `esqueci_senha.html`, `convite.html`, `nova_senha.html` e `app.css` |
| Estáticos sem cache | CSS e JS baixados de novo a cada tela (280 a 445 KB por tela, sem compressão) | Cache de 1 ano, com `?v=<carimbo>` que muda quando o arquivo muda; fontes sem carimbo, para o pré-carregamento bater com o CSS; cache desligado no modo de desenvolvimento | `app/helpers/estaticos.py` (novo) e `app/__init__.py` |
| Sem `robots.txt` e `sitemap.xml` | 404 | 200; o sitemap lista as 4 páginas públicas | `app/blueprints/seo.py` (novo) |
| Páginas públicas sem descrição, canonical, Open Graph e dados estruturados | Faltava tudo; títulos com 17 a 34 caracteres | Login e criar conta com títulos de 57 a 59 caracteres; descrições de 147 a 151 nas 4; canonical; Open Graph; JSON-LD `Organization` + `SoftwareApplication` (com os preços) no login | `app/blueprints/seo.py` e `app/templates/base_auth.html` |
| Telas internas sem "não indexar" | Nada impedia o Google de indexar um link de tela interna publicado por alguém | `X-Robots-Tag: noindex, nofollow` em toda tela que não é pública (inclui convite, nova senha e PDFs) | `app/blueprints/seo.py` |
| Buscadores com IA | Nada | `/llms.txt` com os fatos: o que é, para quem, o que faz, preços, promoção, empresa, links | `app/blueprints/seo.py` |

### 4. Guia de manutenção do front

`docs/MANUTENCAO-FRONT.md`:
- onde fica cada coisa;
- como uma tela é montada;
- a tabela dos comportamentos prontos por atributo `data-*`;
- o passo a passo de uma tela nova;
- o cache com carimbo;
- o que conferir antes de mandar;
- o orçamento de peso, com os números medidos.

## O que ficou de fora, de propósito

| Item | Por quê | Onde está anotado |
|---|---|---|
| Compressão (gzip/brotli) no app | O Render comprime todas as respostas, segundo a equipe dele. Comprimir no app seria trabalho dobrado, ou uma dependência nova | Auditoria 2.5: conferir com `curl` no deploy |
| Cortar o `bootstrap.custom.min.css` (as telas usam 8,4% dele) | Vem do Drive; cortar pede comparação visual de todas as telas e estados. Com compressão e cache, o ganho é de uns 11 KB uma vez | Auditoria 2.7 e `MANUTENCAO-FRONT.md` §7 |
| Alvos de toque pequenos em listas (frequência, mensagens, painel) e fontes de 10 a 11 px | São do desenho do Drive; mexem no visual de várias telas | Auditoria 1.3 e 1.4 |
| 9 ícones SVG antigos sem uso (`static/imagens/`) | São arquivos do Diogo (regra 4) | Auditoria 3.2 |
| `og:image`, imagens reais, GEO completo | Dependem da página de vendas, que vem depois dos testes | Auditoria 5.1, 7.5 e 8.1 |

## Como foi testado

- `pytest` inteiro: **567 passaram**. `tests/test_seo.py` é novo (11 testes):
  - `robots.txt`, `sitemap.xml` (todas as URLs respondem 200) e `llms.txt`;
  - título, descrição, canonical e JSON-LD do login, com os preços;
  - descrições das 4 públicas, no tamanho certo e diferentes entre si;
  - `noindex` nas internas e nos links de senha;
  - carimbo e cache de 1 ano nos estáticos;
  - fontes sem carimbo;
  - cache desligado no desenvolvimento;
  - foco e nome único nas tabelas legais;
  - links dos termos e da privacidade nas telas de acesso.
- Os dois testes de proteção foram ajustados, sem afrouxar o resto:
  - `test_isolamento.py`: as 3 rotas novas são públicas de propósito;
  - `test_seguranca.py`: o JSON-LD é bloco de dados, como o `application/json` que o front já usava.
- Os 16 testes de navegador passaram (celular 360 e 390 px, desktop 1440 px, temas claro e escuro). Login, LGPD e equipe rodaram de novo depois do rodapé.
- Auditoria antes e depois com o script da skill: 0 violações no axe-core, 0 erros no console, 0 rolagem lateral, 0 falhas de rede.

## Como revisar

```bash
git fetch origin
git diff origin/back-33-deploy-render..origin/back-34-auditoria-front --stat
git diff origin/back-33-deploy-render..origin/back-34-auditoria-front -- app/
```

## Riscos

- **Cache de 1 ano:** um arquivo estático chamado **sem** o `url_for` não ganha carimbo e pode ficar velho no navegador por até 1 ano. É o caso dos ícones citados no `manifest.webmanifest` e das fontes do CSS. Para trocar uma fonte ou um ícone desses, mude o **nome do arquivo** (`MANUTENCAO-FRONT.md`, §5).
- **`noindex` em toda tela não pública:** se um dia existir uma página pública nova (ex.: a de vendas), ela precisa entrar em `PUBLICAS`, no `app/blueprints/seo.py`, senão o Google não a mostra.
- **Títulos do login e de criar conta ficaram mais longos** (aparecem na aba do navegador): "Entrar · Vale Tec — gestão de academias e personal trainers".
