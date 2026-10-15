# back-18-seguranca — limite de tentativas, cabeçalhos de segurança e sessão

| | |
|---|---|
| **Branch** | `back-18-seguranca` |
| **Sai de** | `back-17-personal` |
| **Data** | 12/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefas** | 1.6 e 3.7 da lista "Tarefas do backend — Diogo" |
| **Autorização usada** | **A6** (Diogo, 10/10/2026): dependências Flask-Limiter e Flask-Talisman |
| **Tem migration** | **Não.** |
| **Dependência nova** | **Sim, as duas autorizadas:** `Flask-Limiter==4.1.1` e `flask-talisman==1.1.0`. A primeira traz quatro dependências dela: `limits`, `Deprecated`, `ordered-set` e `wrapt`. As seis estão no `requirements.txt`. **Depois do pull: `pip install -r requirements.txt`.** |

## Resumo

Esta branch fecha o que era **P0 para o lançamento** nos documentos anteriores (telas públicas sem limite de tentativas) e os outros itens de segurança que vinham sendo anotados:

1. **Limite de tentativas** no login, em criar conta, em "esqueci a senha" e nos links de convite e de troca de senha.
2. **Cabeçalhos de segurança** em toda resposta, com regra de conteúdo (CSP); **HTTPS obrigatório** em produção.
3. **Sessão com prazo** (12 horas sem uso) e "manter conectado" por 30 dias (era 1 ano).
4. **Trocar a senha derruba as outras sessões**; quem é **removido da equipe perde o acesso na hora**.
5. **O login responde igual** para e-mail que não existe, senha errada e conta desativada.
6. **Sai o popup "Como você vai entrar?"** do login e o botão "Entrar com digital" (que não funcionava).
7. **Limite de 5 MB** para qualquer envio.

**Atenção ao subir:** todo mundo que está logado **vai precisar entrar de novo uma vez** (item 4: o formato do que fica guardado na sessão mudou).

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/extensions/protecao.py` | **Novo.** Liga o limite de tentativas e os cabeçalhos. A regra de conteúdo (CSP) está aqui, comentada linha a linha. |
| `config.py` | Prazo da sessão, cookies, tamanho máximo de envio, onde ficam os contadores, `EM_PRODUCAO`. |
| `app/__init__.py` | Chama `protecao.init_app(app)`. |
| `app/blueprints/auth/routes.py` | Os limites de cada tela pública; sessão com prazo; login sem popup de perfil. |
| `app/blueprints/instrutores/routes.py` | Limite também na tela **antiga** de login (senão ela seria o atalho). |
| `app/services/auth_service.py` | Mensagem única e mesmo trabalho nos três casos de falha. |
| `app/models.py` | `User.get_id`, `User.marca_da_senha` e `load_user`: a sessão só vale com a senha atual e o usuário ativo. |
| `app/helpers/erros.py` | Páginas dos erros 429 e 413. |
| `app/templates/errors/429.html`, `413.html` | **Novos, e não vieram do Drive** (seção 7). |
| `app/templates/auth/login.html` | **3 ajustes marcados** (seção 7). |
| `requirements.txt`, `.env.example` | As dependências; a variável opcional `RATELIMIT_STORAGE_URI`. |
| `tests/test_seguranca.py` | **Novo.** 22 testes. |
| `tests/conftest.py`, `tests/test_login.py` | O ajudante `logar` passa a gravar a sessão no formato novo; o teste de conta desativada confere a mensagem única. |
| `tests/navegador/_base.py` e os testes de login, alunos, planos, cobrança e painel | Deixam de esperar o popup de perfil. |

## Cada mudança: antes, depois e por quê

### 1. Limite de tentativas

Antes: nenhum. Dava para tentar senhas sem parar, criar contas em série e disparar pedidos de troca de senha.

| Tela | Limite (por endereço IP) | O que barra |
|---|---|---|
| `POST /login` | 10 por minuto e 40 por hora | adivinhar senha |
| `POST /login` (segunda regra) | 10 a cada 15 minutos **para o mesmo e-mail**, venha de onde vier | adivinhar a senha de uma conta trocando de IP |
| `POST /criar-conta` | 5 por hora e 20 por dia | criar contas em série |
| `POST /esqueci-senha` | 5 por hora | pedidos de troca de senha em série |
| `/convite/<código>` e `/nova-senha/<código>` | 20 por hora (abrir ou enviar) | chutar códigos |
| `POST /instrutores/login/` (tela antiga) | 10 por minuto e 40 por hora | usar a tela antiga como atalho |

- Só o **envio** conta nas quatro primeiras; abrir a tela é livre.
- Passou do limite: resposta **429**, com a página "Muitas tentativas". Nem a senha certa entra enquanto durar.
- Os números ficam no começo de `auth/routes.py`, com nome (`LIMITE_DO_LOGIN`...). É ali que se ajusta.
- **Onde os contadores ficam:** na memória do processo. Serve para um servidor com um processo. Com mais de um, cada processo conta sozinho; aí é apontar `RATELIMIT_STORAGE_URI` para um Redis (decisão junto com a hospedagem, D4).
- **Nos testes automáticos** o limite fica desligado (centenas de logins saem do mesmo endereço); os testes do próprio limite ligam de volta.

### 2. Cabeçalhos de segurança

Antes: nenhum. Agora toda resposta leva:

| Cabeçalho | O que faz |
|---|---|
| `Content-Security-Policy` | O navegador só carrega script, estilo, imagem e fonte **do próprio sistema**. Um script injetado por alguém não roda. |
| `X-Frame-Options: DENY` e `frame-ancestors 'none'` | Ninguém embute o sistema dentro de outro site para enganar o clique. |
| `X-Content-Type-Options: nosniff` | O navegador não "adivinha" o tipo de um arquivo. |
| `Referrer-Policy` | Ao sair para outro site (o WhatsApp, por exemplo), o endereço interno não vai junto. |
| `Strict-Transport-Security` | **Só em produção:** o navegador passa a usar sempre HTTPS. |

**A regra de conteúdo funciona porque o front novo não tem script nem evento embutido no HTML** (tudo sai de `/static`). Há um teste que varre os templates e falha se alguém acrescentar um `<script>` com código ou um `onclick=`. As exceções da regra, todas explicadas no arquivo:

- `style-src 'unsafe-inline'`: os templates usam o atributo `style="..."` em muitos lugares.
- `cdn.jsdelivr.net`: só as telas **antigas** carregam o Bootstrap de lá. Sai junto com elas.
- `'inline-speculation-rules'`: o `app.js` do front pede ao navegador para ir carregando a próxima página (é o que deixa a troca de tela instantânea). A palavra libera só esse tipo de bloco, que não executa código. **Foi o teste de navegador que achou isso:** sem ela, o console acusava erro em toda tela.

**Em produção** (`FLASK_CONFIG=production`): qualquer acesso por `http://` é mandado para `https://`, e os cookies só viajam por HTTPS. O app reconhece o HTTPS terminado pela hospedagem (cabeçalho `X-Forwarded-Proto`).

### 3. Sessão

| | Antes | Agora |
|---|---|---|
| Sessão comum | valia até fechar o navegador (no celular, quase nunca) | 12 horas sem uso; cada uso renova |
| "Manter conectado" | 365 dias | 30 dias |
| Cookies | `HttpOnly` e `SameSite` só em produção | sempre |

### 4. A sessão cai quando deve

Antes, o cookie guardava só o número do usuário. Dois buracos:

- **Trocar a senha não derrubava ninguém.** Quem tivesse roubado a senha continuava dentro.
- **Quem era removido da equipe continuava usando** o sistema até sair por conta própria.

Agora o cookie guarda `id|marca`, onde a marca é um pedaço do resumo (sha256) da senha guardada. A cada página o sistema confere se a marca bate com a senha **atual** e se o usuário está **ativo**. Mudou a senha, ou foi removido: a sessão deixa de valer na página seguinte, em todos os aparelhos.

A marca não revela a senha nem o hash dela. Não precisou de coluna nova nem de migration.

**Efeito ao subir:** as sessões antigas não têm a marca e deixam de valer. Todos entram de novo uma vez.

### 5. Login: uma resposta só

Antes: "Usuário desativado" aparecia **antes** de a senha ser conferida, o que contava a qualquer pessoa que aquele e-mail tem conta. E, para um e-mail que não existe, a resposta vinha na hora, sem conferir senha nenhuma: dava para descobrir quem tem cadastro medindo o tempo.

Agora os três casos (e-mail inexistente, senha errada, conta desativada) dão **"Usuário ou senha inválidos"**, depois do mesmo trabalho (a senha digitada é sempre conferida, contra a do usuário ou contra uma senha que ninguém tem).

### 6. Tamanho do envio

`MAX_CONTENT_LENGTH` de 5 MB. Acima disso o servidor recusa sem ler, com a página "Arquivo grande demais" (413). Antes não havia limite, e alguns formulários do front têm campo de arquivo.

### 7. Templates

**Novos, sem origem no Drive:** `errors/429.html` e `errors/413.html`, feitos no molde de `errors/403.html` (uma linha de texto cada). **Adauto: revise o texto e leve para o front.**

**`auth/login.html`, 3 ajustes marcados com `{# [back-18-seguranca] ... #}`:**

1. O popup "Como você vai entrar?" só existe com `escolher_perfil` (o servidor manda `False`). O papel vem do banco desde a `back-06`; o popup era do front de exemplo.
2. A etiqueta "Entrando como…" sai junto.
3. O botão "Entrar com digital" só aparece com `oferecer_digital`. Antes ele aparecia em todo aparelho com leitor de digital, e o toque não fazia nada (o servidor não tem essas rotas).

Sem as variáveis, a tela se comporta como no Drive.

## Como foi testado

- **`pytest`: 487 de 487** (22 novos em `tests/test_seguranca.py`): bloqueio por IP e por e-mail; criar conta e pedido de senha; links e tela antiga; sem o limite ligado nada é barrado; mensagem única do login; tela sem popup e sem digital; prazo e proteção do cookie; trocar a senha derruba as sessões (direto no banco e pelo link); removido da equipe perde a sessão; 7 identificações antigas ou forjadas; cabeçalhos em página pública, logada e de erro; nenhum template com script ou evento embutido; produção com HTTPS obrigatório, HSTS e cookie seguro; envio de 6 MB recusado.
- **Navegador (Playwright):** as 13 telas, celular e computador, **com a regra de conteúdo ligada**: cada teste confere o console, então qualquer recurso bloqueado apareceria como erro. Login refeito sem o popup. Resultado: login 48 de 48, painel 78 de 78, alunos 32 de 32, planos 31 de 31, cobrança 33 de 33, frequência 31 de 31, relatórios 28 de 28, configurações 29 de 29, equipe 34 de 34, treinos 79 de 79, avaliações 68 de 68, mensagens 34 de 34, personal 55 de 55.
- **Varredura de rotas por papel**, comparada com a `back-17-personal`: nenhuma rota mudou de resposta.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item da skill | Situação depois desta branch |
|---|---|
| Limite de tentativas nas telas públicas | **Feito** (era P0) |
| Cabeçalhos e CSP | **Feito** |
| HTTPS forçado e HSTS | **Feito**, ligado pela configuração de produção |
| Cookies (`Secure`, `HttpOnly`, `SameSite`) | **Feito** |
| Prazo de sessão | **Feito** |
| Sessão invalidada ao trocar a senha e ao remover acesso | **Feito** |
| Enumeração de contas no login | **Feito** (as telas de criar conta, convite e "esqueci a senha" já respondiam igual desde a `back-13`) |
| Tamanho máximo de envio | **Feito** |
| CSRF | Já existia (Flask-WTF em todo formulário e nas chamadas JSON) |
| Isolamento entre contas e papéis | Já existia, com teste por módulo; a checagem cruzada de todas as rotas fica na checklist final |
| Senhas | bcrypt, mínimo 8 (desde a `back-13`) |
| Segredos | `.env` fora do git; `SECRET_KEY` sem valor padrão (desde a `back-05`) |

**Buscas da skill, rodadas nesta branch** (o que ela manda procurar no código):

- `query.get(` e `get_or_404(` sem filtro de conta: sobraram dois, em `instrutor_service.py` (`editar_instrutor` e `excluir_instrutor`). As duas rotas que os chamam conferem antes que o usuário é da própria conta (`da_conta(User)`), então não há buraco; mas o serviço sozinho não se protege. Vale trocar quando as telas antigas forem revistas.
- `|safe` em dado do usuário: nenhum. Os dois usos são o desenho dos ícones e o QR do PIX, que o servidor gera (e o PIX automático nem está ligado).
- SQL montado com texto: nenhum.
- `.env` no histórico do git: nunca entrou. Segredo com valor padrão no código: nenhum.

**Fica para a checklist final (sem branch):** `pip-audit` nas dependências; conferir que nenhum `.env` entrou no histórico; o teste "conta A × conta B" em todas as rotas de uma vez.

## Como revisar

```bash
git fetch origin
git diff origin/back-17-personal..origin/back-18-seguranca --stat
git diff origin/back-17-personal..origin/back-18-seguranca -- app/ config.py requirements.txt
```

Ordem sugerida: `protecao.py`; `config.py`; `models.py` (`load_user` e `get_id`); `auth_service.py`; `auth/routes.py` (os limites, no começo).

## Para decidir (Adauto e Diogo)

1. **Os números dos limites** (tabela da seção 1). São conservadores; se um cliente real esbarrar, é mudar uma linha.
2. **Onde guardar os contadores em produção** (memória ou Redis). Depende de a hospedagem rodar um ou vários processos (D4).
3. **Prazo da sessão: 12 horas.** Numa recepção que fica o dia todo aberta, é um login por dia. Dá para aumentar.
4. **O logout antigo por GET** (`/instrutores/sair/`) continua existindo com as telas antigas. Some com elas.
5. **`Flask-JWT-Extended`** está no `requirements.txt` desde antes e é iniciado no app, mas nenhuma rota usa. Dá para tirar (é decisão sua, Diogo: é remover dependência).

## Riscos

- **Todos entram de novo uma vez** depois que esta branch for ao ar.
- **Atrás de um proxy mal configurado**, todo mundo teria o mesmo IP e um só usuário errando a senha bloquearia o login de todos por um minuto. Na `back-20` o app passa a ler o IP de verdade do cabeçalho da hospedagem; conferir no ensaio geral.
- **A segunda regra do login (por e-mail)** permite que alguém bloqueie o login de uma conta específica por 15 minutos, errando a senha dela 10 vezes. É a troca usual: sem ela, um ataque distribuído testaria senhas sem limite.
- **CSP em tela antiga:** as telas antigas foram cobertas pela varredura e pelos testes que passam por elas, mas têm menos teste de navegador que as novas. Se alguma depender de algo de fora que não seja o `cdn.jsdelivr.net`, o navegador bloqueia e avisa no console.
