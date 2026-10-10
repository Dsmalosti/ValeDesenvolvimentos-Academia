# back-08-planos — as telas de planos do front novo funcionando com o banco

| | |
|---|---|
| **Branch** | `back-08-planos` |
| **Sai de** | `front-04-planos` (que só traz os 3 templates de `planos/`, copiados do Drive) |
| **Data** | 10/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefas da lista "Tarefas do backend — Diogo"** | 4.1 (rotas com os nomes do front), 4.3 (formato dos campos), 5.4 (valor digitado como `1.234,56`) |
| **Decisões do Diogo usadas** | item 1 (migrations: sim) |
| **Tem migration** | **Sim:** `migrations/versions/b08c3d4e5f60_avaliacoes_incluidas_no_plano.py`. Só acrescenta 1 coluna em `planos`, preenchida com 0. Não move nem apaga dado. |

## Resumo

O menu "Planos" do layout novo levava, por uma ponte temporária, à tela antiga. Agora abre as telas novas: **lista** em cartões com os números de cada plano (alunos, quanto rendeu no mês), **criar**, **editar** e **pausar/reativar**. No computador o formulário fica num painel ao lado da lista; no celular é página inteira.

As telas antigas de planos (`/planos/listar/`, `/planos/criar/` etc.) continuam no ar, porque outras telas antigas ainda têm links para elas.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/blueprints/planos/routes.py` | As pontes `lista` e `novo` viraram rotas de verdade; entraram `editar` e `alternar`. As rotas antigas, no começo do arquivo, não foram tocadas. |
| `app/services/plano_tela_service.py` | **Novo.** Números de cada cartão, validação do formulário e gravação. |
| `app/services/painel_service.py` | Função nova `planos_com_faturamento()` e um parâmetro (`todos`) na função que já calculava o gráfico "De onde vem o faturamento". Nenhum número do painel mudou. |
| `app/models.py` | 1 coluna nova em `Plano`: `avaliacoes_incluidas`. |
| `migrations/versions/b08c3d4e5f60_avaliacoes_incluidas_no_plano.py` | **Novo.** A migration da coluna. |
| `app/blueprints/alunos/routes.py` | Só um comentário (o exemplo de ponte citava `planos.lista`, que deixou de ser ponte). |
| `tests/test_planos.py` | **Novo.** 26 testes. |
| `tests/test_painel.py` | Saíram os 2 casos que conferiam as pontes de planos. |
| `tests/navegador/planos_navegador.py` | **Novo.** Teste das telas num navegador de verdade. |
| `tests/navegador/painel_navegador.py` | O passo "menu Planos leva à tela antiga" virou "abre a lista nova"; a conferência de ponte passou a usar `/exercicios`. |

Nenhum template foi alterado nesta branch.

## Cada mudança: antes, depois e por quê

### 1. Rotas com os nomes do front (tarefa 4.1)

| Endereço | Endpoint | Quem pode | Antes |
|---|---|---|---|
| `GET /planos` | `planos.lista` | todos (instrutor sem os valores de faturamento) | ponte para `/planos/listar/` |
| `GET, POST /planos/novo` | `planos.novo` | dono e recepção | ponte para `/planos/criar/` |
| `GET, POST /planos/<id>/editar` | `planos.editar` | dono e recepção | não existia com este nome |
| `POST /planos/<id>/alternar` | `planos.alternar` | dono e recepção | não existia |

`GET /planos?editar=<id>` abre a lista com o painel lateral já preenchido (é o botão "Editar" do cartão, no computador). `GET /planos?destaque=<id>` é o link do gráfico do painel: o `app.js` do front faz o cartão piscar; o servidor não precisa fazer nada.

O front novo **não tem botão de excluir plano**, só de pausar. A exclusão antiga (`/planos/excluir/<id>`) continua existindo na tela antiga.

### 2. Os números de cada cartão vêm do mesmo lugar que o painel

Cada cartão mostra quantos alunos ativos estão no plano, quanto ele recebeu no mês e quanto isso representa do faturamento. Essa conta já existia no painel (gráfico "De onde vem o faturamento"). Em vez de repetir a conta, a tela de planos **chama a mesma função**, para as duas telas nunca mostrarem números diferentes. A única diferença: o gráfico esconde plano pausado sem aluno, e a tela de planos mostra todos (por isso o parâmetro `todos`).

Ordem dos cartões: ativos primeiro, depois os pausados; dentro de cada grupo, por nome. Não ordenei por faturamento para os cartões não trocarem de lugar de um dia para o outro.

### 3. Formulário conferido no servidor (tarefas 4.3 e 5.4)

- **Nome:** obrigatório, até 100 letras, e **não pode repetir dentro da academia** (sem diferenciar maiúscula). Dois planos com o mesmo nome ficariam iguais na hora de matricular. Esta regra não existia no front de exemplo; se não quiser, é uma linha.
- **Valor:** no formato brasileiro, `1.234,56` (a máscara do front já entrega assim). Maior que zero. O formulário antigo esperava `1234.56` e **recusaria todo valor digitado no front novo**.
  O servidor **não tenta adivinhar** outros formatos: `149.90` é recusado com aviso. O front de exemplo simplesmente tirava os pontos, e esse valor seria gravado como R$ 14.990,00.
- **Duração:** de 1 a 1095 dias (o mesmo limite do campo no front).
- **Descrição:** opcional, até 500 letras.
- **Plano ativo:** o interruptor manda `ativo=1` quando ligado e não manda nada quando desligado.
- **Avaliação física inclusa:** 0, 1, 2 ou 4. Esse campo só existe no formulário do celular. Quando o formulário vem do painel do computador (sem o campo), **o valor gravado não muda**.

Com erro, a página do formulário volta com o que foi digitado e nada é gravado.

### 4. Coluna nova `planos.avaliacoes_incluidas`

O template do front traz o campo e avisa no comentário: "se o backend adotar a coluna". Adotei, porque sem ela a pessoa escolheria "2 avaliações no plano" e a escolha sumiria sem aviso. Nesta branch o número é só **guardado e mostrado**; quem vai usar é o módulo de avaliações.

### 5. Pausar em vez de excluir

`alternar` troca `ativo`. Plano pausado **some do cadastro de aluno** e **continua nos alunos que já estão nele** (isso já estava pronto na `back-07`). Mudar o valor de um plano não mexe no que já foi pago: cada pagamento guarda o próprio valor.

### 6. O instrutor consulta, mas não vê o dinheiro

O instrutor abre a lista e vê nome, preço e duração. A participação no faturamento e o ticket médio chegam zerados para ele. Criar, editar e pausar respondem 403.

## A migration

`b08c3d4e5f60_avaliacoes_incluidas_no_plano.py`, depois da `b07a1f2e3d40`.

- **Sobe:** acrescenta `avaliacoes_incluidas` (número, obrigatório, padrão 0). Os planos que já existem ficam com 0, "nenhuma, cobrada à parte".
- **Desce:** remove a coluna.
- **Depois do pull, rodar `flask db upgrade`**: sem isso, toda tela que lê planos dá erro (painel, alunos, planos).

## Como foi testado

- **`pytest`: 179 de 179** (26 novos em `tests/test_planos.py`). Cobre: lista com os números, os números da tela iguais aos do gráfico do painel, painel lateral preenchido, criar (página e painel), 12 formulários inválidos, HTML no nome, editar, plano de outra academia (404), instrutor (403 e sem dinheiro), pausar e reativar, plano pausado fora do cadastro de aluno.
- **Migration num Postgres temporário** (criado e apagado pelo script): 12 checagens. Sobe, o plano antigo fica com 0, plano inserido sem a coluna recebe 0, `flask db check` sem diferença, desce, sobe de novo.
- **Navegador (Playwright):** planos **31 de 31**, alunos 30 de 30, painel 74 de 74, login 60 de 60. Celular de 390 px com toque (claro) e computador de 1440 px (escuro): abrir pelo menu, enviar vazio (o navegador segura), a máscara de dinheiro, nome repetido (o servidor recusa e devolve o que foi digitado), criar, editar, pausar, conferir que o pausado sumiu do cadastro de aluno, reativar, plano em destaque. Fotos abertas e conferidas.
- **Varredura de todas as rotas GET por papel**, comparada com a `front-04-planos`: só mudaram as rotas de planos acima. Os dois erros 500 antigos (`/instrutores/painel/` e `/fichas/editar/<id>`) continuam iguais dos dois lados.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Como está | Evidência |
|---|---|---|
| Isolamento entre academias | Toda consulta passa por `da_conta(...)`. Plano de outra academia: 404 em `editar` e `alternar`; `?editar=<id de fora>` é ignorado; a lista não mostra plano de fora. | `test_plano_de_outra_academia_da_404`, `test_lista_com_editar_preenche_o_painel_lateral`, `test_lista_mostra_os_planos_da_academia_com_os_numeros` |
| Papéis no servidor | `papel_requerido` em `novo`, `editar`, `alternar`; dinheiro zerado para o instrutor | `test_instrutor_consulta_os_planos_mas_nao_ve_o_dinheiro` |
| CSRF | Formulários com `csrf_token`; `alternar` só por POST | `test_alternar_pausa_e_reativa_sem_apagar` (GET responde 405) |
| Dinheiro | `Decimal` do começo ao fim da gravação (coluna `Numeric(10,2)`); formato conferido antes de converter | `test_criar_plano`, casos de valor em `test_plano_invalido_avisa_e_nao_grava` |
| HTML digitado pelo usuário | O Jinja escapa | `test_nome_com_html_nao_vira_codigo_na_tela` |
| SQL | Só ORM | — |

## Como revisar

```bash
git fetch origin
git diff origin/front-04-planos..origin/back-08-planos --stat
git diff origin/front-04-planos..origin/back-08-planos -- app/
```

Ordem de leitura sugerida: `models.py` e a migration, `painel_service.py` (a função nova fica logo antes de `_faturamento_por_plano`), `plano_tela_service.py` (a função `validar` é o centro), `planos/routes.py`.

## Riscos

- **Quem der pull sem rodar `flask db upgrade` vê erro em toda tela que lê planos.**
- **Nome de plano não pode mais repetir na academia** (só nas telas novas). Se já houver dois planos com o mesmo nome, nada quebra; ao editar um deles, o sistema pede para trocar o nome.
- **Os números do cartão seguem a regra do painel:** o pagamento conta para o plano em que o aluno está **hoje**. Se o aluno trocou de plano no meio do mês, o que ele pagou aparece no plano novo. Resolver isso de vez depende de o pagamento guardar o plano (assunto da cobrança, `back-09`).
- **"1 alunos":** o texto do cartão vem do template do front, que não tem singular. É ajuste de front (no Drive), não de backend.
- **Personal (pacotes de sessões):** o front tem uma variante da tela para personal. Não entrou aqui; é a `back-17`.
