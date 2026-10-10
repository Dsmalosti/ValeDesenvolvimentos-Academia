# back-07-alunos — as telas de alunos do front novo funcionando com o banco

| | |
|---|---|
| **Branch** | `back-07-alunos` |
| **Sai de** | `front-03-alunos` (que só traz os templates de `alunos/`, copiados do Drive) |
| **Data** | 10/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefas da lista "Tarefas do backend — Diogo"** | 4.1 (rotas com os nomes do front), 4.3 (datas em `dd/mm/aaaa`), 4.4 (inativar em vez de excluir) |
| **Decisões do Diogo usadas** | item 1 (migrations: sim), item 8 (aluno continua com `ativo` sim/não) |
| **Tem migration** | **Sim:** `migrations/versions/b07a1f2e3d40_colunas_novas_do_aluno.py`. Só acrescenta 4 colunas vazias em `alunos`. Não move nem apaga dado. |

## Resumo

O menu "Alunos" do layout novo levava, por uma ponte temporária, à tela antiga. Agora abre as telas novas: **lista** com busca, filtros e paginação, **cadastro** (popup no computador, página inteira no celular), **perfil do aluno**, **edição**, **busca ao vivo**, **exportar a lista** e **desativar**.

As telas antigas de alunos (`/alunos/listar/`, `/alunos/cadastro/` etc.) continuam no ar, porque as telas antigas de planos, fichas e pagamentos ainda têm links para elas. Ninguém chega nelas pelo menu novo.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/blueprints/alunos/routes.py` | As pontes `lista`, `novo`, `detalhe` e `buscar` viraram rotas de verdade; entraram `editar`, `inativar`, `excluir`, `exportar` e `acesso`. As rotas antigas, no começo do arquivo, não foram tocadas. |
| `app/services/aluno_tela_service.py` | **Novo.** Tudo o que as telas precisam: filtros, contagens, paginação, validação do formulário, gravação e CSV. |
| `app/services/situacao_service.py` | **Novo.** A regra "este aluno está ativo, pendente ou inativo e quando vence", que antes morava dentro do `painel_service.py`. Agora o painel e a lista usam a mesma função, para nunca mostrarem números diferentes. |
| `app/services/painel_service.py` | Só perdeu as duas funções que foram para o `situacao_service.py` (e passou a importá-las de lá). Nenhum número do painel mudou. |
| `app/models.py` | 4 colunas novas em `Aluno`. |
| `migrations/versions/b07a1f2e3d40_colunas_novas_do_aluno.py` | **Novo.** A migration das 4 colunas. |
| `app/blueprints/pendentes.py` | Ponte nova `treinos.ficha_aluno` (`/alunos/<id>/ficha`): o botão "Visualizar ficha" do perfil leva à ficha do aluno na tela antiga. |
| `tests/test_alunos.py` | **Novo.** 47 testes. |
| `tests/test_painel.py` | Saíram os 4 casos que conferiam as pontes de alunos (elas deixaram de existir); entrou o da ponte `/alunos/<id>/pagamentos`. |
| `tests/navegador/alunos_navegador.py` | **Novo.** Teste das telas num navegador de verdade (celular e computador). |
| `tests/navegador/painel_navegador.py` | O passo "menu Alunos leva à tela antiga" virou "abre a lista nova"; a conferência de ponte passou a usar o menu Planos. |

Nenhum template foi alterado nesta branch: os de `alunos/` são os do Drive, sem ajuste.

## Cada mudança: antes, depois e por quê

### 1. Rotas com os nomes do front (tarefa 4.1)

| Endereço | Endpoint | Quem pode | Antes |
|---|---|---|---|
| `GET /alunos` | `alunos.lista` | todos | ponte para `/alunos/listar/` |
| `GET /alunos/exportar` | `alunos.exportar` | dono e recepção | não existia |
| `GET, POST /alunos/novo` | `alunos.novo` | dono e recepção | ponte para `/alunos/cadastro/` |
| `GET /alunos/buscar` | `alunos.buscar` | todos | ponte para `/alunos/listar/` |
| `GET /alunos/<id>` | `alunos.detalhe` | todos (instrutor sem a parte de dinheiro) | ponte para `/alunos/editar/<id>` |
| `GET, POST /alunos/<id>/editar` | `alunos.editar` | dono e recepção | não existia com este nome |
| `POST /alunos/<id>/inativar` | `alunos.inativar` | dono e recepção | não existia |
| `POST /alunos/<id>/excluir` | `alunos.excluir` | só o dono | não existia com este nome |
| `POST /alunos/<id>/acesso` | `alunos.acesso` | dono e recepção | não existia. **Ainda não faz nada**: só avisa que o bloqueio de acesso chega com o módulo de frequência |

Continuam como ponte, até a branch de cobrança: `alunos.pagamentos` (extrato) e `alunos.renovar`, que levam às telas antigas de pagamento.

**Por quê as regras ficam no serviço e não na rota:** a rota só confere a conta e o papel e escolhe a resposta. A validação e os filtros ficam em `aluno_tela_service.py`, onde dá para testar sem navegador e reaproveitar (a exportação usa o mesmo filtro da lista, por exemplo).

### 2. Formulário: validação no servidor e datas em `dd/mm/aaaa` (tarefa 4.3)

O front manda as datas como `25/12/1990` e o CPF e o telefone com máscara. O formulário antigo (WTForms) esperava `1990-12-25`, então **todo cadastro feito pelo front novo falharia**. As telas novas não usam o formulário antigo: quem confere é a função `validar`, que devolve os valores prontos e um dicionário `{campo: mensagem}` que o template já sabe mostrar embaixo de cada campo.

O que o servidor confere (a conferência do navegador é só conveniência; quem garante é o servidor):

- **Nome:** nome e sobrenome, até 100 letras.
- **CPF:** os dois dígitos verificadores, a mesma conta que o `app.js` faz no navegador; não pode repetir **dentro da academia** (compara só os números, porque cadastros antigos podem estar sem pontos). É gravado sempre como `000.000.000-00`.
- **Telefone:** pelo menos 10 números (DDD + número).
- **E-mail:** opcional. Se vier, formato válido e sem repetir na academia. Vazio é gravado como "sem valor" e não como texto vazio, senão dois alunos sem e-mail bateriam na regra de "único por academia".
- **Datas:** `dd/mm/aaaa`; nascimento não pode ser no futuro.
- **Plano:** tem de ser **da academia** e estar ativo. Na edição, o aluno pode continuar no plano pausado que já tinha.
- **Forma de pagamento:** `pix`, `debito`, `credito` ou `dinheiro`. **Dia de vencimento:** 1 a 28.
- **Observações:** até 1000 letras. É o único campo que o front não desenha com mensagem de erro, então o aviso dele sai na faixa do topo.

Quando há erro, a página volta com o que a pessoa digitou e nada é gravado.

### 3. Quatro colunas novas em `alunos`

`data_inicio`, `dia_vencimento`, `forma_pagamento` e `observacoes`: são campos que o formulário novo tem e o banco não tinha onde guardar. Os nomes são iguais ao `name` dos campos (regra do contrato). Todas aceitam vazio, então os alunos que já existem continuam como estão.

Nesta branch elas são só **guardadas e mostradas** no perfil. Quem vai usar `dia_vencimento` e `forma_pagamento` para calcular cobrança é a branch de cobrança.

### 4. Desativar em vez de excluir (tarefa 4.4)

- **Desativar** (`inativar`): marca `ativo = False`. Não apaga nada; fichas e pagamentos ficam.
- **Excluir** (`excluir`): só o dono. Se o aluno tem ficha ou pagamento, o banco recusa e a tela avisa "desative em vez de excluir".

Antes, a tela antiga só oferecia o botão de excluir e o de trocar o status.

### 5. O instrutor vê o aluno, mas não o dinheiro

O instrutor abre a lista, a busca e o perfil. Não cadastra, não edita, não desativa, não exporta (403 no servidor, não só botão escondido). No perfil, o histórico de pagamentos e o total pago chegam vazios para ele.

### 6. Exportar a lista em CSV

Respeita os filtros da tela e **só leva alunos da academia logada**. Separado por ponto e vírgula e com a marca de acentos, que é como o Excel em português abre certo.

Cuidado a mais: se o texto de uma célula começa com `=`, `+`, `-` ou `@`, o Excel o executa como **fórmula**. Um aluno cadastrado com o nome `=HYPERLINK(...)` viraria um link clicável na planilha do dono. Essas células saem com um apóstrofo na frente, que faz o Excel tratá-las como texto.

## A migration

`b07a1f2e3d40_colunas_novas_do_aluno.py`, depois da `b06c0a1e2f30`.

- **Sobe:** acrescenta as 4 colunas em `alunos`, vazias.
- **Desce:** remove as 4 colunas (o que tiver sido digitado nelas se perde).
- **Depois do pull, o app só funciona depois de `flask db upgrade`**: o modelo passa a pedir colunas que o banco ainda não tem, e qualquer tela que leia alunos daria erro.

## Como foi testado

- **`pytest`: 155 de 155** (47 novos em `tests/test_alunos.py`). Banco SQLite descartável. Cobre: lista, cada filtro, paginação, cadastro válido, 17 cadastros inválidos (um por regra), texto com HTML no nome (não é executado), perfil, aluno de outra academia (404), o que o instrutor não pode (403), edição, desativar, excluir com e sem histórico, CSV (filtro, isolamento e fórmula) e busca ao vivo.
- **Migration num Postgres temporário** (criado e apagado pelo script; nunca o banco do `.env`): 11 checagens. Sobe, o aluno antigo continua igual, `flask db check` diz que banco e `models.py` batem, desce, sobe de novo.
- **Navegador (Playwright):** alunos **30 de 30**, painel **70 de 70**, login **60 de 60**. Celular de 390 px com toque (tema claro) e computador de 1440 px (tema escuro): abrir pelo menu, enviar vazio (o navegador segura e nada vai ao servidor), CPF com dígito errado, CPF repetido (o servidor recusa e devolve o que foi digitado), salvar, perfil, editar, busca ao vivo, desativar; sem "None" na tela, sem rolagem lateral, console sem erro, nenhum arquivo 404. As fotos das telas foram abertas e conferidas.
- **Varredura de todas as rotas GET, logado como dono, recepção e instrutor, com dados**, comparada com a `front-03-alunos`: as únicas diferenças são as rotas de alunos acima. Nenhuma rota que funcionava parou. Dois erros 500 **que já existiam** aparecem dos dois lados: `/instrutores/painel/` (já anotado no roadmap) e `/fichas/editar/<id>` (achado novo, anotado no roadmap; é tela antiga).

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Como está | Evidência |
|---|---|---|
| Isolamento entre academias | Toda consulta passa por `da_conta(...)`. Aluno de outra academia responde 404 em `detalhe`, `editar`, `inativar`, `excluir`, `acesso`. Plano de outra academia não é aceito no formulário. CSV e busca só trazem a própria academia. | `test_perfil_de_outra_academia_da_404`, `test_lista_nao_mostra_aluno_de_outra_academia`, `test_exportar_csv_nao_leva_aluno_de_outra_academia_nem_formula`, caso `DE_OUTRA_CONTA` |
| Papéis no servidor | `papel_requerido` em `novo`, `editar`, `inativar`, `excluir`, `exportar`, `acesso` | `test_instrutor_nao_cadastra_nem_exporta` |
| CSRF | Os formulários mandam `csrf_token` e o `CSRFProtect` do app confere todo POST. Desativar e excluir são só POST. | `test_nenhuma_rota_get_apaga_ou_altera_dados` (em `test_isolamento.py`) continua passando |
| Validação no servidor | Seção 2 acima | `test_cadastro_invalido_avisa_e_nao_grava` |
| HTML digitado pelo usuário | O Jinja escapa; nenhum `\|safe` em dado de aluno | `test_nome_com_html_nao_vira_codigo_na_tela` |
| SQL | Só ORM, sem texto montado à mão | — |
| Planilha | Fórmulas neutralizadas | seção 6 |

Ficam para as branches de segurança, e não pioraram aqui: limite de tamanho de envio (`MAX_CONTENT_LENGTH`), rate limit e headers (`back-18`); exportar e apagar os dados de um aluno a pedido e o cuidado com o campo de observações (`back-19-lgpd`).

## Como revisar

```bash
git fetch origin
git diff origin/front-03-alunos..origin/back-07-alunos --stat
git diff origin/front-03-alunos..origin/back-07-alunos -- app/
```

Para rodar: `flask db upgrade` (num banco de teste) e depois `.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests -q`. Ordem de leitura sugerida: `models.py` e a migration (6 linhas cada), `situacao_service.py`, `aluno_tela_service.py` (a função `validar` é o centro), `alunos/routes.py`.

## Riscos

- **Quem der pull sem rodar `flask db upgrade` vê erro em toda tela que lê alunos**, inclusive o painel.
- **O servidor passou a conferir os dígitos do CPF.** Um aluno antigo gravado com CPF inventado (de teste) não consegue ser salvo na edição sem corrigir o CPF. O navegador já barrava isso antes de enviar, pela regra do próprio front; agora o servidor faz o mesmo.
- **Reativar um aluno desativado ainda é pela tela antiga** (`/alunos/listar/`, botão de status). O front novo não tem esse botão. Vale decidir se entra um.
- **A foto do aluno não é gravada.** O formulário do celular tem o campo, mas o servidor ignora o arquivo. Está combinado para depois do lançamento.
- **O botão "Bloquear" do perfil só mostra um aviso.** A função chega com a frequência.
- **Depois de cadastrar, o desenho do front leva direto para "receber a primeira mensalidade".** Sem a cobrança nova, o cadastro termina no perfil do aluno. Volta ao desenho original na branch de cobrança.
- **O instrutor vê na lista quem está com pagamento pendente** (só a etiqueta, sem valores). Se a academia não quiser isso, é uma mudança pequena.
- **Observações é texto livre e o próprio front sugere "restrição médica".** Isso é dado de saúde, que a LGPD trata como sensível. Fica anotado para a `back-19-lgpd` e para a política de privacidade.
