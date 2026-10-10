# back-06-contas-e-papeis — a academia separada do usuário, e o que cada papel pode

| | |
|---|---|
| **Branch** | `back-06-contas-e-papeis` |
| **Sai de** | `back-05-repo-e-config` |
| **Data** | 10/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefas da lista "Tarefas do backend — Diogo"** | 3.2 (conta × usuário), 3.5 (único por academia), 3.6 (papéis), o que faltava da 3.1 (exercícios) e o "passo 4" do `instrutor_id` |
| **Decisões do Diogo usadas** | item 1 (migrations: sim), item 7 (tabela `contas` separada), item 8 (aluno continua com `ativo`), item 9 (fechar o cadastro aberto) |
| **Tem migration** | **Sim:** `migrations/versions/b06c0a1e2f30_contas_e_papeis.py`. Move dados. Leia a seção "A migration" antes de rodar. |

## Resumo

Até aqui, cada linha de `instrutores` **era** uma academia: o dono via os próprios alunos e ninguém mais. Não havia como a recepção e os instrutores de uma mesma academia trabalharem juntos.

Agora existe a **conta** (a academia). O dono, a recepção e os instrutores são usuários diferentes da mesma conta e veem os mesmos alunos. Cada usuário tem um **papel**, e o servidor bloqueia o que o papel não pode.

Para quem usa hoje, nada muda de aparência, a não ser o nome da academia no painel: deixou de ser o texto fixo "Minha academia".

## Arquivos

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `app/models.py` | alterado | modelo `Conta`; `conta_id` e `papel` em `User`; `conta_id` em `Aluno`, `Plano`, `Pagamento` e `Exercicio`; únicos por conta em `Aluno` |
| `migrations/versions/b06c0a1e2f30_contas_e_papeis.py` | novo | a migration |
| `app/helpers/conta.py` | alterado | a conta passa a ser `current_user.conta_id`; entram `papel_requerido`, `exigir_papel_em`, `exercicios_visiveis` e `exercicios_proprios` |
| `app/helpers/contexto.py` | alterado | `academia` e o papel vêm do banco |
| `app/cli.py` | novo | comando `flask criar-conta` |
| `app/services/{aluno,plano,pagamento,exercicio,instrutor}_service.py` | alterado | filtram por conta; gravam `conta_id` |
| `app/blueprints/{alunos,planos,pagamentos,exercicios,fichas,instrutores,painel}/routes.py`, `pendentes.py` | alterado | filtro por conta e permissão por papel |
| `tests/test_contas.py` | novo | 56 testes |

Toda linha alterada no backend tem o comentário `[back-06-contas-e-papeis]` dizendo como era antes.

## Cada mudança: antes, depois e por quê

### 1. A conta (tabela `contas`)

- **Antes:** não existia. A "academia" era o próprio usuário.
- **Depois:** tabela `contas` com `nome`, `razao`, `cnpj`, `telefone`, `email`, `cidade`, `endereco`, `modelo` (`academia` ou `personal`), `checkin_ativo`, `pix_ligado` e `criado_em`. São os campos que o front lê em `academia.*`.
- **`instrutores` ganhou** `conta_id` (obrigatório) e `papel` (`proprietario`, `recepcao` ou `instrutor`; padrão `proprietario`).

### 2. `conta_id` nas tabelas de negócio

- **Antes:** alunos, planos e pagamentos eram filtrados por `instrutor_id` (o usuário que cadastrou).
- **Depois:** ganharam `conta_id` (obrigatório), e é por ele que o sistema isola as academias.
- **Por quê não bastava `conta_id` só em `instrutores`:** se o aluno continuasse preso ao `instrutor_id` de quem o cadastrou, o aluno cadastrado pela recepção não apareceria para o dono.
- **`instrutor_id` continua existindo** e não foi mexido. Deixou de significar "o dono" e passou a significar "quem cadastrou" ou "quem registrou".
- **Fichas e treinos** não ganharam coluna: continuam sendo da conta por meio do aluno.

### 3. O filtro continua num lugar só

Na `back-03` todas as consultas passaram a usar `app/helpers/conta.py`. Por isso esta troca mexeu em pouca coisa: `conta_id()` devolvia `current_user.id` e agora devolve `current_user.conta_id`; `da_conta(Modelo)` filtrava por `instrutor_id` e agora filtra por `conta_id`. Os serviços, que recebiam o `instrutor_id` por parâmetro só para filtrar, pararam de receber.

### 4. Papéis (tarefa 3.6)

Esconder o botão no template é só aparência; quem bloqueia é a rota. Regra aplicada às telas que existem hoje:

| O quê | Dono | Recepção | Instrutor |
|---|---|---|---|
| Ver alunos, planos, exercícios e fichas | sim | sim | sim |
| Criar e editar fichas e exercícios | sim | sim | sim |
| Cadastrar, editar, ativar e inativar aluno | sim | sim | **403** |
| **Excluir** aluno de vez | sim | **403** | **403** |
| Criar, editar e excluir plano | sim | sim | **403** |
| Tudo de pagamentos | sim | sim | **403** |
| Relatórios e cobranças (ainda "em construção") | sim | sim | **403** |
| Ver a lista da equipe | sim | sim | **403** |
| Editar o próprio usuário | sim | sim | sim |
| Editar outra pessoa da equipe | sim | **403** | **403** |
| Tirar alguém da equipe | sim (nunca a si mesmo) | **403** | **403** |
| Painel gerencial, com os números de dinheiro | sim | sim | vê "em construção" |

- **404 × 403:** registro de **outra academia** responde 404, como se não existisse. O 403 é para quem é da academia, mas não tem o papel.
- **Atenção, Diogo — escolhas minhas, fáceis de mudar** (é uma linha de decorator por rota):
  - excluir aluno só o dono, por causa da LGPD (tarefa 4.3 da sua lista diz o mesmo);
  - recepção pode mexer em planos e preços;
  - instrutor pode criar exercício e ficha, mas não cadastrar aluno.
- **O painel do instrutor** (`painel/instrutor.html` do front) ainda não foi ligado. Até lá o instrutor vê "Painel do instrutor: em construção", em vez dos números da academia.
- **Hoje não há como existir um instrutor ou uma recepção**: o convite de equipe é a `back-13`. Os papéis já estão testados, à espera dela.

### 5. Exercício com dono (o que faltava da tarefa 3.1)

- **Antes:** um catálogo único. Qualquer academia logada editava e apagava os exercícios de todas.
- **Depois:** `exercicio.conta_id`, que aceita vazio.
  - **vazio** = catálogo padrão do sistema: todas as academias usam, nenhuma edita;
  - **preenchido** = exercício criado por aquela academia: só ela vê, edita e apaga.
- **Efeito nos exercícios que já existem:** viram catálogo padrão. Continuam aparecendo para todos e nas fichas, mas **ninguém mais consegue editá-los ou apagá-los pela tela** (a tela antiga ainda mostra os botões; o clique dá 404). Para mudar o catálogo padrão, por enquanto, só direto no banco.

### 6. E-mail e CPF de aluno únicos por academia (tarefa 3.5)

- **Antes:** `unique=True` em `alunos.email` e `alunos.cpf`: únicos no banco inteiro. Um aluno que treina em duas academias travava o cadastro na segunda.
- **Depois:** únicos dentro da conta: `uq_alunos_conta_id_email` e `uq_alunos_conta_id_cpf`.
- **Também corrigido:** ao editar um aluno, a checagem de "e-mail já cadastrado" olhava todas as academias e, pela mensagem, revelava que o e-mail existia em outra. Agora olha só a própria conta.

### 7. Cadastro aberto fechado (decisão do Diogo, item 9)

- **Antes:** qualquer pessoa na internet abria `/instrutores/cadastro/`, preenchia nome, e-mail e senha e saía com uma conta nova, já logada.
- **Depois:** a rota responde 404. O endpoint continua existindo porque o template antigo de login tem um link para ele.
- **Como criar uma academia agora:** `flask criar-conta` no servidor. O comando pergunta o nome da academia, o nome e o e-mail do dono e a senha (duas vezes, sem mostrar na tela).
- **O Adauto quer que os clientes se cadastrem sozinhos no lançamento.** Isso volta pela tela nova "Criar conta", na `back-13`, com limite de tentativas e e-mail funcionando.

### 8. Nome da academia e papel na tela

- **Antes:** `academia.nome` era o texto fixo "Minha academia", e todo usuário aparecia como dono.
- **Depois:** vêm de `contas` e de `instrutores.papel`.
- **Ainda não há tela para mudar o nome da academia.** É a tela de Configurações (`back-12`). Por enquanto o nome é o que a migration ou o `flask criar-conta` gravou.

## A migration

Arquivo: `migrations/versions/b06c0a1e2f30_contas_e_papeis.py`. Foi escrita à mão, porque além de mudar a estrutura ela **move dados**.

**O que faz, na ordem:**

0. Confere que não há aluno nem plano com `instrutor_id` vazio. Se houver, **para antes de mexer em qualquer coisa** e diz quantos são.
1. Cria a tabela `contas`.
2. Cria as colunas novas, ainda aceitando vazio.
3. Para cada usuário existente, cria uma conta chamada "Academia de *Nome Sobrenome*" e liga a ela os alunos, planos e pagamentos dele. Todo usuário existente vira `proprietario`. Os exercícios ficam sem conta (catálogo padrão).
4. Torna `conta_id` obrigatório, cria chaves estrangeiras e índices, e troca os únicos de e-mail e CPF.

**Downgrade:** desfaz tudo e apaga `contas`. Alunos, planos e pagamentos continuam, porque `instrutor_id` nunca foi mexido. Perde-se o que tiver sido configurado na conta. Se duas academias tiverem cadastrado o mesmo e-mail ou CPF depois do upgrade, o downgrade falha até as repetições serem resolvidas.

**Como rodar** (em banco de desenvolvimento; faça backup antes se houver dado que importe):

```bash
flask db upgrade
```

**Atenção, Diogo — dois pontos:**

- **Quem tem dois usuários que são da mesma academia** no banco local vai ficar com duas contas, uma para cada. A migration não tem como saber que eram a mesma academia. Juntar é um `UPDATE` no `conta_id`.
- **As migrations antigas não rodam do zero num Postgres vazio.** Descobri ao testar: `flask db upgrade` num banco novo falha numa migration anterior, ao mudar o tipo de `treino.repeticoes` (`coluna "repeticoes" não pode ser convertida automaticamente para tipo integer`). Não é desta branch e não corrigi. Precisa ser resolvido antes do primeiro deploy, senão não há como criar o banco de produção só com `flask db upgrade`. Está no roadmap, na branch de produção.

## Como foi testado

- **`pytest`: 111 de 111.** Os 56 novos (`tests/test_contas.py`) cobrem:
  - dono, recepção e instrutor veem os mesmos alunos; aluno cadastrado pela recepção aparece para o dono;
  - outra academia continua sem ver nada;
  - o instrutor recebe 403 em 16 combinações de rota e método, e entra em 7 telas que são dele;
  - a recepção passa onde o instrutor é barrado; só o dono exclui aluno;
  - o instrutor não vê nenhum número do painel;
  - gestão da equipe: quem edita quem, o dono não se exclui, usuário de outra academia dá 404;
  - o cadastro aberto responde 404 e não cria nada;
  - exercício: catálogo padrão × próprio × de outra academia;
  - e-mail e CPF: repetidos entre academias, sim; na mesma academia, não;
  - nome da academia e papel aparecem no painel;
  - `flask criar-conta`: cria, recusa e-mail repetido, não mostra a senha, e o dono criado consegue entrar.
- Os 55 testes das branches anteriores continuam passando. Só os utilitários de teste mudaram, para criar a conta de cada usuário.
- **A migration, em Postgres de verdade:** um script cria um banco temporário no Postgres local, testa e apaga. 25 checagens, todas passando:
  - parte do estado da `main` com dados de duas academias;
  - com um aluno sem dono, a migration para e não deixa nada pela metade;
  - cada usuário ganha a sua conta; alunos, planos e pagamentos vão para a conta certa;
  - `conta_id` obrigatório onde deve; únicos trocados;
  - **`flask db check` não acusa diferença** entre o banco migrado e o `models.py`;
  - downgrade volta ao estado anterior sem perder linha; upgrade de novo funciona.
- **Navegador (Playwright):** painel 66 de 66; login 60 de 60 (uma das três rodadas do login falhou num passo de popup por tempo de espera; as outras duas passaram inteiras, e a tela de login não foi tocada por esta branch).
- **Não testado:** a migration em SQLite (os testes usam `create_all`, não migrations) e em MySQL.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Seção da skill | Situação depois desta branch |
|---|---|
| §1 Tabela de negócio com o discriminador de conta **NOT NULL** + FK | Feito para alunos, planos e pagamentos. Fichas e treinos herdam pelo aluno. Exercício aceita vazio de propósito (catálogo). |
| §1 Nunca `Model.query.get(id)` vindo da URL | Não sobra nenhum em rota. Os dois `get_or_404` de `InstrutorService` só são chamados depois de a rota conferir a conta. |
| §1 Teste "conta A pede o id da conta B → 404" | Mantidos os da `back-03` e ampliados para usuários e exercícios. |
| §2 Rota checa o papel no servidor | Feito, com tabela acima e teste por rota. |
| §2 Papel é coluna do usuário, nunca inferido de formulário | Feito. O campo `perfil` do popup de login continua sem dar permissão nenhuma. |
| §3 Cadastro sem controle | Fechado. |
| §3 Limite de tentativas, sessão com prazo | Continua faltando; `back-18`. |

## Como revisar

```bash
git fetch origin
git diff origin/back-05-repo-e-config..origin/back-06-contas-e-papeis -- app/models.py migrations   # comece por aqui
git diff origin/back-05-repo-e-config..origin/back-06-contas-e-papeis -- app/helpers
git diff origin/back-05-repo-e-config..origin/back-06-contas-e-papeis -- app/services app/blueprints
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests -q
```

## Riscos

- **É a mudança mais funda até agora:** troca a coluna pela qual o sistema inteiro isola as academias. A proteção é o conjunto de testes "conta A × conta B", que percorre as rotas.
- **Depois do `git pull`, o app não sobe sem rodar a migration**: o código passa a exigir `conta_id`.
- **Ninguém cria conta pela internet** até a `back-13`. Para o lançamento com auto-cadastro, ela é obrigatória.
- **O catálogo de exercícios fica congelado** para edição pela tela.
- **O instrutor fica sem painel** até a tela dele ser ligada.
