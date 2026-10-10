# back-01-auth-login — login da tela nova

| | |
|---|---|
| **Branch** | `back-01-auth-login` |
| **Sai de** | `front-01` (front do login, correção do iPhone e configuração do Claude Code), que sai da `main` `9b61934` |
| **Data** | 06/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefas da lista "Tarefas do backend — Diogo"** | 1.1, 1.2, 1.3, 1.4, 1.5 |
| **Fica de fora** | 1.6 (limite de tentativas: depende de lib nova, esperando o ok) e 1.7 (requirements) |

## Resumo

A tela de login nova (`templates/auth/login.html`) passa a funcionar de verdade no backend.
O login antigo (`/instrutores/login/`) **continua funcionando**; nada dele foi apagado.

## Arquivos

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `app/blueprints/auth/__init__.py` | novo | vazio (marca a pasta como pacote Python) |
| `app/blueprints/auth/routes.py` | novo | blueprint `auth`: `login`, `logout`, `esqueci_senha`, `criar_conta` |
| `app/__init__.py` | alterado | +2 linhas: import e `register_blueprint(auth_blueprint)` |
| `app/extensions/admin.py` | alterado | `login_view`: `"instrutores.login"` → `"auth.login"` |
| `app/services/auth_service.py` | alterado | busca o e-mail sem diferenciar maiúscula de minúscula |
| `app/services/instrutor_service.py` | alterado | salva o e-mail em minúsculo no criar e no editar |
| `config.py` | alterado | `ProductionConfig`: cookies `Secure` e `SameSite=Lax` |

Toda linha alterada em arquivo que já existia tem o comentário `[back-01-auth-login]`, explicando o que era antes.

## Cada mudança: antes, depois e por quê

### 1. Blueprint `auth` (novo)

- **Antes:** o login era `instrutores.login` em `/instrutores/login/`, com a tela antiga e o `LoginForm` (campo `email`).
- **Depois:** `auth.login` em `/login`, renderizando `auth/login.html`. Ele lê os campos do form novo: `identificador`, `senha`, `lembrar` e `perfil`.
- **Por quê:** o template novo chama `url_for('auth.login')`, `auth.logout`, `auth.esqueci_senha` e `auth.criar_conta`. Se um endpoint não existe, o Flask dá `BuildError` e a página inteira vira erro 500.
- **Detalhes importantes:**
  - **`perfil` não dá permissão nenhuma.** É só o popup de teste "Como você vai entrar?", que sai na versão final. A permissão vai vir da coluna `papel` (tarefa 3.6).
  - **`lembrar`** agora funciona: `login_user(usuario, remember=lembrar)`. Antes, o login antigo ignorava isso.
  - **`session.clear()` antes do `login_user`** evita *session fixation*.
  - **`?next=`** só é aceito se for caminho do próprio site (`/...`). Isso evita o *open redirect* `?next=https://site-falso`.
  - **O `next` fica guardado na sessão entre o GET e o POST** (chave `login_proximo`). O form do template posta em `url_for('auth.login')`, sem o `?next=`; sem guardar, a pessoa sempre caía no painel depois de entrar, e não na página que tinha pedido. Abrir `/login` sem `?next=` apaga o destino antigo, e ele some junto com o `session.clear()` do login. (Corrigido em 10/10: o teste de 06/10 postava direto em `/login?next=...` e por isso não pegou.)
  - **Já logado** que abre `/login` vai direto para `/`.
  - **`/sair` só por POST.** Por GET, uma `<img src="/sair">` em qualquer site deslogaria o usuário, e o prefetch de links do front também.
  - **Logout:** `session.clear()` vem **antes** do `logout_user()`. Na ordem inversa, o cookie "lembrar de mim" sobrevive e loga a pessoa de volta (o teste pegou isso).
  - **`esqueci_senha` e `criar_conta`** respondem 501 ("em construção"). Elas só existem para os links da tela não quebrarem; as telas de verdade vêm na tarefa 5.10.

### 2. `login_view`

- **Antes:** `login_manager.login_view = "instrutores.login"`.
- **Depois:** `"auth.login"`.
- **Por quê:** quem acessa uma página sem estar logado é mandado para a tela nova.

### 3. E-mail sem diferenciar maiúscula

- **Antes:** `User.query.filter_by(email=email)`. `Ana@ValeTec.com` não achava `ana@valetec.com`.
- **Depois:** `User.query.filter(func.lower(User.email) == email.strip().lower())`.
- **E também:** `InstrutorService` salva `email.strip().lower()` no criar e no editar.
- **Por quê:** o teclado do celular coloca a primeira letra em maiúscula. O cliente digitava a senha certa e via "Usuário ou senha inválidos".
- **Atenção, Diogo:** e-mails que já estão no banco com letra maiúscula **continuam entrando**, porque a comparação é em minúsculo dos dois lados. Se existirem dois cadastros iguais mudando só a maiúscula, o login pega o primeiro. Vale rodar esta consulta para conferir:

  ```sql
  SELECT lower(email), count(*) FROM instrutores GROUP BY lower(email) HAVING count(*) > 1;
  ```

### 4. Cookies de produção

- **Antes:** nada configurado. O cookie de sessão ia sem `Secure` e sem `SameSite`.
- **Depois:** no `ProductionConfig`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE='Lax'`, `REMEMBER_COOKIE_SECURE`, `REMEMBER_COOKIE_HTTPONLY` e `REMEMBER_COOKIE_SAMESITE='Lax'`.
- **Por quê:**
  - `Secure`: o cookie só trafega por HTTPS;
  - `SameSite=Lax`: outro site não usa o cookie do usuário para disparar ações;
  - `HttpOnly`: o JavaScript não lê o cookie.
- **Só em produção:** em desenvolvimento (`http://localhost`) o `Secure` impediria o login, por isso não entrou no `DevelopmentConfig`.
- **Efeito colateral:** com HTTPS, o Flask-WTF também confere o cabeçalho `Referer` no POST. Navegador manda isso sozinho, então não muda nada para o usuário.

## O que NÃO mudou (de propósito)

- **`instrutores.login`, `instrutores.logout` e a tela antiga** continuam iguais. O `cabecalho.html` antigo ainda usa `url_for('instrutores.logout')`. Eles saem na branch que trocar o layout base.
- **`LoginForm`** não é usado pela rota nova, mas ficou no lugar.
- **Nenhuma migration, nenhuma dependência nova.**

## Como foi testado

Harness em `harness-integracao/` (fora do repo): sobe o app com SQLite descartável e 2 usuários (um ativo, um inativo).

- **`teste_login.py`: 113 de 114 checagens passaram.** A única que falha é o limite de tentativas (1.6, fora desta branch).
  - **Servidor:**
    - CSRF obrigatório;
    - senha errada, e-mail inexistente (mesma mensagem dos dois) e usuário inativo;
    - campos vazios, e-mail com espaços e e-mail com maiúscula;
    - "lembrar de mim" ligado e desligado;
    - já logado em `/login`, `next` seguro e `next` para outro site;
    - `GET /sair` dá 405, `POST /sair` desloga, inclusive com o cookie "lembrar de mim";
    - os cookies com `FLASK_CONFIG=production`;
    - os arquivos estáticos e a rota antiga `/instrutores/login/`.
  - **Navegador (Playwright):**
    - celular de 360 e 390 px e desktop de 1440 px, nos temas claro e escuro;
    - popup de perfil, "Trocar", validação, olho da senha, aviso de erro e login certo;
    - uso só pelo teclado;
    - console sem erros e nenhum arquivo dando 404.
- **`smoke_rotas.py`:** GET em todas as rotas sem parâmetro, logado. O resultado é **idêntico** ao da `main`.

### Revalidação em 10/10/2026 (branch reaplicada em cima da `front-01` atual)

A `front-01` ganhou o `CLAUDE.md`, as skills e a correção do iPhone (`ajustes-iphone`), então o commit desta branch foi reaplicado em cima dela e testado de novo, sem o remendo do harness (agora o blueprint `auth` é o do próprio repositório).

- **Servidor (test client, SQLite descartável): 51 de 52 checagens passaram.** A que falha continua sendo o limite de tentativas (1.6, fora desta branch). Entraram checagens novas para o fluxo do navegador (POST em `/login` sem `?next=`), `POST /sair` sem CSRF e `perfil` vazio.
- **Cookies com `FLASK_CONFIG=production`: 7 de 7** (`Secure`, `HttpOnly` e `SameSite=Lax` na sessão e no "lembrar de mim").
- **Smoke de rotas, anônimo e logado, contra a `main`:** os status não mudaram. As únicas diferenças são as esperadas: quem não está logado é mandado para `/login` em vez de `/instrutores/login/`, e existem as três rotas novas.
- **Navegador (o embutido do Claude, não o Playwright):** celular de 375 px e desktop de 1440 px. Pedir uma página sem login, cair na tela nova, errar a senha, acertar e voltar para a página pedida.
- **Não refeito nesta rodada:** os testes de Playwright de 06/10 (toque de verdade, uso só pelo teclado). O Playwright não está instalado nesta máquina.

## Bug antigo encontrado (não é desta branch)

`/instrutores/painel/` dá **500 também na `main`**. O `painel-administrativo.html` chama `url_for('alunos.excluirAlunos')`, mas o endpoint se chama `alunos.excluirAluno` (sem o "s"). Não mexi, porque é tela antiga que vai ser trocada pelo painel novo. Se quiser corrigir antes, é uma letra.

## Como revisar

```bash
git fetch origin
git diff origin/front-01..origin/back-01-auth-login    # só o backend desta branch
```
