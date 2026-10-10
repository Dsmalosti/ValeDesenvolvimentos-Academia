# back-05-repo-e-config — repositório limpo e configuração com um nome só

| | |
|---|---|
| **Branch** | `back-05-repo-e-config` |
| **Sai de** | `back-04-painel` |
| **Data** | 10/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefas da lista "Tarefas do backend — Diogo"** | 2.5, 1.7, 2.3 e 3.8 |
| **Autorizações** | Itens 2, 3 e 4 da lista respondida pelo Diogo em 10/10/2026 (todos "sim") |

## Resumo

Quatro arrumações que dependiam de autorização. Nenhuma muda o que o usuário vê; duas mudam o que cada desenvolvedor precisa fazer na própria máquina (veja "O que cada um precisa fazer").

## Arquivos

| Arquivo | Tipo | O que mudou |
|---|---|---|
| 102 arquivos `.pyc` e `instance/database.db` | saíram do git | continuam no disco de cada um |
| `requirements.txt` | alterado | saiu `mysql-connector==2.2.9` |
| `requirements-dev.txt` | novo | `pytest`, para quem desenvolve |
| `app/__init__.py` | alterado | lê `DATABASE_URL` |
| `config.py` | alterado | `SECRET_KEY` sem valor padrão |
| `tests/conftest.py`, `tests/navegador/*.py` | alterado | usam o nome novo da variável |
| `tests/test_config.py` | novo | 6 testes |

## Cada mudança: antes, depois e por quê

### 1. `.pyc` e `database.db` fora do git (tarefa 2.5)

- **Antes:** 102 arquivos `.pyc` (cache que o Python gera sozinho) e o `instance/database.db` estavam versionados.
- **Depois:** `git rm --cached` em todos. Os arquivos **continuam no disco**; só deixam de ser acompanhados. O `.gitignore`, consertado na `back-02`, impede que voltem.
- **Por quê:**
  - o `.pyc` muda toda vez que alguém roda o projeto. Nesta integração, dois commits feitos pelo botão do editor levaram dezenas de `.pyc` por engano e precisaram ser desfeitos;
  - o `database.db` é um banco SQLite de teste. Pode conter e-mail e senha criptografada de quem testou.
- **Atenção, Diogo:** tirar do git **não apaga do histórico**. O `database.db` continua nos commits antigos do GitHub. Se ele tiver dado de alguém de verdade, vale trocar aquelas senhas. Limpar o histórico exigiria reescrever commits já publicados, o que não fiz.

### 2. `requirements.txt` (tarefa 1.7)

- **Antes:** tinha `mysql-connector==2.2.9` **e** `mysql-connector-python==9.4.0`.
- **Depois:** saiu só o `mysql-connector==2.2.9`.
- **Por quê:** essa versão antiga não instala em Python 3.12 ou mais novo, e o `pip install` do deploy pararia nessa linha. O `mysql-connector-python` é o pacote oficial e atual, e ficou.
- **Ainda dá para enxugar:** como o desenvolvimento é em Postgres e não há produção em MySQL, o `mysql-connector-python` também poderia sair. Não tirei porque a autorização foi só para a versão antiga.
- **Novo `requirements-dev.txt`:** inclui o `requirements.txt` e acrescenta o `pytest`. O Playwright, usado só nos testes de navegador, ficou de fora por baixar um Chromium de 150 MB; o arquivo explica como instalar.

### 3. Um nome só para a variável do banco (tarefa 2.3)

- **Antes:** o `create_app()` lia `DATABASE_URI`; o `ProductionConfig` lia `DATABASE_URL`. Como o `create_app()` sobrescrevia tudo, o `ProductionConfig` nunca valia. Numa hospedagem que só cria `DATABASE_URL` (o padrão da maioria), o app não subia.
- **Depois:** o nome oficial é **`DATABASE_URL`**, lido pelo `create_app()`.
- **Transição:** se só existir `DATABASE_URI`, o app ainda sobe e escreve um aviso no log pedindo para renomear. Fiz assim para ninguém ficar com o ambiente quebrado de um dia para o outro. O nome antigo sai de vez na branch de produção.
- **Se existirem os dois,** vale o `DATABASE_URL`.

### 4. `SECRET_KEY` sem valor padrão (tarefa 3.8)

- **Antes:** `SECRET_KEY = os.getenv("SECRET_KEY", "chave-dev")` no `config.py`.
- **Depois:** `os.getenv("SECRET_KEY")`, sem padrão.
- **Por quê:** o valor padrão está publicado no GitHub. Se a variável faltasse em algum ambiente, o app subiria com uma chave que qualquer pessoa conhece, e daria para forjar uma sessão de login. O `create_app()` já recusava subir sem a chave; faltava tirar o padrão do `config.py`.

## O que cada um precisa fazer

1. **No `.env`:** renomear `DATABASE_URI` para `DATABASE_URL`. Enquanto não renomear, o app funciona e avisa no log.
2. **Depois do `git pull` desta branch,** os `.pyc` deixam de aparecer no `git status`. Não é preciso apagar nada.
3. **Para rodar os testes:** `pip install -r requirements-dev.txt`.

## Como foi testado

- **`pytest`: 55 de 55.** Os 6 novos (`tests/test_config.py`): sobe com `DATABASE_URL`; o nome antigo funciona e avisa; o novo vence o antigo; não sobe sem banco; não sobe sem `SECRET_KEY`; o `config.py` não tem mais valor padrão para a chave.
- **Instalação limpa:** criei um ambiente virtual novo, em Python 3.13, e rodei `pip install -r requirements.txt` e depois `-r requirements-dev.txt`. Os dois terminaram sem erro e o `pip check` não acusou conflito.
- **`git ls-files`** não lista mais nenhum `.pyc` nem nada em `instance/`.
- Os testes de navegador não foram refeitos nesta branch: nenhuma tela mudou.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item da seção 6 (segredos e dependências) | Situação |
|---|---|
| `.env` fora do git | Já era: `git log --all -- .env` vem vazio. |
| Um nome só de variável, validado ao subir | Feito: `DATABASE_URL`, e o app recusa subir sem ela. |
| Segredo sem valor padrão no código | Feito para a `SECRET_KEY`. |
| Banco de teste fora do repositório | Feito daqui em diante; continua no histórico (veja o item 1). |
| `pip-audit` antes do deploy | Não rodado nesta branch; está na revisão final de segurança. |

## Como revisar

```bash
git fetch origin
git diff origin/back-04-painel..origin/back-05-repo-e-config -- . ':!*.pyc' ':!instance'   # o que mudou de verdade
git diff --stat origin/back-04-painel..origin/back-05-repo-e-config | tail -1             # confere os 103 arquivos removidos
```

## Riscos

- **Quem dependia do `instance/database.db` versionado** para rodar localmente precisa criar o próprio banco. Pelo que o Diogo respondeu, ele usa Postgres local, então não é afetado.
- **Ao trocar para uma branch antiga,** o git recoloca os `.pyc` versionados daquela branch no disco; ao voltar, tira de novo. É esperado.
- **Variável de ambiente:** em qualquer ambiente novo (inclusive a produção), a variável a criar é `DATABASE_URL`.
