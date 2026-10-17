# Auditoria de qualidade web — Vale Tec — 17/10/2026

**Como foi feita**

- **Skill:** `auditoria-qualidade-web` (`.claude/skills/auditoria-qualidade-web/`), feita nesta branch a partir do pedido do Adauto.
- **Ambiente:** **local**, a demonstração em `http://127.0.0.1:5002`, com o código de todas as branches até a `back-34`. **A produção ainda não existe:** HTTPS, compressão e tempos de carga ficam "não verificado" até o deploy.
- **Páginas:**
  - públicas: `/login`, `/criar-conta`, `/esqueci-senha`, `/termos`, `/privacidade`;
  - logadas como dono: `/`, `/alunos`, `/planos`, `/frequencia`, `/mensagens`, `/perfil`, `/configuracoes`, `/treinos`, `/assinatura`.
- **Larguras:** 360, 390, 768 e 1440 px. São **56 combinações** de página e largura.
- **Ferramentas:**
  - script `auditar_paginas.py` (Playwright e Chromium);
  - axe-core 4.10.2 para acessibilidade;
  - cobertura de CSS do Chromium;
  - leitura do código e dos cabeçalhos HTTP;
  - a bateria de testes do projeto (566 no `pytest`, 16 testes de navegador).

## Resumo

- **Corrigido nesta branch:**
  - o único erro grave de acessibilidade (a tabela rolável dos termos e da política não recebia foco pelo teclado);
  - a falta de cache nos arquivos estáticos;
  - o SEO técnico inteiro: `robots.txt`, `sitemap.xml`, descrições, canonical, Open Graph, dados estruturados, `noindex` nas telas internas e `llms.txt`;
  - o link da política de privacidade nas telas de entrar e de senha.
- **Depois das correções:** 0 violações no axe-core, 0 erros no console, 0 rolagem lateral e 0 falhas de rede, nas 56 combinações.
- **O que mais pesa e falta:**
  - **não existe página pública de apresentação ou de vendas.** É ela que precisa de imagens reais, texto de venda, `og:image` e conteúdo para buscadores com IA (GEO). Fica para a página de vendas, depois dos testes, como o Adauto pediu;
  - alvos de toque pequenos em listas;
  - fontes de 10 a 11 px, que vêm do desenho do Drive.

## Resultado por item

| # | Item | Status | Gravidade | Evidência | Correção |
|---|---|---|---|---|---|
| 1.1 | Sem rolagem lateral (360 a 1440 px) | **Aprovado** | — | 0 de 56 combinações com `scrollWidth > clientWidth` | — |
| 1.2 | Acessibilidade automática (axe-core) | **Aprovado** depois da correção | — | Antes: 2 violações **sérias** (`scrollable-region-focusable` em `/termos` e `/privacidade`). Depois: 0 violações em 56 combinações | Feito: `tabindex="0"`, `role="region"` e nome único em cada tabela (`legal_service.py`) |
| 1.3 | Alvos de toque de 44 px ou mais (celular) | **Reprovado** | P2 | Nomes de aluno como link com 19 a 20 px de altura em `/frequencia` e `/mensagens`; "Mensal/Anual" com 16 a 18 px e uma barra de 6×30 px no painel. Links dentro do texto dos termos ficam fora da regra (WCAG 2.5.8, exceção de texto corrido) | Aumentar a área de toque no CSS (`padding` ou link cobrindo a linha inteira). É desenho do Drive: decidir junto com a manutenção do front |
| 1.4 | Fonte mínima de 12 px | **Reprovado** | P3 | Textos de 10 a 11,5 px em `/alunos`, painel, `/configuracoes` e `/criar-conta` (etiquetas e legendas dos `tokens.css`) | Subir as etiquetas para 12 px no `tokens.css`, conferindo os cartões |
| 1.5 | `lang`, um `<h1>` visível, rótulos | **Aprovado** | — | `lang="pt-BR"` em todas; 1 `<h1>` visível por tela (o outro, do cabeçalho do celular ou do computador, fica oculto); axe sem `label` | — |
| 1.6 | Tema escuro | **Aprovado** | — | Os 16 testes de navegador rodam o desktop no tema escuro, com fotos conferidas | — |
| 1.7 | Teclado (Tab, foco visível, Esc nos popups) e movimento reduzido | **Não verificado** | — | Esta auditoria não percorreu a página com o teclado | Percorrer login, alunos e um popup com Tab e Esc; emular `prefers-reduced-motion` |
| 2.1 | Peso por tela | **Aprovado** | — | 280 KB (login) a 445 KB (painel), **sem compressão** (o servidor local não comprime) | — |
| 2.2 | Requisições por tela | **Aprovado** | — | 11 a 19 | — |
| 2.3 | JS por tela | **Aprovado** | — | 59 KB (login) a 102 KB (painel), sem compressão | — |
| 2.4 | Cache dos arquivos estáticos | **Aprovado** depois da correção | — | Antes: nenhum estático com `Cache-Control`. Depois: `public, max-age=31536000` com `?v=<carimbo>` na URL (`tests/test_seo.py`) | Feito: `app/helpers/estaticos.py`. Fontes sem carimbo, para o pré-carregamento bater com o CSS |
| 2.5 | Compressão (gzip/brotli) | **Não verificado (local)** | — | O servidor local não comprime. Segundo a equipe do Render (fórum), toda resposta sai comprimida | No deploy: `curl -sI -H "Accept-Encoding: br" https://valesolucoestec.com.br/static/css/app.css` deve mostrar `content-encoding` |
| 2.6 | Fontes | **Aprovado** | — | 7 `woff2` (94 KB), `font-display: swap`, as 2 principais pré-carregadas | — |
| 2.7 | CSS sem uso | **Reprovado** | P3 | As 16 telas usam 8,4% do `bootstrap.custom.min.css` (88 KB) e 39,9% do `app.css` (95 KB) | Cortar o Bootstrap para as regras usadas, com comparação visual de todas as telas e estados. Ganho real de uns 11 KB com compressão |
| 2.8 | LCP, CLS, TTFB | **Não verificado (local)** | — | LCP local de 80 a 344 ms, sem rede: não serve de medida | Em produção, medir no celular em 4G (PageSpeed Insights) |
| 2.9 | Requisições a outros sites | **Aprovado** | — | 0 domínios de fora em todas as telas | — |
| 3.1 | Imagens WebP abaixo de 300 KB | **Aprovado** (não há fotos) | — | Só ícones SVG e favicons PNG (até 15 KB), que são exceções legítimas | Foto nova: WebP, menos de 300 KB, com `width` e `height` |
| 3.2 | Arquivos sem uso | **Reprovado** | P3 | 9 ícones SVG antigos em `static/imagens/` (5 KB, das telas antigas, do Diogo), nunca baixados | Apagar com o OK do Diogo |
| 4.1 | Vídeos WebM | **Aprovado** (não há vídeo) | — | Nenhum `<video>` | — |
| 5.1 | Imagens reais e autênticas | **Não verificado** | — | O sistema não usa fotos; a página de vendas, onde elas importam, ainda não existe | Na página de vendas: capturas de tela reais do sistema e fotos do piloto, com autorização |
| 6.1 | Design próprio | **Aprovado** | — | Identidade consistente (azul-marinho e amarelo, Sora e Plus Jakarta, cartões, ícones próprios), conferida nas capturas | — |
| 6.2 | Texto natural, sem cara de IA | **Aprovado** nas telas | — | Ex.: "Comece em 1 minuto / Sem planilha, sem instalar nada"; descrições novas concretas, sem "eleve/potencialize" | Revisar o texto da página de vendas com a mesma régua |
| 7.1 | `robots.txt` e `sitemap.xml` | **Aprovado** depois da correção | — | Antes: 404 nos dois. Depois: 200; o sitemap lista só as 4 públicas, que respondem 200 | Feito: `app/blueprints/seo.py` |
| 7.2 | Título, descrição e canonical das públicas | **Aprovado** depois da correção | P3 sobrando | Login: título com 59 caracteres e descrição com 150; criar conta: 57 e 147; termos e privacidade com descrições de 150 e 151 e títulos de 24 e 34 (curtos, mas claros) | — |
| 7.3 | Telas internas fora do Google | **Aprovado** depois da correção | — | `X-Robots-Tag: noindex, nofollow` em todas as internas e nos links de convite e de senha | Feito |
| 7.4 | Dados estruturados | **Aprovado** depois da correção | — | JSON-LD `Organization` e `SoftwareApplication` (com os dois preços em BRL) no login | Validar no Rich Results Test do Google depois do deploy |
| 7.5 | Open Graph com imagem | **Reprovado** | P2 | Título, descrição e URL existem; **falta `og:image`** (a prévia do link no WhatsApp sai sem imagem) | Criar com a página de vendas (1200×630, abaixo de 300 KB) |
| 8.1 | GEO (conteúdo para buscadores com IA) | **Reprovado** | P1 para vender | `llms.txt` e JSON-LD com os fatos (o que é, para quem, preço, empresa) já existem, mas **não há página pública** que explique o produto: a porta de entrada é o login | Página de vendas com "o que é", para quem, preço, perguntas frequentes e dados da empresa |
| 9.1 | Política de privacidade onde há coleta | **Aprovado** depois da correção | — | Antes: só "Criar conta" tinha o link; **Entrar, Esqueci a senha, Convite e Nova senha pediam e-mail e senha sem link para a política**. Depois: rodapé com Termos de uso e Privacidade nas cinco. Política 1.0 com fornecedores, transferência internacional, prazos e canal | Feito (rodapé das telas de acesso) |
| 9.2 | Cookies | **Aprovado** | — | Só os necessários (sessão, "lembrar de mim") e o tema guardado no aparelho; nenhum de análise ou propaganda, portanto sem banner | Ao pôr pixel de anúncio (Meta ou Google) na página de vendas: banner de consentimento antes de gravar (seria P0) |
| 10.1 | Domínio próprio, SSL e HTTPS obrigatório | **Aprovado no código, não verificado em produção** | — | Em produção: Talisman com `force_https` e HSTS de 1 ano, cookies `Secure` (testes da `back-18`); domínio `valesolucoestec.com.br` registrado | No deploy: `curl -sI http://valesolucoestec.com.br` deve dar 301 para `https://`, com o `Strict-Transport-Security` presente e o certificado vencendo em mais de 30 dias |

## Correções priorizadas

1. **P1 — Página de vendas pública** (já está na lista do Adauto, depois dos testes). Resolve o GEO (8.1), o `og:image` (7.5) e as imagens reais (5.1).
2. **P2 — Alvos de toque nas listas** (1.3): frequência, mensagens e os rótulos do painel.
3. **P3 — Fontes de 10 a 11 px** (1.4), **corte do Bootstrap** (2.7) e **apagar os 9 SVGs antigos** (3.2, com o OK do Diogo).

## Não verificado e como verificar

- **Em produção, no dia do deploy:**
  - HTTPS, HSTS e certificado (10.1);
  - compressão (2.5);
  - LCP, CLS e TTFB no celular (2.8, PageSpeed Insights);
  - dados estruturados no Rich Results Test (7.4);
  - o `sitemap.xml` com o domínio de verdade.
- **Teclado e movimento reduzido** (1.7): uma passada manual em 3 telas.
- **Como repetir esta auditoria:** `docs/MANUTENCAO-FRONT.md`, seção 6.
