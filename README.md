# MinhaAcademia · Vale Desenvolvimentos

SaaS de gestão para academias e personal trainers: alunos, planos com controle de vencimento, biblioteca de exercícios e fichas de treino por dia da semana.

Cada conta de instrutor é uma academia isolada (multi-tenant): nenhuma rota lê ou altera dados de outra conta.

## Stack

- Python 3.13 · Flask 3 · SQLAlchemy 2 · Flask-Migrate (Alembic) · PostgreSQL
- Flask-Login + bcrypt + CSRF (Flask-WTF)
- Tailwind CSS 3 compilado (sem CDN) + JavaScript puro para as interações

## Rodando localmente

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
cp .env.example .env            # preencha SECRET_KEY e DATABASE_URI
flask --app main db upgrade
flask --app main run --debug
```

Acesse http://127.0.0.1:5000 e crie a conta da academia em **Criar conta**.

### CSS

O arquivo `app/static/css/app.css` é gerado. Depois de mexer em templates ou em `app/static/src/app.css`:

```bash
npm install
npm run build:css     # ou npm run dev:css para recompilar ao salvar
```

Faça commit do `app.css` gerado: assim o servidor de produção não precisa de Node.

### Testes

```bash
python -m pytest
```

Os testes usam SQLite em memória e cobrem autenticação, isolamento entre academias, fluxo completo (plano → aluno → ficha) e regras de vencimento.

## Estrutura

```
app/
  __init__.py          create_app, erros, cabeçalhos de segurança
  models.py            User (instrutor/academia), Aluno, Plano, Exercicio, Ficha, Treino, TreinoExercicio
  tenancy.py           do_instrutor() e obter_do_instrutor_ou_404(): use em TODA rota que acessa dados
  services/            regras de negócio (validação, unicidade, renovação, exclusões protegidas)
  blueprints/<modulo>/ rotas, forms e templates de cada módulo
  templates/
    layouts/           app.html (painel com menu lateral) e auth.html (login/cadastro)
    macros/ui.html     componentes: campo, botões, badge, cabeçalho, estado vazio, paginação, ícones
  static/src/app.css   fonte do Tailwind (tokens da marca em tailwind.config.js)
migrations/            Alembic
tests/                 pytest
```

## Regras de negócio

- **Vencimento** = `data_inicio_plano` + `plano.duracao_dias`. "A vencer" = até 7 dias.
- **Renovar** inicia um novo ciclo; se o plano ainda não venceu, o ciclo começa no vencimento atual (o aluno não perde dias).
- **Receita mensal estimada** soma o valor equivalente a 30 dias dos planos em dia.
- Plano com alunos e exercício usado em ficha não podem ser excluídos (desative-os).
- Excluir um aluno exclui as fichas dele.
- E-mail e CPF de aluno são únicos **por academia**.

## Deploy (Render, Railway, Heroku)

1. Variáveis: `FLASK_CONFIG=production`, `SECRET_KEY` (32+ caracteres), `DATABASE_URL` ou `DATABASE_URI`.
2. Build: `pip install -r requirements.txt`
3. O `Procfile` roda `flask db upgrade` no release e sobe o `gunicorn`.
4. Health check: `GET /saude`.

Em produção os cookies de sessão são `Secure`, o app confia no proxy (`ProxyFix`) e recusa `SECRET_KEY` fraca.
