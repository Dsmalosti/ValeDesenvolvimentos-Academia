# back-03-isolamento — uma academia não enxerga a outra

| | |
|---|---|
| **Branch** | `back-03-isolamento` |
| **Sai de** | `back-02-limpeza` |
| **Data** | 10/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefas da lista "Tarefas do backend — Diogo"** | 3.1 (o que dá para fazer sem migration), 3.3 e 3.4 |
| **Fica de fora** | Exercício com dono, e-mail e CPF únicos por academia, `instrutor_id` obrigatório e a tabela `contas`. Todos pedem migration e estão na `back-05-contas-e-papeis`. |

## Resumo

Antes desta branch, qualquer pessoa com login em **uma** academia conseguia, trocando um número na URL:

- trocar o e-mail e a senha do dono de **outra** academia, e assim tomar a conta dele;
- apagar o usuário de outra academia;
- ler, editar e apagar as fichas e os treinos de outra academia;
- ver a lista de usuários de todas as academias, com nome e e-mail.

E duas rotas de fichas abriam **sem login nenhum**.

Agora toda consulta dessas telas passa por um filtro de conta único, e o que não é da conta responde 404. Nenhuma migration, nenhuma dependência nova, nenhum template alterado.

## Arquivos

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `app/helpers/conta.py` | novo | `conta_id()`, `da_conta()`, `fichas_da_conta()`, `treinos_da_conta()`, `exigir_login_em()` |
| `app/blueprints/fichas/routes.py` | alterado | todas as consultas filtradas; login nas duas rotas abertas; excluir treino só por POST |
| `app/blueprints/instrutores/routes.py` | alterado | listar, editar e excluir só o próprio usuário |
| `app/blueprints/alunos/form.py` | alterado | o select de planos só mostra os da conta |
| `app/services/dashboard_service.py` | alterado | o painel só conta os alunos da conta |
| `app/blueprints/{alunos,planos,exercicios,pagamentos}/routes.py`, `app/routes.py` | alterado | segunda tranca de login no blueprint inteiro |
| `tests/test_isolamento.py` | novo | 15 testes "conta A × conta B" |

Toda linha alterada no backend tem o comentário `[back-03-isolamento]` dizendo como era antes.

## Cada mudança: antes, depois e por quê

### 1. Um lugar só para o filtro de conta (`app/helpers/conta.py`)

- **Antes:** cada rota filtrava (ou esquecia de filtrar) por conta própria. Alunos e planos já estavam certos; o resto usava `Model.query.all()` e `get_or_404(id)`.
- **Depois:** quatro funções, usadas por todas as rotas:
  - `conta_id()`: o id da conta de quem está logado;
  - `da_conta(Model)`: consulta já filtrada, para modelos com `instrutor_id`;
  - `fichas_da_conta()` e `treinos_da_conta()`: a ficha e o treino não têm dono direto, então o filtro passa pelo aluno (join).
- **Por quê:** com o filtro num lugar só, ninguém esquece. E quando a tabela `contas` chegar (tarefa 3.2), muda **uma função** (`conta_id()`), não todas as rotas.
- **404, não 403:** quando o registro é de outra conta, a resposta é "não existe". O 403 confirmaria para um curioso que aquele id existe em outra academia.
- **Não mexi nas rotas de alunos, planos e pagamentos que já filtravam** com `current_user.id`. Estão corretas; passam para o helper na `back-05`, junto com a troca para `conta_id`.

### 2. Usuários (`instrutores`): o pior item

- **Antes:** `editarInstrutor` e `excluirInstrutor` usavam o id da URL sem conferir. `listarInstrutores` fazia `User.query.all()`.
- **Depois:** editar e excluir só valem para o próprio usuário (`instrutor_id == conta_id()`); o resto responde 404. A lista mostra só o próprio usuário.
- **Por quê:** dava para trocar o e-mail e a senha de outro dono e entrar na conta dele. Era a falha mais grave do sistema.
- **Efeito visível:** a tela "lista de instrutores" passa a ter uma linha só. Ela volta a listar a equipe quando existir a tabela `contas`.

### 3. Fichas e treinos

- **Antes:** `Ficha.query.all()`, `Ficha.query.get_or_404(id)`, `Treino.query.get_or_404(id)` em todas as rotas; o select de alunos trazia os de todas as academias.
- **Depois:** `fichas_da_conta()` e `treinos_da_conta()` em todas; o select de alunos usa `da_conta(Aluno)`.
- **Envio forjado:** o WTForms só aceita um valor que esteja nas opções do select. Então filtrar as opções também bloqueia quem manda o id de outra conta direto no POST. Há teste para isso.

### 4. Login obrigatório em tudo (tarefa 3.3)

- **Antes:** `fichas.criarFicha` (`/fichas/novo/`) e `fichas.fichaDetalhes` (`/fichas/detalhes/<id>`) não tinham `@login_required`. Qualquer pessoa na internet criava e lia fichas.
- **Depois:** as duas ganharam o decorator. Além disso, cada blueprint sem página pública (`alunos`, `planos`, `exercicios`, `fichas`, `pagamentos`, `main`) chama `exigir_login_em(blueprint)`, que barra quem não está logado antes de qualquer rota.
- **Por quê duas trancas:** o decorator esquecido foi exatamente o que aconteceu. Com a tranca no blueprint, uma rota nova já nasce protegida.
- **Não entrou em `instrutores` nem em `auth`**, porque têm páginas públicas (login e cadastro). Lá continuam os decorators.

### 5. Nenhum GET apaga dados (tarefa 3.4)

- **Antes:** `/fichas/treino/<id>/excluir` aceitava `GET` e `POST`.
- **Depois:** só `POST`.
- **Por quê:** com GET, abrir o endereço já apagava o treino. Um link, uma imagem em outro site ou o carregamento antecipado de links do front novo apagaria dados sozinho.
- **Template:** o `ficha-detalhes.html` já envia `POST` com `csrf_token`. Nada muda para quem usa.

### 6. Painel e select de planos

- **Painel:** `Aluno.query.all()` → `da_conta(Aluno).all()`. Contava os alunos e os aniversariantes de todas as academias.
- **Cadastro de aluno:** `Plano.query.all()` → `da_conta(Plano).all()`. Mostrava os planos de todas as academias.

## O que NÃO foi resolvido aqui (precisa de migration)

| Pendência | Risco hoje | Vai em |
|---|---|---|
| **Exercício não tem dono.** A tabela não tem a coluna. | É um catálogo único: qualquer academia logada vê, edita e apaga os exercícios que as outras usam. Não vaza dado pessoal, mas uma academia pode estragar o catálogo de todas. | `back-05` |
| **E-mail e CPF de aluno são únicos no banco inteiro.** | Um aluno de duas academias trava o cadastro, e a mensagem de erro revela que ele existe em outra. | `back-05` |
| **`instrutor_id` aceita vazio** em `alunos` e `planos`. | Um registro sem dono fica invisível para todo mundo. | `back-05` |
| **Logout antigo por GET** (`/instrutores/sair/`). | Qualquer site desloga o usuário. Não altera dado. | `back-06`, com a saída do cabeçalho antigo |
| **Cadastro aberto** (`/instrutores/cadastro/`). | Qualquer pessoa cria uma conta de academia. É como o sistema funciona hoje; vira decisão (T4 do roadmap). | decisão |

## Atenção, Diogo: registros antigos sem dono

Com o filtro, uma ficha só aparece se o aluno dela tiver `instrutor_id`. Se houver aluno antigo sem dono no banco, as fichas dele somem de todas as listas (os alunos e planos sem dono já estavam invisíveis antes desta branch). Vale conferir:

```sql
SELECT count(*) FROM alunos WHERE instrutor_id IS NULL;
SELECT count(*) FROM planos WHERE instrutor_id IS NULL;
```

Se vier diferente de zero, é preciso atribuir um dono a esses registros antes do deploy.

## Como foi testado

- **`pytest`: 30 de 30** (15 novos de isolamento, mais os 15 que já existiam).
- **Contraprova:** rodei os 15 testes de isolamento contra o código **anterior** a esta branch: **9 falharam**. Ou seja, os testes realmente pegam as falhas, e não passam por acaso.
- O que os testes de isolamento cobrem, logado na conta A e mirando a conta B:
  - 19 combinações de rota e método com id de B respondem 404;
  - excluir, inativar e editar aluno e plano de B não alteram nada;
  - nada de B foi tocado depois de todas as tentativas (ficha, treino, e-mail do dono);
  - as 5 listas não mostram nada de B, e mostram o que é de A;
  - os selects só oferecem o que é de A;
  - envio forjado com id de B não cria nada, e o mesmo envio com id de A cria (prova que a recusa é pelo id);
  - o painel conta só os alunos de A;
  - **sem login, nenhuma rota fora da lista de públicas responde** (o teste percorre todas as rotas do app, então rota nova entra sozinha);
  - **nenhuma rota de excluir, alternar ou sair aceita GET** (com o logout antigo anotado como pendência conhecida).
- **Smoke de rotas** contra a `main`: os status só mudaram onde era para mudar. `/fichas/novo/` e `/fichas/detalhes/<id>` passaram a pedir login, e `/fichas/treino/<id>/excluir` deixou de aceitar GET.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Seção da skill | Situação depois desta branch |
|---|---|
| §1 Isolamento entre contas | Fechado para alunos, planos, pagamentos, fichas, treinos, usuários e painel, com teste. **Aberto** para exercícios e para a unicidade de e-mail e CPF (precisam de migration). |
| §1 "Nunca `Model.query.get(id)` vindo da URL" | Sobram `Exercicio.query.get_or_404` (pendência acima) e `User.query.get_or_404` em `editarInstrutor`, este protegido pela checagem `instrutor_id == conta_id()` na linha anterior. |
| §2 Papéis | Não existe ainda (`back-05`). Hoje todo usuário é dono da própria conta. |
| §3 Autenticação | Login obrigatório em todas as rotas não públicas, com teste que percorre o app inteiro. Limite de tentativas continua faltando (`back-19`). |
| §4 CSRF | `CSRFProtect` global já existia; nenhuma rota que altera dado aceita GET, com exceção do logout antigo. |

## Como revisar

```bash
git fetch origin
git diff origin/back-02-limpeza..origin/back-03-isolamento -- app     # o backend desta branch
git diff origin/back-02-limpeza..origin/back-03-isolamento -- tests   # os testes
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests -q    # rodar os testes
```

Sugestão de leitura: comece pelo `app/helpers/conta.py`, que é curto, e depois o `fichas/routes.py`.

## Riscos

- **Registros antigos sem dono** ficam invisíveis (veja a consulta acima). É o único risco de dado "sumir" para o usuário.
- **A lista de instrutores encolhe** para uma linha. Se alguém usava essa tela para administrar todos os usuários do sistema, perde isso. Essa função, se for necessária, deve ser uma tela de administrador do Vale Tec, não uma tela de cliente.
- O arquivo `fichas/routes.py` foi regravado inteiro para receber os comentários; o `git diff` mostra só as linhas que mudaram de fato.
