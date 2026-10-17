# Critérios e números de referência

Leia a seção da área que estiver auditando. Os números são **referências práticas** (Core Web Vitals do Google, WCAG 2.2 nível AA, boas práticas de mercado), não leis. Quando reprovar por um número, cite o número medido e o de referência.

## Sumário
1. Acessibilidade (WCAG 2.2 AA)
2. Desempenho
3. Imagens e vídeo
4. SEO técnico
5. GEO
6. Privacidade, cookies e LGPD
7. HTTPS e domínio
8. Texto com cara de IA: exemplos de reescrita

## 1. Acessibilidade (WCAG 2.2 AA)

| Critério | Referência | Como medir |
|---|---|---|
| Contraste de texto | 4,5:1 (normal), 3:1 (texto grande ≥ 24 px, ou 18,66 px em negrito) | axe-core `color-contrast` |
| Contraste de componentes (borda de campo, ícone que é botão) | 3:1 | Olhando + ferramenta de contraste |
| Alvo de toque | WCAG 2.2 pede 24×24 px no mínimo; para celular use **44×44 px** | `getBoundingClientRect()` nos `a`, `button`, `input` visíveis |
| Foco visível | Todo elemento focável mostra o foco | Tab pela página e captura de tela |
| Rótulos | Todo `input`, `select` e `textarea` com `<label for>` ou `aria-label` | axe-core `label` |
| Imagens | `alt` descritivo; decorativa com `alt=""` | axe-core `image-alt` |
| Idioma | `<html lang="pt-BR">` | DOM |
| Títulos | Um `h1`, ordem sem pular nível | DOM |
| Movimento | `prefers-reduced-motion: reduce` desliga animações grandes | Emular no Playwright |
| Zoom | 200% sem perder conteúdo | Playwright com `device_scale_factor`, ou CSS `zoom` |

## 2. Desempenho

| Métrica | Bom | Precisa melhorar | Ruim |
|---|---|---|---|
| LCP (maior elemento visível) | ≤ 2,5 s | ≤ 4 s | > 4 s |
| CLS (pulos de layout) | ≤ 0,1 | ≤ 0,25 | > 0,25 |
| INP (resposta ao toque) | ≤ 200 ms | ≤ 500 ms | > 500 ms |
| TTFB (primeiro byte) | ≤ 0,8 s | ≤ 1,8 s | > 1,8 s |
| Peso da primeira visita (celular) | ≤ 1 MB | ≤ 2 MB | > 2 MB |
| Requisições na primeira visita | ≤ 30 | ≤ 60 | > 60 |
| JS (comprimido) | ≤ 200 KB | ≤ 400 KB | > 400 KB |

**Medição local × produção:** em local o tempo é irreal (sem rede). Use os números locais para **peso e quantidade**. Tempo, compressão e cache só valem em produção, ou com o Chromium limitando a rede (Playwright + CDP `Network.emulateNetworkConditions`, "Fast 3G": 1,6 Mbps, 150 ms de latência).

**Compressão:** só um texto de 1 KB ou mais sem `Content-Encoding` reprova. Muitas hospedagens comprimem no proxy; confira em produção antes de mexer no código.

**Cache dos estáticos:** o ideal é `Cache-Control: public, max-age=31536000, immutable` **com** carimbo de versão na URL. Cache longo **sem** carimbo é pior que sem cache: o usuário fica com CSS velho.

## 3. Imagens e vídeo

- WebP com qualidade entre 75 e 85 resolve quase tudo. Foto de destaque (hero) com até 1600 px de largura costuma ficar entre 80 e 200 KB.
- Limite do pedido: **cada imagem abaixo de 300 KB**. Acima disso, reprovar com o tamanho.
- Exceções que **não** reprovam: SVG; favicon (`.ico`, `.png` pequeno); `apple-touch-icon` (PNG 180×180); ícones do manifesto PWA (PNG 192 e 512). Os aparelhos exigem esses formatos.
- **Vídeo:** WebM (VP9) até cerca de 1 a 2 MB para um vídeo curto de fundo, sem áudio, com `poster`. Vídeo longo: use player de terceiro só com consentimento (YouTube grava cookies) ou o modo "youtube-nocookie".

## 4. SEO técnico

- `<title>`: 50 a 60 caracteres, com o nome do produto e o assunto da página. Único por página.
- `meta description`: 120 a 160 caracteres, escrita para gente (é o texto do resultado de busca).
- `canonical` absoluto (`https://dominio/caminho`).
- Open Graph: `og:title`, `og:description`, `og:image` (1200×630, menos de 300 KB), `og:url`, `og:type`.
- `robots.txt`: `User-agent: *`, `Disallow` para áreas privadas, `Sitemap: https://dominio/sitemap.xml`.
- `sitemap.xml`: só URLs públicas, canônicas e que respondem 200.
- Telas atrás de login: `X-Robots-Tag: noindex` ou `<meta name="robots" content="noindex">`. Não basta o `robots.txt`: ele bloqueia o rastreio, mas não a indexação de um link encontrado em outro site.
- JSON-LD: valide a estrutura (tipo, campos obrigatórios); o validador oficial é o "Rich Results Test" do Google, usado em produção.

## 5. GEO (buscadores com IA)

Os buscadores com IA citam páginas que respondem a perguntas com fatos verificáveis. Checklist:
- "O que é" numa frase, no começo da página.
- Para quem é (público concreto: "academias de bairro com 50 a 500 alunos").
- Preço visível, com o que inclui.
- Quem oferece: razão social, CNPJ, cidade, contato. Os mesmos dados em todo lugar.
- FAQ com perguntas reais e respostas de 1 a 3 frases.
- Números com fonte (ex.: "economiza 3 horas por semana", só se medido).
- Datas de atualização visíveis em páginas de conteúdo.
- Dados estruturados repetindo os mesmos fatos.

## 6. Privacidade, cookies e LGPD

- **Política de privacidade:** link no rodapé de toda página e perto de todo formulário. Tem de dizer:
  - quem é o controlador;
  - os dados e as finalidades, com a base legal;
  - com quem compartilha, incluindo fornecedores e se os dados saem do país;
  - o prazo de guarda;
  - os direitos e o canal para pedir;
  - o encarregado, ou a dispensa dele, com o canal.
- **Cookies estritamente necessários** (sessão, CSRF, segurança, preferência de tema): basta informar na política, sem banner.
- **Cookies de análise ou propaganda** (Google Analytics, Meta Pixel, TikTok Pixel, Hotjar): pedem **consentimento antes de gravar**. O banner precisa ter "Recusar" tão fácil quanto "Aceitar". Uma página de vendas com anúncio quase sempre cai aqui.
- **Formulário:** coletar só o necessário. Caixa de aceite de marketing desmarcada.

## 7. HTTPS e domínio

Comandos de conferência em produção:

```bash
curl -sI http://dominio.com.br          # tem de ser 301 para https://
curl -sI https://dominio.com.br         # procurar Strict-Transport-Security e Content-Security-Policy
python - <<'EOF'
import ssl, socket, datetime
h = "dominio.com.br"
c = ssl.create_default_context().wrap_socket(socket.socket(), server_hostname=h)
c.connect((h, 443)); cert = c.getpeercert()
print(cert["subject"], cert["notAfter"])
EOF
```

- HSTS: `max-age` ≥ 15552000 (6 meses). `includeSubDomains` só se **todos** os subdomínios tiverem HTTPS.
- Conteúdo misto: no console do navegador aparece "Mixed Content". O script acusa qualquer requisição `http://` numa página `https://`.

## 8. Texto com cara de IA: exemplos de reescrita

| Genérico | Natural e concreto |
|---|---|
| "Eleve a gestão da sua academia a outro nível com nossa solução completa." | "Cadastre alunos, cobre mensalidades e veja quem está atrasado, tudo no celular." |
| "Desbloqueie todo o potencial do seu negócio 🚀" | "Saiba hoje quem não pagou e mande o lembrete pelo WhatsApp em um toque." |
| "Rápido, seguro e intuitivo." | "Funciona no navegador do celular. Sem instalar nada. Seus dados ficam separados dos de outras academias." |
| "No mundo acelerado de hoje, gerir uma academia é desafiador." | (cortar: começar direto pelo que o produto faz) |
