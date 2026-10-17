# back-29-dependencias — 5 atualizações de segurança e uma dependência a menos

| | |
|---|---|
| **Branch** | `back-29-dependencias` |
| **Sai de** | `back-28-precos-e-promocao` |
| **Data** | 17/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Autorização** | Regra 4 do `CLAUDE.md` (mexer no `requirements.txt`). Adauto, 17/10/2026: "Autorizar a atualização das 5 dependências com falha conhecida — confirmado"; "Autorizar tirar o Flask-JWT-Extended, que não é usado — pode tirar" |
| **Tem migration** | Não |

## O que mudou

### 1. Cinco pacotes atualizados (falhas de segurança conhecidas)

O `pip-audit` da `back-20` achou falhas publicadas em cinco pacotes. Cada um subiu só até a primeira versão corrigida, sem pular versão grande:

| Pacote | Antes | Agora | O que a falha permitia (resumo) |
|---|---|---|---|
| Flask | 3.1.2 | **3.1.3** | Em certos acessos à sessão, faltava o cabeçalho `Vary: Cookie`. Um cache no meio do caminho poderia guardar uma página de um usuário logado e mostrá-la a outro (CVE-2026-27205) |
| Werkzeug | 3.1.3 | **3.1.9** | Quatro falhas corrigidas entre a 3.1.4 e a 3.1.9 (servidor de desenvolvimento e tratamento de requisições) |
| idna | 3.11 | **3.15** | Falha no tratamento de nomes de domínio |
| Mako | 1.3.10 | **1.3.12** | Falha no motor de templates (o sistema não usa o Mako direto: ele vem com o Alembic, das migrations) |
| python-dotenv | 1.1.1 | **1.2.2** | Falha ao ler o arquivo `.env` |

Depois da troca, o `pip-audit -r requirements.txt` respondeu **"No known vulnerabilities found"**.

### 2. Flask-JWT-Extended saiu

- O `app/extensions/security.py` ligava um `JWTManager` que nada no sistema usava: o login é por sessão (Flask-Login), não por token.
- Saíram o import, o `jwt = JWTManager()` e o `jwt.init_app(app)`, com um comentário `[back-29-dependencias]` explicando o que havia.
- A linha `Flask-JWT-Extended==4.7.4` saiu do `requirements.txt`. É um pacote a menos para atualizar e conferir.

## Como era antes

- `requirements.txt` com as cinco versões antigas e o `Flask-JWT-Extended`.
- O app criava o `JWTManager` ao subir.

## O que o Adauto precisa fazer no computador dele

Depois de juntar esta branch, atualizar o ambiente local (o Claude não mexeu no `.venv` do projeto; os testes rodaram num ambiente separado):

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip uninstall -y Flask-JWT-Extended PyJWT
```

O segundo comando é opcional: só limpa o que não é mais usado.

## Como foi testado

Tudo num **ambiente Python novo**, criado do zero só com o `requirements-dev.txt` desta branch e o Playwright. Assim ficou provado que o sistema sobe e funciona sem o Flask-JWT-Extended instalado.

- `pytest` inteiro: **532 passaram**.
- Os 16 testes de navegador (todas as telas, celular e desktop, temas claro e escuro): **672 conferências, todas passando**.
- `pip-audit -r requirements.txt`: nenhuma falha conhecida.

## Como revisar

```bash
git fetch origin
git diff origin/back-28-precos-e-promocao..origin/back-29-dependencias
```

## Riscos

- **Mudança de comportamento entre versões**: são todas versões de correção (o último número muda, ou o do meio no `python-dotenv` e no `idna`). A bateria inteira de testes e de navegador passou com elas.
- **Ambiente local desatualizado**: quem não rodar o `pip install -r requirements.txt` continua com as versões antigas, que funcionam, mas com as falhas.
