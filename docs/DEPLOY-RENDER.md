# Vale Tec no Render — passo a passo do primeiro deploy

Guia para o Diogo (e o Adauto) colocarem o Vale Tec no ar no **Render**, a hospedagem escolhida em 17/10/2026.
Complementa o `docs/DEPLOY.md`, que diz o que o sistema precisa em qualquer hospedagem.
Escrito na `back-33-deploy-render`.

> **Antes de começar, falta uma autorização:** o Render precisa de um servidor de aplicação para rodar o Python em produção.
> A sugestão é o **Gunicorn** (uma linha nova no `requirements.txt`), que ainda espera o OK do Diogo.
> Com o OK, o Claude faz a branch com o Gunicorn e o arquivo `render.yaml` (seção 9). Até lá, este guia serve para conhecer o painel e criar o banco.

**Preços:** confira na página de preços do Render antes de contratar. Os valores abaixo são das comparações de 2026, não da página oficial.

| Peça | Plano sugerido | Custo aproximado por mês |
|---|---|---|
| Servidor do app (Web Service) | Starter | US$ 7 |
| Banco (Postgres) | Basic, o menor pago | a partir de US$ 6 |
| Domínio | já registrado no Registro.br | cerca de R$ 40 por ano |
| E-mail do sistema (Brevo) | grátis (300 e-mails por dia) | R$ 0 |
| Caixas suporte@ e ouvidoria@ (encaminhamento) | grátis | R$ 0 |
| **Total** | | **cerca de US$ 13 a 14 por mês** (uns R$ 75 a 80), mais o domínio |

**Por que não o plano grátis do Render:** o servidor grátis "dorme" depois de um tempo sem uso, e o primeiro acesso demora quase um minuto para acordar. O banco grátis expira depois de 30 dias. Servem para testar, não para cliente.

---

## 1. Criar a conta no Render

1. Entrar em https://render.com e criar a conta **com o login do GitHub do Diogo** (o repositório é dele).
2. Autorizar o Render a ler o repositório `Dsmalosti/ValeDesenvolvimentos-Academia`.
3. Cadastrar o cartão para os planos pagos.

**Região:** use a mesma região para o banco e para o app. Sugestão: **Virginia (US East)**, a mais perto do Brasil entre as que o Render oferece. Os termos de uso já dizem "Estados Unidos".

## 2. Criar o banco (Postgres)

1. No painel: **New → Postgres**.
2. **Name:** `valetec-banco`. **Database:** `valetec`. **Region:** a escolhida acima.
3. **PostgreSQL version:** a mais nova oferecida. O sistema foi testado no 18.
4. **Plan:** o menor pago (não o Free).
5. Criar. Depois de pronto, na página do banco, copiar o **Internal Database URL**. É ele que o app usa. O "External" só serve para backup e manutenção feitos de fora.

> **Nunca** cole essas URLs em conversa, e-mail ou no GitHub: elas têm a senha do banco dentro.

## 3. Criar o servidor do app (Web Service)

1. **New → Web Service** e escolher o repositório.
2. Preencher:

| Campo | Valor |
|---|---|
| Name | `valetec` (vira o endereço provisório `valetec.onrender.com`) |
| Region | a mesma do banco |
| Branch | `main` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn --workers 1 --threads 8 --bind 0.0.0.0:$PORT main:app` (depende do Gunicorn no `requirements.txt`) |
| Instance Type | Starter |
| Health Check Path | `/saude` |
| Pre-Deploy Command | `flask --app main db upgrade` (roda as migrations antes de cada versão nova entrar no ar) |

3. Em **Environment**, cadastrar as variáveis da seção 4.
4. Criar. O primeiro build demora alguns minutos.

## 4. Variáveis de ambiente (no painel do Render, nunca no git)

| Variável | Valor |
|---|---|
| `PYTHON_VERSION` | `3.13.14` (a versão usada nos testes) |
| `FLASK_CONFIG` | `production` |
| `SECRET_KEY` | gerar uma nova: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | o **Internal Database URL** do passo 2 |
| `PROXIES_NA_FRENTE` | `1` |
| `SMTP_HOST` | `smtp-relay.brevo.com` |
| `SMTP_PORTA` | `587` |
| `SMTP_USUARIO` | o "login SMTP" que o Brevo mostra em SMTP & API |
| `SMTP_SENHA` | uma **chave SMTP** criada no Brevo (não é a senha da conta nem a chave de API) |
| `EMAIL_REMETENTE` | `Vale Tec <nao-responda@valesolucoestec.com.br>` |
| `VALE_TEC_SUPORTE_EMAIL` | `suporte@valesolucoestec.com.br` (já é o padrão) |
| `VALE_TEC_PIX_CHAVE` | a chave PIX da conta do MEI, **quando a conta do banco existir**. Sem ela, a tela de assinatura manda o cliente falar com o suporte |
| `VALE_TEC_SUPORTE_WHATSAPP` | `55` + DDD + número, **quando o chip existir**. Vazio = sem botão de WhatsApp |

## 5. Primeira vez: criar as tabelas e os administradores

No painel do serviço, abrir **Shell**, que é um terminal dentro do servidor:

```bash
flask --app main banco-novo
```

Cria todas as tabelas no banco vazio, marca a versão e grava o catálogo padrão de exercícios. Ele só roda em banco vazio: se achar alguma tabela, não mexe em nada.

Depois:

1. O Adauto e o Diogo criam as contas deles pela tela `/criar-conta`, com os e-mails pessoais.
2. No Shell, ligar o painel de administração para os dois:

```bash
flask --app main admin-do-sistema --email adauto.netto2005@gmail.com
flask --app main admin-do-sistema --email dsmalosti@gmail.com
```


## 6. Domínio: valesolucoestec.com.br (DNS no Registro.br)

1. No Render, na página do serviço: **Settings → Custom Domains → Add**. Adicionar `valesolucoestec.com.br` e `www.valesolucoestec.com.br`.
2. No Registro.br: **Meus domínios → valesolucoestec.com.br → DNS → Editar zona**. Criar:

| Tipo | Nome | Valor |
|---|---|---|
| A | (vazio, o próprio domínio) | `216.24.57.1` (o endereço que o Render mostrar; confira na tela dele) |
| CNAME | `www` | `valetec.onrender.com` |

3. **Apagar qualquer registro AAAA** do domínio. O Render pede isso.
4. Voltar ao Render e clicar em **Verify**. Quando o DNS espalhar (de minutos a algumas horas), o Render emite o **certificado HTTPS de graça**.
5. Abrir `https://valesolucoestec.com.br/saude`: tem de responder `ok`.

## 7. E-mail

### 7.1 E-mails que o sistema manda (Brevo)

1. Entrar no Brevo (a conta já foi criada) → **Senders, Domains & Dedicated IPs → Domains → Add a domain** → `valesolucoestec.com.br`.
2. O Brevo mostra alguns registros (TXT do código do Brevo, DKIM e DMARC). Criar cada um na zona DNS do Registro.br, **exatamente** como ele mostra.
   - **Um registro SPF só** por domínio. Se já existir um, junte os dois num só.
   - **Um registro `_dmarc` só.**
3. Esperar o Brevo marcar o domínio como autenticado. Sem isso, ele troca o remetente por um endereço `@brevosend.com` e os e-mails tendem a cair no spam.
4. Em **SMTP & API → SMTP**: copiar o login e criar uma **chave SMTP** só para o Vale Tec. Vão para `SMTP_USUARIO` e `SMTP_SENHA` (seção 4).
5. **Teste:** pela tela "Esqueci a senha", pedir o link para o seu e-mail e conferir se chegou, e se chegou na caixa de entrada, não no spam.

### 7.2 Caixas suporte@ e ouvidoria@ (receber e-mail)

O Brevo **só envia**. Para **receber** nos endereços que estão nos termos, o jeito mais barato é um encaminhamento grátis para o Gmail que vocês já usam:

1. Criar conta no **ImprovMX** (plano grátis) e adicionar o domínio.
2. Criar os apelidos `suporte` e `ouvidoria`, encaminhando para `vale.informatica02@gmail.com`.
3. Criar na zona DNS do Registro.br os registros **MX** que o ImprovMX mostrar, e incluir o SPF dele **no mesmo registro SPF** do item 7.1.
4. Teste: mandar um e-mail de outra conta para `suporte@valesolucoestec.com.br` e ver se chega no Gmail.

Mais tarde, se quiserem responder **como** `suporte@` (e não como o Gmail), dá para configurar o Gmail para enviar pelo SMTP do Brevo. Também dá para contratar caixa de verdade (Zoho Mail, Google Workspace).

## 8. Backup: o que os termos prometem e como cumprir

Os termos (versão 1.0) prometem **cópia de segurança diária, guardada por 30 dias**.

| O que o Render faz | O que falta |
|---|---|
| Banco pago tem **recuperação para um momento qualquer (PITR)**, mas só dos últimos **3 dias** no plano de workspace Hobby (7 dias no Pro) | Os outros 27 dias |
| Backup "lógico" (arquivo do banco) só quando alguém pede, na página do banco (Recovery) | O backup **diário automático** |

**Proposta, sem custo:** uma tarefa agendada do GitHub (GitHub Actions) que todo dia de madrugada:
- faz um `pg_dump` do banco, pelo **External Database URL**;
- criptografa o arquivo com uma senha;
- guarda o resultado no próprio GitHub por **30 dias**, apagado sozinho depois.

> **Atenção: hoje o repositório `Dsmalosti/ValeDesenvolvimentos-Academia` é PÚBLICO** (conferido em 17/10/2026).
> - Num repositório público, os arquivos guardados pelo GitHub Actions podem ser baixados por qualquer pessoa com conta no GitHub. Mesmo criptografado, **backup com dado de aluno não pode ficar exposto assim**.
> - Por isso o modelo **só roda se o repositório for privado** (a primeira linha do job confere).
> - **Recomendação:** tornar o repositório privado (**Settings → General → Danger Zone → Change visibility**). Isso protege também o código, que é o produto, e o histórico.
> - Se o repositório continuar público, a alternativa é guardar o backup num armazenamento privado (Cloudflare R2 ou Backblaze B2, com plano grátis), com a mesma tarefa usando o `rclone`. O Claude adapta quando decidirem.

O modelo está em `docs/exemplos/backup-diario.yml`. Para ligar (com o repositório privado):

1. No GitHub do repositório: **Settings → Secrets and variables → Actions**. Criar `BANCO_URL_EXTERNA` (o External Database URL) e `SENHA_DO_BACKUP` (uma senha longa, guardada também num lugar seguro fora do GitHub: sem ela o backup não abre).
2. Copiar `docs/exemplos/backup-diario.yml` para `.github/workflows/backup-diario.yml` numa branch e abrir o PR. Isso liga uma automação no repositório, então decidam juntos.
3. Rodar uma vez à mão (aba **Actions → Backup diário → Run workflow**) e conferir se o arquivo apareceu.

**Teste de restauração** (obrigatório antes do primeiro cliente; o Claude faz junto):

1. Baixar o último backup em Actions e abrir com a senha:
   `gpg --decrypt backup.sql.gz.gpg | gunzip > backup.sql`
2. Criar um banco Postgres **separado** (o grátis do Render serve) e restaurar:
   `psql "<URL do banco de teste>" < backup.sql`
3. Apontar uma cópia do app para esse banco e entrar com uma conta: os dados têm de estar lá.
4. Apagar o banco de teste.

## 9. Depois do OK do Gunicorn: o arquivo `render.yaml`

Com o OK, a branch do Gunicorn traz também este arquivo na raiz do repositório. Ele descreve o serviço e o banco, e o Render cria tudo igual a partir dele (**New → Blueprint**):

```yaml
services:
  - type: web
    name: valetec
    runtime: python
    region: virginia
    plan: starter
    branch: main
    buildCommand: pip install -r requirements.txt
    preDeployCommand: flask --app main db upgrade
    startCommand: gunicorn --workers 1 --threads 8 --bind 0.0.0.0:$PORT main:app
    healthCheckPath: /saude
    envVars:
      - key: PYTHON_VERSION
        value: 3.13.14
      - key: FLASK_CONFIG
        value: production
      - key: PROXIES_NA_FRENTE
        value: "1"
      - key: SECRET_KEY
        generateValue: true          # o Render gera uma chave aleatória
      - key: DATABASE_URL
        fromDatabase:
          name: valetec-banco
          property: connectionString
      - key: SMTP_SENHA
        sync: false                  # o Render pede o valor no painel; não fica no arquivo

databases:
  - name: valetec-banco
    region: virginia
    plan: basic-256mb
    databaseName: valetec
```

## 10. Ambiente de teste e de produção

O Adauto pediu para pensar nisso depois que o sistema estiver no ar. As opções:

| Opção | Como funciona | Custo |
|---|---|---|
| **A. Só a demonstração local** (como hoje) | Cada branch é testada no computador do Adauto (`instance/demo`) antes do PR; a `main` vai para produção | R$ 0 |
| **B. Um segundo serviço "homologação" no Render** | Uma branch `homologacao` sobe sozinha num serviço separado, com banco separado. O Diogo junta lá primeiro, todo mundo testa no celular, e só depois junta na `main` | Mais US$ 7 do servidor; o banco pode ser o grátis, mas ele expira em 30 dias e precisa ser recriado |
| **C. Preview do Render** | Cada PR ganha um endereço próprio, temporário | Pede o workspace Pro do Render (pago por pessoa) |

**Sugestão:** começar com a **A** e passar para a **B** quando houver clientes pagando, que é quando um erro em produção passa a custar caro.

## 11. Lista do primeiro deploy no Render

- [ ] Gunicorn autorizado e na `main` (com o `render.yaml`)
- [ ] Banco criado (plano pago, região Virginia)
- [ ] Serviço criado, variáveis da seção 4 cadastradas
- [ ] `flask --app main banco-novo` no Shell
- [ ] Contas do Adauto e do Diogo criadas; `admin-do-sistema` para os dois
- [ ] Domínio verificado no Render e `https://valesolucoestec.com.br/saude` respondendo `ok`
- [ ] Domínio autenticado no Brevo; "Esqueci a senha" chegando na caixa de entrada
- [ ] `suporte@` e `ouvidoria@` recebendo (encaminhamento para o Gmail)
- [ ] Backup diário ligado (seção 8) e **restauração testada**
- [ ] Limite de tentativas conferido de duas redes (`docs/DEPLOY.md`, seção 6)
- [ ] Ensaio geral no iPhone e no Android (Adauto)
- [ ] Chave PIX e WhatsApp do suporte cadastrados quando existirem

## Fontes

- Render, DNS de outros provedores (registro A para o domínio principal): https://render.com/docs/configure-other-dns
- Render, recuperação do Postgres (PITR por plano, backup lógico sob demanda): https://render.com/docs/postgresql-refresh
- Brevo, configuração de SMTP e autenticação de domínio (guia técnico): https://www.captaindns.com/br/blog/brevo-transactional-email-technical-guide
- ImprovMX, planos: https://www.improvmx.com/pricing
