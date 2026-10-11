# back-02-limpeza — defeitos que quebravam telas ou sujavam o log

| | |
|---|---|
| **Branch** | `back-02-limpeza` |
| **Sai de** | `back-01-auth-login` |
| **Data** | 10/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefas da lista "Tarefas do backend — Diogo"** | 2.1, 2.2, 2.4 e a parte do `.gitignore` da 2.5 |
| **Fica de fora** | O resto da 2.5 (tirar `.pyc` e `database.db` do git), 1.7 (`requirements.txt`), 2.3 (variável do banco) e 3.8 (`SECRET_KEY` padrão). Todos dependem de autorização (regra 4 do `CLAUDE.md`) e foram para a `back-05-repo-e-config`. |

## Resumo

Cinco correções pequenas, nenhuma muda o banco nem adiciona dependência. Entra também a primeira pasta de testes automáticos do projeto (`tests/`).

## Arquivos

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `app/blueprints/exercicios/routes.py` | alterado | redirect depois de editar um exercício |
| `app/blueprints/fichas/routes.py` | alterado | `/excuir/` → `/excluir/`; `'Get'` → `'GET'` |
| `app/blueprints/planos/routes.py` | alterado | saíram 3 `print()` |
| `app/services/plano_service.py` | alterado | saiu 1 `print()` |
| `app/services/base_service.py` | alterado | saíram 3 `print()`; o erro ao salvar passa a ir para o log |
| `app/services/dashboard_service.py` | alterado | contagem de alunos ativos |
| `.gitignore` | alterado | linhas que não valiam por causa de espaços; pastas locais |
| `tests/` | novo | `conftest.py`, `test_limpeza.py`, `test_login.py` |

Toda linha alterada no backend tem o comentário `[back-02-limpeza]` dizendo como era antes.

## Cada mudança: antes, depois e por quê

### 1. Editar exercício dava erro 500 (tarefa 2.1)

- **Antes:** `redirect(url_for('exercicios.listarPlanos'))`. Esse endpoint não existe.
- **Depois:** `url_for('exercicios.listarExercicios')`.
- **Por quê:** salvar a edição de um exercício terminava em `BuildError`. O exercício até era salvo, mas a pessoa via uma tela de erro.

### 2. Rota de excluir ficha com erro de digitação (tarefa 2.2)

- **Antes:** `/fichas/excuir/<id>` e `methods=['Get', 'POST']` no editar.
- **Depois:** `/fichas/excluir/<id>` e `['GET', 'POST']`.
- **Por quê:** a URL errada viraria contrato quebrado com o front novo. O template antigo usa `url_for('fichas.excluirFicha')`, então continua funcionando sem mexer nele.
- **Atenção:** quem tiver a URL antiga salva em algum lugar recebe 404. Só o formulário da lista de fichas a usava.

### 3. `print()` com dados de formulário (tarefa 2.4)

- **Antes:** 7 `print()` em `planos/routes.py`, `plano_service.py` e `base_service.py`. Três deles despejavam os dados digitados no log do servidor.
- **Depois:** todos removidos. No `BaseService.salvar`, o erro passa a ser registrado com `logging`.
- **Por quê:** quando houver CPF e telefone nesses formulários, isso é vazamento de dado pessoal no log (LGPD).
- **Detalhe:** o log grava só o **tipo** do objeto e o **tipo** do erro (`Falha ao salvar Aluno: IntegrityError`). A mensagem completa do banco traz os valores (e-mail, CPF) e por isso não vai para o log. Antes, esse erro era engolido sem deixar rastro nenhum.

### 4. Painel contava zero alunos ativos

- **Antes:** `sum(1 for a in alunos if a.ativo == 'ativo')`. A coluna é `True`/`False`, nunca o texto `'ativo'`, então o total dava sempre zero.
- **Depois:** `if a.ativo`.
- **Por quê:** é o primeiro número que o dono vê ao entrar. É o mesmo defeito que já tinha sido corrigido no `painelAdm`, mas aqui tinha ficado.
- **Ainda falta:** esta função conta os alunos de **todas** as academias. Isso é corrigido na `back-03-isolamento`.

### 5. `.gitignore` que não valia (parte da tarefa 2.5)

- **Antes:** as linhas `__pycache__/` e `*.pyc` tinham três espaços na frente. O git lê esses espaços como parte do nome, então as regras nunca valeram.
- **Depois:** linhas sem os espaços, mais `instance/`, `.pytest_cache/` e `.claude/launch.json` (configuração local do Claude Code).
- **O que isso resolve:** `.pyc` **novo** deixa de aparecer no `git status`.
- **O que isso NÃO resolve:** os 100 `.pyc` e o `instance/database.db` que **já estão versionados** continuam versionados. O `.gitignore` não vale para arquivo que o git já acompanha. Tirá-los é a `back-05`, que depende de autorização.

## Testes automáticos (novo)

O projeto não tinha testes. Entraram em `tests/`:

- `conftest.py`: sobe o app com **SQLite descartável** e nunca toca o banco do `.env`. Tem uma trava: se o banco não for o descartável, nenhum teste roda.
- `test_limpeza.py`: 4 testes, um para cada defeito desta branch.
- `test_login.py`: 11 testes do login da `back-01` (CSRF, senha errada, usuário inativo, maiúscula no e-mail, "lembrar de mim", voltar para a página pedida, `next` de outro site, sair só por POST).

Como rodar:

```bash
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests -q
```

O `-B` e o `-p no:cacheprovider` evitam criar `.pyc` e pasta de cache.

**Atenção, Diogo:** o `pytest` está instalado no ambiente do Adauto, mas **não está no `requirements.txt`**. Não mexi no arquivo (regra 4). Fica para decidir se entra num `requirements-dev.txt`.

## O que NÃO mudou (de propósito)

- **`/instrutores/painel/` continua dando erro 500.** O formulário de exclusão em massa do `painel-administrativo.html` chama `alunos.excluirAlunos`, que não existe, e a rota `alunos.excluirAluno` exclui um aluno por vez. Não é erro de digitação: a rota de exclusão em massa nunca foi criada. Como essa tela sai com o painel novo, não criei rota nova para ela. O doc da `back-01` dizia que era "uma letra"; estava errado.
- **Painel antigo com números fixos.** "Pagamentos pendentes" e "Planos a vencer" mostram `237` escrito direto no `notificacao.html`. Também some com o painel novo.
- **Nenhuma migration, nenhuma dependência nova, nenhum arquivo apagado.**

## Como foi testado

- **`pytest`: 15 de 15.**
- **Smoke de rotas** (todas as rotas GET, anônimo e logado, SQLite descartável) contra a `main`: mesmos status. As diferenças são as da `back-01` (redirecionamento para `/login` e as três rotas novas).
- `git grep` confirma que não sobrou nenhum `print(` em `app/`.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Situação nesta branch |
|---|---|
| Logs sem dado pessoal (§9) | Melhorou: saíram os `print()` com dados de formulário; o log novo não leva valores. |
| Segredos (§6) | `git log --all -- .env` vem vazio: o `.env` nunca foi commitado. `SECRET_KEY` com valor padrão no `config.py` continua (tarefa 3.8, na `back-05`). |
| Isolamento entre contas (§1) | Não tratado aqui: é a `back-03`. |

## Como revisar

```bash
git fetch origin
git diff origin/back-01-auth-login..origin/back-02-limpeza -- app .gitignore   # o backend desta branch
git diff origin/back-01-auth-login..origin/back-02-limpeza -- tests            # os testes
```

## Riscos

- Baixo. A única mudança de comportamento visível é a URL de excluir ficha, usada só por um formulário que continua funcionando.
- O log novo no `BaseService.salvar` usa o `logging` padrão do Python. Sem configuração de log em produção, a mensagem vai para a saída de erro do servidor, que é onde os `print()` já iam.
