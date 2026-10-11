---
name: "saas-flask-seguranca"
description: "Use antes de lançar ou revisar um SaaS em Flask/SQLAlchemy — isolamento entre contas (multi-tenant), papéis, CSRF, rate limit, headers, segredos, uploads, PIX, LGPD."
---

# Segurança de SaaS em Flask (checklist de lançamento)

Segurança aqui é **pré-condição de lançamento**, não feature. Cada item abaixo tem o "porquê" —
se não entender o porquê, não marque como feito.

## 1. Isolamento entre contas (o erro que mata SaaS)

- Toda tabela de negócio tem o discriminador de conta (`instrutor_id` no Vale Tec) **NOT NULL** + FK.
  `nullable=True` só durante a migration que popula dado legado; depois trava.
- Nunca `Model.query.get(id)` vindo da URL. Sempre:
  ```python
  aluno = Aluno.query.filter_by(id=id, instrutor_id=current_user.conta_id).first_or_404()
  ```
- Centralize: um helper `da_conta(Model)` ou `query_class` que já filtra pela conta. Revisão de código
  procura `query.get(` e `filter_by(id=` sem o filtro de conta.
- Teste obrigatório: logar na conta A e pedir `/alunos/<id da conta B>` → 404 (não 403: não revele que existe).
- Export (CSV/PDF), webhooks e jobs agendados também filtram por conta — são onde o filtro costuma faltar.

## 2. Papéis (dono / recepção / instrutor)

- Esconder botão no template é **cosmético**. A rota checa o papel no servidor:
  `@requer_papel('proprietario')` antes de financeiro, metas, custos, exclusão.
- Coluna `papel` no usuário; nunca inferir papel por e-mail ou por flag no formulário.

## 3. Autenticação

- Senha com bcrypt/argon2 (já é bcrypt no projeto — não trocar).
- **Rate limit** no login e em "esqueci senha": Flask-Limiter, ex. `5/minute` por IP + por identificador.
- Mensagem de erro igual pra "usuário não existe" e "senha errada".
- Sessão: `SESSION_COOKIE_SECURE=True`, `HTTPONLY=True`, `SAMESITE='Lax'`; `PERMANENT_SESSION_LIFETIME` definido.
- Trocar o id de sessão após login (Flask-Login `login_user` + `session.clear()` antes).

## 4. Formulários e entrada

- CSRF em **todo** POST (Flask-WTF `CSRFProtect`); o front já manda `csrf_token` e `<meta name="csrf-token">`.
- Validação no servidor sempre (o `data-validate` do front é conveniência, não segurança).
- Dinheiro: `Numeric(10,2)`/`Decimal`, nunca float. Converter "1.234,56" no servidor.
- Jinja já escapa HTML; nunca `|safe` em dado do usuário. `|tojson|forceescape` em atributos `data-json`.
- Só ORM/queries parametrizadas; nada de f-string em SQL.

## 5. Transporte e headers

- HTTPS forçado em produção + HSTS (Flask-Talisman).
- CSP: o front do Vale Tec não usa script inline executável (só `type="application/json"`) —
  dá pra ter `script-src 'self'`. Manter assim: JS novo vai em arquivo em `static/js/`.
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `frame-ancestors 'none'`.

## 6. Segredos e dependências

- `.env` no `.gitignore` e **nunca commitado** (`git log --all -- .env` tem que vir vazio).
  Se já foi, trocar todas as chaves — apagar do histórico não basta.
- Um nome só de variável por config (`DATABASE_URL`), validado ao subir o app.
- `pip-audit` antes de cada deploy externo.

## 7. Pagamentos e webhooks (PIX)

- Webhook valida assinatura/secret do PSP e é **idempotente** (mesmo evento 2× não paga 2×: unique no id do evento).
- Pagamento guarda `origem_confirmacao` (webhook/manual + quem) — nunca booleano solto.
- Valor confirmado vem do PSP, não do formulário.

## 8. Uploads

- Lista branca de tipo (verificar bytes, não só extensão), limite de tamanho (`MAX_CONTENT_LENGTH`),
  nome gerado no servidor, fora de `static/` público, servido por rota que checa a conta.

## 9. LGPD (dados de aluno: CPF, telefone, saúde)

- Coletar só o necessário; avaliação física é medida, nunca diagnóstico.
- Exportar e excluir dados do aluno a pedido (soft delete + anonimização).
- Logs sem CPF/senha/token.

## Como usar esta skill

1. Rode a checklist por seção e marque com evidência (arquivo:linha ou teste).
2. Para cada falha: severidade (P0 bloqueia lançamento) + correção + teste que prova.
3. Não aplique mudança de backend sem explicar ao Adauto o que muda e pedir permissão (regra do projeto).