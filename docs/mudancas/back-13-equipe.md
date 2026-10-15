# back-13-equipe — criar conta, convite da equipe e troca de senha

| | |
|---|---|
| **Branch** | `back-13-equipe` |
| **Sai de** | `front-09-equipe` (que só traz os 3 templates, copiados do Drive) |
| **Data** | 12/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefa** | 5.10 da lista "Tarefas do backend — Diogo": criar conta e convite da equipe |
| **Decisões usadas** | D9 (os clientes se cadastram sozinhos); T4 (o cadastro antigo foi fechado na `back-06`; este é o novo) |
| **Tem migration** | **Sim:** `migrations/versions/b13b9c0d1e20_convites_e_troca_de_senha.py`. Cria `convites` e `redefinicoes_senha`. Não altera tabela existente. |
| **Dependência nova** | **Nenhuma.** O envio de e-mail usa a biblioteca padrão do Python. |

## Resumo

É por esta branch que as pessoas passam a entrar no sistema sem ninguém rodar comando no servidor:

- o **dono cria a própria conta** em `/criar-conta` (academia ou personal) e já cai no painel;
- o dono **convida a recepção e os instrutores**: informa e-mail e papel, o sistema gera um link (vale 7 dias, uso único) e a pessoa cria a própria senha;
- o dono **troca o papel** e **remove** alguém da equipe;
- quem **esqueceu a senha** pede um link (vale 1 hora, uso único) e cria uma nova.

**Sobre o e-mail (D6, ainda não decidido):** o sistema já sabe enviar, por qualquer provedor que ofereça SMTP; basta preencher 5 variáveis de ambiente. Enquanto elas não existirem, **nada depende do e-mail**: o convite tem o botão de copiar o link (para mandar pelo WhatsApp) e o suporte gera o link de troca de senha por um comando.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/models.py` | Modelos novos `Convite` e `RedefinicaoSenha`. |
| `migrations/versions/b13b9c0d1e20_convites_e_troca_de_senha.py` | **Novo.** A migration. |
| `app/services/acesso_service.py` | **Novo.** Criar conta, convidar, aceitar convite, trocar papel, remover, pedir e fazer a troca de senha. |
| `app/helpers/email.py` | **Novo.** Envio de e-mail por SMTP, com `smtplib` (biblioteca padrão). |
| `app/blueprints/auth/routes.py` | `criar_conta` e `esqueci_senha` deixam de responder 501; rotas novas `convite` e `nova_senha`. O login e o sair não mudaram. |
| `app/blueprints/config/routes.py` | `config.membro` deixa de só avisar: convidar, trocar papel, remover e cancelar convite. |
| `app/services/config_service.py` | A lista da equipe esconde quem foi removido e mostra os convites em aberto. |
| `app/cli.py` | Comando novo `flask link-de-senha`. |
| `app/templates/auth/nova_senha.html` | **Novo, e não veio do Drive** (ver seção 6). |
| `app/templates/config/index.html`, `app/templates/auth/esqueci_senha.html` | **1 ajuste marcado em cada** (ver seção 6). |
| `.env.example` | **Novo.** Os nomes das variáveis de ambiente, sem valores. |
| `tests/test_equipe.py` | **Novo.** 31 testes. |
| `tests/test_isolamento.py`, `tests/test_configuracoes.py` | As duas telas públicas novas entram na lista de rotas sem login; saiu o teste do aviso "equipe ainda não disponível". |
| `tests/navegador/equipe_navegador.py` | **Novo.** Teste no navegador, com três navegadores separados (dono, convidado, visitante). |

## Cada mudança: antes, depois e por quê

### 1. Rotas

| Endereço | Endpoint | Quem | Antes |
|---|---|---|---|
| `GET, POST /criar-conta` | `auth.criar_conta` | público | respondia 501 |
| `GET, POST /convite/<token>` | `auth.convite` | público, com o link | não existia |
| `GET, POST /esqueci-senha` | `auth.esqueci_senha` | público | respondia 501 |
| `GET, POST /nova-senha/<token>` | `auth.nova_senha` | público, com o link | não existia |
| `POST /configuracoes/equipe` | `config.membro` | só o dono | só avisava "ainda não disponível" |

### 2. Criar conta

Pede o que a tela do front pede: tipo (academia ou personal), nome, e-mail e senha.

- Cria a **conta** e o **usuário dono**, e já deixa a pessoa logada (com sessão nova, como no login).
- O nome da academia nasce como "Academia de *Nome*" e é trocado depois em Configurações. A tela foi desenhada assim, com poucos campos de propósito.
- Academia nasce com o check-in ligado; personal, desligado.
- E-mail que já tem conta: a tela diz só "Esse e-mail já tem conta. Entre ou recupere a senha."
- Senha: de 8 a 72 caracteres. O limite de cima existe porque o bcrypt ignora o que passa de 72; melhor recusar do que cortar calado.

### 3. Convite da equipe

Tabela `convites`, como no documento "Acesso e mensagens": `conta_id`, `email`, `papel`, `token_hash`, `criado_por_id`, `criado_em`, `expira_em`, `usado_em`.

- O código do link tem 256 bits de acaso (`secrets.token_urlsafe(32)`). **O banco guarda só o hash (sha256)** dele: se o banco vazar, os links não vazam junto.
- Vale **7 dias** e **uma vez só**. O uso único é garantido por `usado_em`, gravado na mesma transação que cria o usuário.
- Link que não existe, que venceu ou que já foi usado: a mesma tela "Este convite não vale mais", com 404.
- Só dá para convidar como recepção ou instrutor. Ninguém é convidado como dono.
- Convidar de novo o mesmo e-mail substitui o convite anterior (o link antigo deixa de valer).
- E-mail que já tem acesso ao sistema não pode ser convidado. A mensagem é a mesma para "já é da sua equipe" e "é de outra academia", para não revelar onde a pessoa tem conta.
- No máximo 20 convites em aberto por conta, para o sistema não servir de disparador de e-mail.

**O botão de copiar o link.** Como o banco só tem o hash, o link completo só existe na hora em que é criado. Ele fica na sessão do dono, e por isso o botão de copiar aparece **para quem acabou de criar o convite, naquele navegador**. Em outro aparelho o convite aparece na lista, sem o botão; o dono cancela e convida de novo se precisar do link.

### 4. Trocar papel e remover

- Vale só para quem é da mesma conta, não é o dono e não é a própria pessoa logada.
- **Remover não apaga o cadastro:** a pessoa fica desativada, some da lista e não consegue mais entrar. O nome dela continua nos pagamentos e nas entradas que confirmou.
- Quem foi removido pode ser convidado de novo: volta com o mesmo cadastro, reativado, com a senha e o papel novos.

### 5. Troca de senha

Tabela `redefinicoes_senha`: `usuario_id`, `token_hash`, `criado_em`, `expira_em`, `usado_em`. Mesmo cuidado do convite: só o hash.

- A tela de pedir o link **responde igual** se a conta existe ou não. Senão ela serviria para descobrir quem tem cadastro.
- O link vale **1 hora** e **uma vez**. Pedir de novo cancela o link anterior.
- Depois de trocar, a pessoa **não entra sozinha**: vai para o login e entra com a senha nova.
- Conta desativada não recebe link.

**Sem e-mail configurado**, a tela diz "Pedido registrado: o envio de e-mail ainda não está ligado; peça o link a quem administra a sua conta ou ao suporte", em vez de afirmar que enviou. O suporte gera o link com:

```bash
flask link-de-senha --email pessoa@exemplo.com
```

### 6. Templates

**Novo, sem origem no Drive:** `auth/nova_senha.html`. O front tem a tela de pedir o link, mas não a de criar a senha nova, e sem ela a troca de senha não existe. Montei com as mesmas peças de `auth/convite.html` (mesma base, mesmo campo de senha com barra de força). **Adauto: revise o visual e leve para o front.**

**Ajustes marcados com `{# [back-13-equipe] ... #}`:**

1. `config/index.html`: o botão de copiar o link só aparece quando o link existe (ver seção 3).
2. `auth/esqueci_senha.html`: "Link enviado" só aparece se o envio de e-mail estiver configurado.

### 7. E-mail

`app/helpers/email.py` envia texto simples por SMTP, sempre com criptografia (STARTTLS). Variáveis (os nomes estão em `.env.example`):

`SMTP_HOST`, `SMTP_PORTA` (padrão 587), `SMTP_USUARIO`, `SMTP_SENHA`, `EMAIL_REMETENTE`

- Sem `SMTP_HOST` e `EMAIL_REMETENTE`, nada é enviado e o sistema segue funcionando.
- Uma falha do provedor **não derruba a tela**: o erro vai para o log, sem o destinatário e sem o texto (o texto traz o link, que é um segredo).
- Nos testes automáticos nunca envia.

Com isso, a decisão D6 (qual provedor) vira só preencher essas variáveis.

## A migration

`b13b9c0d1e20_convites_e_troca_de_senha.py`, depois da `b12a8b9c0d10`. Cria as duas tabelas; não toca em nenhuma existente. O downgrade apaga as duas (convites e pedidos pendentes deixam de valer; usuários já criados continuam).

## Como foi testado

- **`pytest`: 317 de 317** (31 novos em `tests/test_equipe.py`). Criar conta (academia e personal, 5 inválidos, já logado); senha guardada com bcrypt; convite com hash no banco e link só na sessão de quem criou; convidar de novo; 6 convites inválidos; só o dono convida; aceitar o convite (conta e papel certos, já logado); link usado, vencido e inventado (404 em GET e POST); dado inválido não gasta o convite; trocar papel (ninguém vira dono, dono não é rebaixado); remover (não apaga, não entra mais, não some o dono, não mexe em outra academia); reconvidar quem foi removido; cancelar convite (e não cancelar o de outra academia); "esqueci a senha" com resposta idêntica; trocar a senha; link de senha de uso único, vencido e substituído; conta desativada; comando do suporte; e-mail com criptografia e falha do provedor sem derrubar.
- **Migration num Postgres temporário:** 13 checagens.
- **Navegador (Playwright):** equipe **34 de 34** (as outras telas sem mudança: configurações 29 de 29, relatórios 28 de 28, frequência 31 de 31, cobrança 33 de 33, alunos 32 de 32, planos 31 de 31, painel 74 de 74, login 60 de 60), celular e computador, com navegadores separados para o dono, o convidado e um visitante: criar conta pelo link do login, convidar, copiar o link, aceitar, link que não vale duas vezes, trocar papel, remover, removido não entra, pedir e trocar a senha, entrar com a senha nova.
- **Varredura de rotas por papel:** só mudou o que é desta branch.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Como está | Evidência |
|---|---|---|
| Senhas | bcrypt (o que o projeto já usava); mínimo 8, máximo 72 | `test_dono_cria_a_propria_conta_e_ja_entra` |
| Links de acesso | 256 bits de acaso; só o hash no banco; validade curta; uso único | `test_dono_convida_e_o_banco_guarda_so_o_hash_do_link`, `test_link_de_convite_so_vale_uma_vez_e_por_7_dias`, `test_trocar_a_senha_pelo_link` |
| Não revelar quem tem conta | "Esqueci a senha" responde igual; o convite usa a mesma frase para qualquer e-mail já cadastrado | `test_esqueci_a_senha_responde_igual_exista_a_conta_ou_nao`, `test_convite_invalido_nao_e_criado` |
| Sessão | Sessão nova ao criar conta e ao aceitar convite (`session.clear()` antes do login) | `_entrar`, em `auth/routes.py` |
| Isolamento entre academias | O convite leva a conta de quem convidou; papel, remoção e cancelamento passam por `da_conta(...)` | `test_remover_tira_o_acesso_sem_apagar_o_cadastro`, `test_cancelar_convite_e_convite_de_outra_academia` |
| Papéis | Só o dono gerencia a equipe; ninguém se promove a dono | `test_so_o_dono_convida_e_gerencia`, `test_trocar_o_papel` |
| CSRF | Todos os formulários mandam `csrf_token`, inclusive os públicos | — |
| Segredos | `.env.example` só tem os nomes; a senha do SMTP só existe em variável de ambiente; o log de falha de e-mail não traz destinatário nem link | `enviar_email` |

**Pendente, e é P0 para o lançamento:** as quatro telas públicas ainda **não têm limite de tentativas**. Entra na `back-18-seguranca` (Flask-Limiter, já autorizado). Até lá, `/criar-conta` aceita cadastros em série e `/esqueci-senha` pode ser chamada sem limite.

## Como revisar

```bash
git fetch origin
git diff origin/front-09-equipe..origin/back-13-equipe --stat
git diff origin/front-09-equipe..origin/back-13-equipe -- app/ migrations/
```

Ordem sugerida: `models.py` e a migration, `acesso_service.py` (o texto do começo explica os links), `helpers/email.py`, `auth/routes.py` (do comentário "[back-13-equipe]" para baixo), `config/routes.py` (`membro`).

## Para decidir (Adauto e Diogo)

1. **D6, o provedor de e-mail.** Qualquer um com SMTP serve. Sem ele o sistema funciona (link copiado e comando do suporte), mas "esqueci a senha" depende de alguém.
2. **Confirmar o e-mail do dono** depois de criar a conta. O documento de acesso sugere exigir antes de convidar equipe e de ligar o PIX. Não entrou: precisa do e-mail funcionando.

## Riscos

- **Sem limite de tentativas nas telas públicas** até a `back-18` (acima).
- **Trocar a senha não derruba quem já está logado** com aquela conta em outro aparelho. Entra na `back-18`, junto com o prazo de validade da sessão.
- **O link de convite só pode ser copiado por quem o criou, na hora.** É o preço de guardar só o hash.
- **Conta criada sozinha não tem aceite de termos gravado.** Os links "termos de uso" e "política de privacidade" da tela ainda não levam a lugar nenhum: é a `back-19-lgpd`.
- **Quem cria conta "personal"** entra no layout de academia até a variante Personal existir (`back-17`).
- **O instrutor convidado vê "em construção" no painel**: o painel do instrutor ainda não foi ligado.
