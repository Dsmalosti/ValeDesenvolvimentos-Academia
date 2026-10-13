# back-20-producao — preparar o sistema para o servidor de produção

| | |
|---|---|
| **Branch** | `back-20-producao` |
| **Sai de** | `back-19-lgpd` |
| **Data** | 13/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefas** | 3.10 da lista "Tarefas do backend — Diogo" e a checklist final da Fase C |
| **Autorização usada** | A4 (Diogo, 10/10/2026): nome único da variável do banco. **Esta branch mexe em configuração de produção** (regra 4 do `CLAUDE.md`): o Adauto pediu em 12/10/2026 para terminar o que não depende de decisão; cada ponto está na seção "Para decidir", para o Diogo conferir antes do merge |
| **Tem migration** | **Não.** Nenhuma tabela ou coluna muda |
| **Dependência nova** | **Não.** O `ProxyFix` usado aqui já vem dentro do Werkzeug |

## Resumo

Não existe servidor de produção ainda (D4). Esta branch deixa o código pronto para quando existir, e fecha a checklist final de segurança:

1. **Comando `flask banco-novo`**: monta um banco vazio de uma vez. É a resposta ao achado "as migrations antigas não rodam do zero".
2. **`/saude`**: endereço público para a hospedagem perguntar se o app está de pé.
3. **Proxy**: com `PROXIES_NA_FRENTE`, o limite de tentativas enxerga o endereço de cada visitante, e não o do proxy.
4. **Fuso horário**: no servidor (Linux) o sistema assume o horário de Brasília.
5. **Banco em produção**: só vale `DATABASE_URL`; o formato `postgres://` das hospedagens é aceito.
6. **Registros (logs)** com data e origem em produção.
7. **`docs/DEPLOY.md`**: o passo a passo para subir e para atualizar.
8. **Checklist final**: teste "conta A × conta B" em todas as rotas, `pip-audit`, `.env` fora do histórico.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/__init__.py` | Fuso, variável do banco em produção, `postgres://`, proxy, logs e o registro do `/saude`. Cada trecho com o comentário `[back-20-producao]` |
| `app/blueprints/saude.py` | **Novo.** A rota `/saude` |
| `app/cli.py` | Comando novo `banco-novo` |
| `.env.example` | `PROXIES_NA_FRENTE` e a explicação da `TZ` (comentada, com o aviso do Windows) |
| `docs/DEPLOY.md` | **Novo.** Guia de deploy |
| `tests/test_producao.py` | **Novo.** 10 testes |
| `tests/test_isolamento.py` | `/saude` entra na lista de rotas públicas conhecidas |

## Cada mudança: antes, depois e por quê

### 1. `flask banco-novo`

**O achado:** num Postgres vazio, `flask db upgrade` para na segunda migration antiga, `f456ba924031`, com o erro "coluna "repeticoes" não pode ser convertida automaticamente para tipo integer". Conferido num Postgres temporário em 13/10/2026. Nunca apareceu antes porque o banco de cada um já existia quando essa migration foi escrita.

**Antes:** não havia como criar o banco de produção.

**Agora:** `flask banco-novo` cria todas as tabelas a partir do `models.py`, marca o banco na versão mais nova das migrations (`alembic stamp head`) e grava o catálogo padrão de exercícios. Dali em diante cada versão nova entra com `flask db upgrade`, como sempre.

**Por que não consertar a migration antiga:** ela é do Diogo e já rodou no banco dele e no do Adauto. Mexer em migration que já rodou é arriscado e não traz ganho: num banco novo não há dado para migrar.

**Trava:** o comando se recusa a rodar se o banco tiver qualquer tabela. Não há como ele passar por cima de um banco em uso.

### 2. `/saude`

**Antes:** não existia. O monitor da hospedagem teria de bater na tela de login.

**Agora:** `GET /saude` responde `ok` (200) se o app respondeu e o banco aceitou uma consulta (`SELECT 1`), ou `banco fora do ar` (503). Pública, sem cache, e sem nenhum dado: o detalhe do erro do banco **não** vai na resposta (ele traz endereço e usuário do banco).

É a única rota que aceita HTTP sem redirecionar para HTTPS em produção, porque o monitor costuma chamar o app por dentro da rede da hospedagem. Todas as outras continuam redirecionando (há teste).

### 3. Proxy (`PROXIES_NA_FRENTE`)

**Antes:** atrás de um proxy, todo visitante teria o endereço do proxy. Uma pessoa errando a senha 10 vezes bloquearia o login de todos por um minuto (risco anotado na `back-18`).

**Agora:** com `PROXIES_NA_FRENTE=1`, o app lê o endereço de verdade do cabeçalho que o proxy manda (`ProxyFix`, do Werkzeug). Sem a variável nada muda, de propósito: confiar nesse cabeçalho sem ter proxy deixaria qualquer um inventar o próprio endereço e escapar do limite. As duas situações têm teste.

### 4. Fuso horário

**Antes:** o sistema usava o fuso da máquina. Servidor costuma estar em UTC: depois das 21h de Brasília o sistema já estaria no dia seguinte (vencimentos, aniversariantes, fila do dia) e a hora do pagamento sairia com 3 horas a mais.

**Agora:** no servidor (Linux), ao subir, o app assume `America/Sao_Paulo`, a não ser que a variável `TZ` diga outro fuso.

**No Windows nada muda**, e isso foi um defeito que apareceu e foi corrigido durante a branch: a primeira versão definia `TZ` em qualquer sistema. Medido no computador do Adauto: com `TZ=America/Sao_Paulo` o Python no Windows passou a marcar 03:57 quando eram 00:57. O Windows não entende esse formato. Por isso, no Windows, o app não cria a variável e avisa no log se encontrar uma. No `.env.example` a linha `TZ` ficou comentada, com o aviso.

### 5. Variável do banco

- **Só `DATABASE_URL` em produção.** Antes: o nome antigo, `DATABASE_URI`, era aceito em qualquer ambiente (a `back-05` avisava que sairia na branch de produção). Agora ele só é aceito, com aviso, fora de produção.
- **`postgres://` é lido como `postgresql://`.** Antes: o app não subia com o endereço no formato que várias hospedagens entregam, porque o SQLAlchemy 2 não o aceita.

### 6. Logs

**Antes:** sem configuração, só os erros apareciam, sem data. **Agora**, em produção: nível INFO, com data, nível e origem, na saída do processo. Fora de produção nada muda.

## Checklist final de segurança (skill `saas-flask-seguranca`)

| Seção | Resultado | Evidência |
|---|---|---|
| 1. Isolamento entre contas | **OK** | Teste novo `test_a_conta_b_nao_ve_nada_da_conta_a_em_nenhuma_rota`: a conta A tem um registro de cada tipo, todos com uma marca no texto; a conta B pede todas as rotas GET com os ids da A. Nenhuma resposta traz a marca. O mesmo teste prova que enxerga: logada, a conta A vê a marca em mais de 20 rotas. Busca por `query.get(` sem filtro de conta: só as três já conferidas (o usuário da sessão, e `instrutor_service`, chamado depois de a rota conferir a conta) |
| 2. Papéis | **OK** | Varredura das 78 rotas com dono, recepção e instrutor: igual à `back-19`, mais `/saude` |
| 3. Autenticação | **OK** | `back-18`: limite de tentativas, mensagem única, sessão com prazo, `session.clear()` antes de `login_user` |
| 4. Formulários | **OK** | CSRF ligado em tudo, nenhuma rota isenta; nenhum SQL montado com texto; dinheiro em `Numeric` |
| 5. Transporte e cabeçalhos | **OK** | `back-18`; nesta branch, o teste de que só `/saude` aceita HTTP |
| 6. Segredos e dependências | **Atenção** | `git log --all -- .env` vazio. `pip-audit` achou falhas conhecidas em 5 dependências (abaixo) |
| 7. Pagamentos | Não se aplica | PIX é confirmação manual no MVP (decisão de 12/10/2026) |
| 8. Uploads | Não se aplica | Não há upload; envio limitado a 5 MB |
| 9. LGPD | **OK no código** | `back-19`. Falta o advogado e os dados "a definir" |

### `pip-audit` (13/10/2026)

Rodado fora do projeto, num ambiente descartável, sobre o `requirements.txt`. **Nenhuma versão foi alterada nesta branch**: mudar o `requirements.txt` pede o OK do Adauto e do Diogo.

| Pacote | Versão | Corrigido em | O que é | Peso para o Vale Tec |
|---|---|---|---|---|
| `Werkzeug` | 3.1.3 | 3.1.9 | Quatro avisos sobre nomes especiais de arquivo do Windows (`CON`, `NUL`) ao servir arquivos | **Baixo.** Só afeta servidor Windows; a produção será Linux. Atinge o computador de quem desenvolve |
| `Flask` | 3.1.2 | 3.1.3 | Em alguns usos da sessão falta o cabeçalho que impede um cache de guardar a página de um usuário logado | **Médio se** houver um cache (CDN) na frente do sistema; baixo sem cache |
| `idna` | 3.11 | 3.15 | Um texto montado de propósito faz a conversão de domínio demorar muito | **Baixo.** Entra pela validação de e-mail, que tem limite de tentativas |
| `Mako` | 1.3.10 | 1.3.12 | Leitura de arquivo fora da pasta, no Windows | **Nenhum.** Só o Alembic usa, com os modelos dele |
| `python-dotenv` | 1.1.1 | 1.2.2 | Funções de gravar no `.env` seguem atalho de arquivo | **Nenhum.** O sistema só lê o `.env` |

**Recomendação:** nenhuma bloqueia o lançamento num servidor Linux, mas são cinco atualizações pequenas (só o último número da versão muda). Vale subir as cinco numa branch própria, rodar a bateria inteira e só então fazer o deploy.

## Como foi testado

- **`pytest`: 512 de 512.** 10 novos em `tests/test_producao.py`: `/saude` (resposta, banco fora do ar sem vazar o erro, HTTP em produção); `banco-novo` (cria, marca na última versão, recusa banco com tabela); `postgres://`; `DATABASE_URL` obrigatória em produção; `SECRET_KEY` obrigatória; fuso; limite de tentativas com e sem proxy; varredura conta A × conta B.
- **Postgres de verdade (temporário, criado e apagado pelo teste; nunca o banco do `.env`):** `flask db upgrade` num banco vazio para em `f456ba924031`; `flask banco-novo` cria 20 tabelas e 64 exercícios, marca `b19a4b5c6d70`, e `flask db check` confirma que o banco bate com o `models.py`.
- **Varredura de rotas por papel:** igual à `back-19`, mais `/saude`. As duas telas antigas com erro conhecido continuam como estavam.
- **Navegador (celular 390 px claro e desktop 1440 px escuro):** as 14 telas, todas as checagens.
- **O que não foi rodado aqui:** o trecho do teste de fuso que vale para Linux (`time.tzset`), porque esta máquina é Windows. No Windows o teste confere o outro lado: que o app não cria a variável e o relógio não muda. Conferir a hora no ensaio geral (está no `DEPLOY.md`).

## Como revisar

```bash
git fetch origin
git diff origin/back-19-lgpd..origin/back-20-producao --stat
git diff origin/back-19-lgpd..origin/back-20-producao -- app/ .env.example
```

Ordem sugerida: `app/__init__.py` (são cinco trechos pequenos, todos comentados), `app/blueprints/saude.py`, o fim de `app/cli.py`, e depois `docs/DEPLOY.md`.

## Para decidir (Adauto e Diogo)

1. **Configuração de produção desta branch.** Conferir se concordam com: horário de Brasília por padrão no servidor; `DATABASE_URI` não valer mais em produção; `/saude` pública e sem HTTPS obrigatório; confiar no cabeçalho do proxy só com `PROXIES_NA_FRENTE` definida.
2. **Atualizar as 5 dependências** apontadas pelo `pip-audit` (tabela acima).
3. **Servidor de aplicação** (Gunicorn, Waitress ou o da hospedagem): é dependência nova e depende da hospedagem (D4).
4. **Hospedagem, domínio e e-mail** (D4, D5, D6): sem eles não há deploy. O `DEPLOY.md` vale para qualquer escolha.
5. **Backup diário guardado por 30 dias**: é o que os termos dizem; liga-se na hospedagem do banco. Testar a restauração antes do primeiro cliente.
6. **Migration antiga `f456ba924031`**: fica como está? Com o `banco-novo` ela não atrapalha mais, mas quem tentar `flask db upgrade` num banco vazio vai dar com o erro. O `DEPLOY.md` avisa.
7. **Tarefa diária da inatividade automática**: não foi feita. A regra continua rodando quando o painel de cada conta abre, uma vez por dia, o que funciona sem agendador. Uma tarefa agendada depende da hospedagem e pediria mexer no filtro de conta dos serviços.

## Riscos

- **O Linux não foi testado aqui.** Tudo foi desenvolvido e testado no Windows. Os pontos que só existem no servidor (fuso, proxy de verdade, HTTPS da hospedagem) têm teste automático onde foi possível e estão na lista do ensaio geral do `DEPLOY.md`.
- **`PROXIES_NA_FRENTE` errada.** Faltando: um usuário errando a senha bloqueia todos por um minuto. Sobrando (maior que o número real de proxies): o visitante consegue inventar o próprio endereço. O `DEPLOY.md` traz o teste das duas redes.
- **`banco-novo` cria as tabelas pelo `models.py`, não pelas migrations.** Se algum dia o `models.py` e as migrations divergirem, o banco novo e os antigos ficam diferentes. Hoje não divergem: `flask db check` confere isso e passou no Postgres temporário.
- **`/saude` é pública.** Responde só `ok`, mas faz uma consulta ao banco a cada chamada e não tem limite de tentativas. É o comum para esse tipo de rota; se virar alvo, dá para limitar.
