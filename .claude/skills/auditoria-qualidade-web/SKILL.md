---
name: auditoria-qualidade-web
description: Auditoria sênior de qualidade de site ou sistema web, com status aprovado/reprovado/não verificado e evidência para cada item, gravidade e correções priorizadas. Cobre responsividade e acessibilidade (telas, toque, teclado, contraste), desempenho (peso, requisições, cache, compressão, LCP/CLS), imagens WebP abaixo de 300 KB e vídeos WebM, imagens reais que passam confiança, design próprio e texto sem cara de IA, SEO técnico (rastreio, metadados, cabeçalhos, sitemap, dados estruturados), GEO (conteúdo claro para buscadores com IA), política de privacidade e cookies, domínio próprio com SSL e HTTPS obrigatório. Use sempre que o usuário pedir para auditar, revisar, otimizar, "deixar mais leve/rápido", conferir SEO, acessibilidade, LGPD/cookies ou HTTPS de um site, landing page, página de vendas ou SaaS, antes de lançar ou depois de publicar, mesmo que ele não use a palavra "auditoria".
---

# Auditoria de qualidade web

Papel: **auditor sênior**. O trabalho é medir, não opinar. Cada item termina com um de três status:

| Status | Quando usar |
|---|---|
| **Aprovado** | Você viu a evidência (medida, arquivo:linha, cabeçalho HTTP, captura de tela) e ela passa no critério |
| **Reprovado** | Você viu a evidência e ela não passa. Diga quanto falta (ex.: "412 KB, limite 300 KB") |
| **Não verificado** | Não deu para medir: produção ainda não existe, falta acesso, a ferramenta não roda aqui. Diga **o quê** impediu e **como** verificar depois |

**Nunca presuma conformidade.** "O framework já faz isso" não é evidência; o cabeçalho HTTP de resposta é. Na dúvida entre aprovado e não verificado, é não verificado. Um relatório com tudo aprovado sem números é sinal de auditoria mal feita.

## Gravidade

| Nível | Significado | Exemplo |
|---|---|---|
| **P0** | Bloqueia o lançamento ou expõe dado/pessoa | Sem HTTPS; formulário de login sem rótulo para leitor de tela; política de privacidade ausente onde há coleta |
| **P1** | Prejudica muito quem usa ou a busca | Página de 3 MB no celular; imagem de 1,2 MB; sem `<title>` |
| **P2** | Melhora clara, sem urgência | CSS sem compressão; falta `sitemap.xml` |
| **P3** | Acabamento | Descrição com 170 caracteres |

## Fluxo

1. **Inventário.** Liste as páginas públicas (home, vendas, login, cadastro, termos, privacidade) e as internas principais. Leia os templates-base e onde ficam CSS, JS, fontes e imagens. Descubra se existe produção (domínio) ou só ambiente local. A produção é a fonte da verdade para HTTPS, compressão e cache, porque o proxy da hospedagem costuma mudar isso.
2. **Medição automática.** Rode `scripts/auditar_paginas.py` (seção "Script"). Ele mede, por página e por largura de tela, requisições, peso, formatos de imagem, metadados, cabeçalhos, rolagem lateral, alvos de toque, erros no console e acessibilidade com o axe-core. Também confere `robots.txt`, `sitemap.xml`, HTTPS, HSTS e o certificado.
3. **Inspeção humana.** Abra as capturas de tela, de verdade, e leia o texto das páginas. Design, cara de IA e confiança das imagens não se medem por script.
4. **Relatório** no formato da seção "Relatório".
5. **Correções** em ordem de gravidade. Em projeto com regras de branch/PR (ex.: o `CLAUDE.md` do repositório), siga essas regras. Mudança em dependência, configuração de produção ou arquivo de outra pessoa pede autorização antes.
6. **Medir de novo** e mostrar o antes e depois com números.

## O que conferir, e como

Para cada área: o critério, como medir e as armadilhas. Detalhes e números de referência em `references/criterios.md`. Leia quando for auditar a área.

### 1. Layout responsivo e acessibilidade
- **Larguras:** 360, 390, 768 e 1440 px. Nenhuma pode ter rolagem lateral (`scrollWidth <= clientWidth`).
- **Métodos de entrada:**
  - **toque:** alvos com 44 px ou mais;
  - **mouse:** estados de hover não escondem conteúdo;
  - **teclado:** Tab percorre tudo na ordem certa, o foco é visível e popups fecham com Esc e devolvem o foco.
- **Zoom de 200%** sem quebrar. Fonte mínima de 12 px.
- **axe-core:** zero violações `critical` e `serious`. Contraste AA (4,5:1 para texto normal). Todo campo com rótulo, toda imagem com `alt` (vazio se for decorativa), `lang` no `<html>`.
- **Preferências do usuário:** `prefers-reduced-motion` respeitado; tema escuro sem texto ilegível.

### 2. Carregamento rápido e eficiência
- **Peso da primeira visita no celular:** ideal até 1 MB. JS até cerca de 200 KB comprimido.
- **Métricas:**
  - LCP até 2,5 s;
  - CLS até 0,1;
  - TTFB até 0,8 s, medido em produção.
- **Texto comprimido:** HTML, CSS e JS com `Content-Encoding: br` ou `gzip`.
- **Cache:** arquivos estáticos com cache longo e um "carimbo" de versão na URL (`?v=hash`), para a versão nova chegar logo.
- **Fontes:** `woff2`, só os pesos usados, `font-display: swap` e pré-carregamento da fonte principal.
- Nada de terceiros bloqueando a renderização. Cada requisição a outro domínio é custo, risco e LGPD.
- Arquivo ou CSS sem uso é peso morto: procure com `grep` quem referencia cada arquivo de `static/`.

### 3. Imagens: WebP e menos de 300 KB
- **Fotos e ilustrações:** WebP (ou AVIF), **cada arquivo abaixo de 300 KB**, com `width` e `height` (evita CLS), `loading="lazy"` abaixo da dobra e `srcset` quando a imagem muda de tamanho.
- **Exceções legítimas** (não reprovar, mas citar):
  - SVG para ícones e logotipos;
  - PNG ou ICO para favicon, `apple-touch-icon` e ícones do manifesto PWA, porque os aparelhos exigem esses formatos.

### 4. Vídeos: WebM otimizado
- WebM (VP9 ou AV1) com MP4 de reserva para o Safari antigo.
- `poster`, `preload="none"` ou `"metadata"`. Reprodução automática só sem som (`muted playsinline`).
- Sem vídeo no site: o item fica **aprovado (não se aplica)**, dizendo isso.

### 5. Imagens reais, autênticas e relevantes
- Fotos de banco genéricas e imagens geradas por IA derrubam a confiança. Prefira capturas de tela do produto de verdade, fotos reais do negócio e clientes reais com autorização.
- Avalie olhando as imagens, e diga quais trocar e por quê.

### 6. Design distinto e texto natural
- **Design:** identidade própria (cores, tipografia, componentes consistentes), e não um modelo padrão sem personalidade. A skill `frontend-design` ajuda a propor direção.
- **Texto:** frases concretas, com números e o nome das coisas. Marcas de texto genérico gerado por IA, para reprovar e reescrever:
  - "Eleve", "Desbloqueie", "Revolucione", "Potencialize", "solução completa", "no mundo de hoje";
  - tríades de adjetivos e emojis decorativos;
  - travessão em todo parágrafo;
  - promessas vagas sem número.
- Mostre o trecho e uma reescrita.

### 7. SEO técnico
- **`robots.txt`:** existe, aponta o sitemap e não bloqueia o que deve ser achado.
- **`sitemap.xml`:** existe e só tem URLs públicas que respondem 200.
- **Páginas públicas:** cada uma com:
  - `<title>` único (50 a 60 caracteres);
  - `meta description` (120 a 160);
  - `link rel="canonical"`;
  - **um** `<h1>` e cabeçalhos em ordem;
  - Open Graph (título, descrição, imagem).
- **Páginas atrás de login:** `noindex` (cabeçalho `X-Robots-Tag` ou meta).
- **Dados estruturados** JSON-LD válidos para o tipo de página (Organization, SoftwareApplication, Product/Offer, FAQPage, LocalBusiness).
- **Códigos de status certos:** 404 de verdade, 301 nos redirecionamentos.

### 8. SEO para buscadores com IA (GEO)
- O conteúdo responde direto: o que é, para quem, quanto custa, como funciona, quem oferece (razão social, CNPJ, cidade, contato), perguntas frequentes com respostas curtas e factuais.
- Nome, endereço e contato iguais em todo lugar (site, termos, redes, Google Perfil da Empresa).
- Os dados estruturados reforçam os mesmos fatos.
- `llms.txt` é opcional: citar como melhoria, não reprovar sem ele.

### 9. Política de privacidade e cookies
- Toda página que coleta dado (cadastro, contato, login) tem link visível para a política e para os termos.
- A política diz quais dados, para quê, base legal, com quem compartilha (incluindo hospedagem e e-mail, e se saem do país), por quanto tempo e como exercer direitos.
- **Cookies:** liste os que o site grava (DevTools → Application, ou o script).
  - Só os necessários (sessão, CSRF, preferência de tema): basta informar na política.
  - Análise, propaganda ou pixel de anúncio: precisa de banner de consentimento **antes** de gravar.

### 10. Domínio próprio, SSL e HTTPS obrigatório
- Domínio próprio (não `*.onrender.com`, `*.vercel.app` etc. para clientes).
- Certificado válido, com o nome certo e vencendo em mais de 30 dias.
- `http://` responde 301 para `https://`. Uma só forma canônica (com ou sem `www`), e a outra redireciona.
- `Strict-Transport-Security` com `max-age` de pelo menos 6 meses.
- Nenhum conteúdo misto (recurso `http://` numa página `https://`).
- Sem produção no ar: **não verificado**. Diga o que conferir no dia do deploy e audite a configuração no código (ex.: Talisman, `force_https`, cookies `Secure`).

## Script

`scripts/auditar_paginas.py` usa só o Python e o Playwright (com o Chromium dele). O axe-core é carregado do CDN na hora do teste e não fica no projeto.

```bash
python scripts/auditar_paginas.py --base http://127.0.0.1:5000 \
    --paginas / /login /criar-conta /termos /privacidade \
    --internas /alunos /planos --login-url /login --email EMAIL --senha SENHA \
    --saida pasta-do-relatorio
```

- `--internas` (opcional): páginas que pedem login. O script entra pela tela de login com os campos padrão do formulário. Use os seletores com `--campo-email` e `--campo-senha` se forem outros.
- Gera `auditoria.json` (tudo medido), `auditoria.md` (tabelas por página) e capturas de tela por largura.
- **Nunca** passe senha de produção de um cliente: use uma conta de teste.
- Em ambiente local, compressão, cache e HTTPS refletem o servidor de desenvolvimento, não a hospedagem: marque esses itens como "não verificado (local)", a menos que rode contra a produção.

## Relatório

Use sempre esta estrutura, em português simples:

```markdown
# Auditoria de qualidade web — <site> — <data>
Ambiente auditado: <produção URL | local>. Páginas: <lista>. Ferramentas: <script, axe-core x.y, leitura do código>.

## Resumo
<3 a 5 linhas: o que está bom, os P0/P1, o que não deu para verificar>

## Resultado por item
| # | Item | Status | Gravidade | Evidência | Correção |
|---|---|---|---|---|---|
| 1.1 | Sem rolagem lateral em 360–1440 px | Aprovado | — | 0 de 20 páginas×larguras com overflow | — |
| 3.1 | Imagens WebP < 300 KB | Reprovado | P1 | hero.jpg 1,2 MB (static/img/hero.jpg) | Converter para WebP 1600 px, ~180 KB |
...

## Correções priorizadas
1. **P0 —** ...
2. **P1 —** ...

## Não verificado e como verificar
- HTTPS/HSTS: no dia do deploy, `curl -I https://dominio` e conferir ...
```

## Junto com outras skills

| Skill | O que ela cobre |
|---|---|
| `saas-qa-release` | Varredura de rotas por perfil, Playwright no celular e no desktop, console limpo |
| `saas-flask-seguranca` | Cabeçalhos, HTTPS, cookies, CSP e LGPD do lado do servidor |
| `saas-interacoes-mobile` | Gestos, popups, gavetas e transições |
| `frontend-design` | Direção visual quando o design reprova por ser genérico |
| `dataviz` | Gráficos e painéis acessíveis |

Projeto Flask/Jinja: ver `references/flask-jinja.md` (carimbo de versão nos estáticos, `robots.txt` e `sitemap.xml` por rota, bloco de metadados no template-base e `noindex` nas telas internas).
