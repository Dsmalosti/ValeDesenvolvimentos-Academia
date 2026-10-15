# back-09-cobranca — cobrança, renovação, diária avulsa e extrato

| | |
|---|---|
| **Branch** | `back-09-cobranca` |
| **Sai de** | `front-05-cobranca` (que só traz os 3 templates da cobrança, copiados do Drive) |
| **Data** | 12/10/2026 (a proposta de esquema é de 10/10/2026) |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefa** | 5.2 da lista "Tarefas do backend — Diogo": cobrança, renovação e diária |
| **Esquema** | Aprovado pelo Diogo no PR #22: "ok" nas 6 perguntas (seção 7). O primeiro commit desta branch foi só a proposta; o código veio depois do OK. |
| **Tem migration** | **Sim, e é a mais delicada até aqui:** `migrations/versions/b09d5e6f7a80_cobrancas_e_pagamentos.py`. Cria `cobrancas` e **converte a tabela `pagamentos`** para o formato novo. Leia a seção 4 antes de rodar. |

## Resumo

Até aqui o sistema só sabia registrar "o aluno pagou". Agora existe a **cobrança** (o que se deve, e que pode ficar em aberto) e o **pagamento** (o que entrou, com quem confirmou e como).

O que passa a funcionar nas telas novas:

- depois de cadastrar um aluno, a recepção vai direto **receber a primeira mensalidade**, ou toca em "Cobrar depois";
- **receber** em PIX, débito, crédito ou dinheiro. No lançamento **toda confirmação é manual, inclusive o PIX**: a recepção confere e confirma, e o sistema guarda quem confirmou e a que horas (decisão do Adauto em 12/10/2026; pagamento pelo próprio sistema fica para depois);
- **renovar**, trocando ou não de plano, com o novo vencimento já calculado;
- **diária avulsa** de visitante, sem cadastro de aluno;
- **extrato** do aluno, na tela e em planilha.

## 1. Como é hoje e por que muda

Hoje existe uma tabela só, `pagamentos`: `aluno_id`, `instrutor_id`, `conta_id`, `valor`, `data_pagamento`, `data_vencimento`, `forma_pagamento`, `observacao`. Cada linha é "o aluno pagou tanto, e por isso está em dia até tal data".

O que ela não consegue representar, e o front novo precisa:

1. **Cobrança em aberto.** O front tem "Cobrar depois" e "Renovar sem cobrar". Hoje só existe o que já foi pago.
2. **Quem confirmou e como.** A regra do front é "toda confirmação mostra a origem": o banco avisou (automático) ou alguém da recepção marcou (manual, com o nome).
3. **Diária avulsa.** Entrada de caixa de visitante, sem aluno. Hoje `aluno_id` é obrigatório.
4. **O plano da época.** Hoje o faturamento por plano usa o plano em que o aluno está *hoje*. Se ele trocou de plano, o histórico muda junto.

A proposta parte das tabelas do `Esquema-Backend.md` (seção 3), com os ajustes que a `back-06` trouxe (existe `conta_id`) e os que a diária avulsa exige. Onde eu mudei em relação àquele documento está marcado com **(mudou)**.

## 2. Tabela `cobrancas` (nova)

Uma cobrança é "o que se deve": nasce na matrícula, na renovação ou na diária avulsa, e fica `pendente` até ser paga.

| Coluna | Tipo | Vazio? | O que é |
|---|---|---|---|
| `id` | Integer | não | chave |
| `conta_id` | Integer, FK `contas.id` | não | a academia dona da cobrança. É por ela que uma academia não vê a outra. **(mudou: o documento usava `instrutor_id` para isso; desde a `back-06` é `conta_id`)** |
| `aluno_id` | Integer, FK `alunos.id` | **sim** | o aluno. Vazio só na diária avulsa. **(mudou: era obrigatório)** |
| `plano_id` | Integer, FK `planos.id` | **sim** | o plano **da época** da cobrança. Vazio só na diária avulsa. **(mudou: era obrigatório)** |
| `tipo` | String(20) | não | `matricula`, `renovacao` ou `diaria`. **(nova)** O front mostra textos diferentes para cada um. |
| `nome_visitante` | String(100) | sim | nome de quem pagou a diária avulsa, se informado. **(nova)** |
| `valor` | Numeric(10,2) | não | o valor **congelado** na hora em que a cobrança nasce. Mudar o preço do plano depois não altera cobrança antiga. |
| `data_inicio` | Date | não | início do período que esta cobrança cobre. **(nova)** Matrícula: a data de início do aluno. Renovação: o vencimento atual do aluno, ou hoje, se já venceu (é a conta que o front de exemplo faz). Diária: hoje. |
| `data_vencimento` | Date | sim | fim do período: `data_inicio` + duração do plano. É até quando o aluno fica em dia **depois de pagar**. Vazio na diária. |
| `status` | String(20) | não | `pendente`, `paga` ou `cancelada`. Texto conferido pela aplicação (não `db.Enum`), para poder mudar sem migration. **(mudou: sem `atrasada`, ver pergunta 1)** |
| `data_geracao` | DateTime | não | quando a cobrança foi criada |
| `instrutor_id` | Integer, FK `instrutores.id` | sim | **quem** criou a cobrança (mesmo sentido que essa coluna tem nas outras tabelas desde a `back-06`) |

**Índice:** `(conta_id, status, data_vencimento)`, que é a combinação que o painel consulta.

### Regras que saem dessa tabela

- **Vencimento do aluno** = a maior `data_vencimento` entre as cobranças **pagas** dele. É a mesma regra de hoje, só que lida das cobranças.
- **Aluno pendente** = aluno ativo que (a) tem vencimento anterior a hoje, **ou** (b) tem cobrança `pendente` cujo período já começou. O caso (b) é novo: hoje, quem foi matriculado e não pagou nada aparece como "em dia".
- **Inadimplência do painel** = soma das cobranças pendentes em atraso, mais o valor do plano de quem venceu e não tem cobrança nova (como hoje).
- **Faturamento por plano** = pelo `plano_id` da cobrança, e não mais pelo plano atual do aluno. Diária avulsa aparece numa linha "Avulsos".

## 3. Tabela `pagamentos` (a que existe, com outro formato)

Um pagamento é "o que entrou no caixa": a confirmação de uma cobrança.

| Coluna | Tipo | Vazio? | O que é | De onde vem na migração |
|---|---|---|---|---|
| `id` | Integer | não | chave | o `id` atual é mantido |
| `conta_id` | Integer, FK `contas.id` | não | a academia. Repete o da cobrança de propósito: toda consulta do sistema filtra por essa coluna, e assim nenhuma depende de lembrar do `JOIN`. **(mudou: não estava no documento)** | `conta_id` atual |
| `cobranca_id` | Integer, FK `cobrancas.id` | não | a cobrança que este pagamento quita | a cobrança criada para a linha antiga |
| `forma` | String(20) | não | `pix`, `debito`, `credito` ou `dinheiro` | `forma_pagamento` atual, como estava (a tela antiga gravava `dinheiro`, `pix` ou `cartao`); se estiver vazio, `nao_informada`. `cartao` e `nao_informada` só existem em linha antiga |
| `valor_pago` | Numeric(10,2) | não | quanto entrou. Pode ser diferente do valor da cobrança. | `valor` atual |
| `data_pagamento` | DateTime | não | dia **e hora** (o front mostra "confirmado às 14h32"). **(mudou: hoje é só data)** | a data atual, com hora 00:00 |
| `origem_confirmacao` | String(20) | não | `manual` (alguém da recepção confirmou) ou `webhook` (o banco avisou). No lançamento, sempre `manual`. | `manual` |
| `confirmado_por_instrutor_id` | Integer, FK `instrutores.id` | sim | quem confirmou, quando é manual | `instrutor_id` atual |
| `referencia_externa` | String(100) | sim | código da transação no banco. Fica vazio até existir PIX automático. | vazio |
| `observacao` | Text | sim | anotação livre. **(mantida: já existe hoje e o documento não tinha)** | `observacao` atual |

**Saem da tabela** (passam para a cobrança): `aluno_id`, `instrutor_id`, `valor`, `data_vencimento`, `forma_pagamento`.

## 4. Como a migration funciona

Uma migration só, `b09d5e6f7a80_cobrancas_e_pagamentos.py`, escrita à mão, depois da `b08c3d4e5f60`:

1. Cria `cobrancas`.
2. Para **cada linha** de `pagamentos`, cria uma cobrança `paga`: mesmo aluno e conta; plano = o plano atual do aluno (é a melhor informação que existe); `tipo` = `matricula` para o primeiro pagamento do aluno e `renovacao` para os seguintes; `valor`, `data_vencimento` e quem registrou copiados; `data_inicio` = a data do pagamento.
3. Em `pagamentos`: acrescenta as colunas novas, preenche com os valores da tabela acima, liga cada linha à sua cobrança e só então remove as colunas antigas.
4. **Downgrade:** devolve as colunas antigas a partir da cobrança e apaga `cobrancas`. Pagamento de diária avulsa (sem aluno) não tem como voltar para o formato antigo e é apagado no downgrade; isso fica escrito na migration.

Teste, como nas outras: num Postgres temporário, com pagamentos antigos dentro, conferindo que nenhum valor muda, que `flask db check` não acha diferença, e ida e volta (upgrade, downgrade, upgrade).

Pela resposta 12 do Diogo, não há banco de produção nem dado real: o que existe para converter são dados de teste.

## 5. O que foi feito

### Arquivos

| Arquivo | O que é |
|---|---|
| `app/models.py` | Modelo novo `Cobranca`; `Pagamento` no formato novo; constantes dos valores aceitos (tipos, status, formas). |
| `migrations/versions/b09d5e6f7a80_cobrancas_e_pagamentos.py` | **Novo.** A migration da seção 4. |
| `app/services/cobranca_service.py` | **Novo.** Gerar cobrança, renovar, receber, diária e extrato. |
| `app/blueprints/cobrancas/routes.py` | **Novo.** As rotas `cobrancas.*`. |
| `app/helpers/dinheiro.py` | **Novo.** Ler e escrever valores em reais (`1.234,56`). A leitura nasceu na `back-08`, dentro do serviço de planos; veio para cá para a cobrança usar a mesma. |
| `app/services/situacao_service.py` | A regra de "em dia / pendente" passou a ler as cobranças. Função nova `cobrancas_em_aberto_da_conta()`. |
| `app/services/painel_service.py` | Vencimento e pendência vêm do `situacao_service`; faturamento soma `valor_pago`; faturamento por plano usa o plano **da cobrança**; linha "Avulsos" para as diárias. |
| `app/services/aluno_tela_service.py` | Perfil e lista leem as cobranças; o histórico de pagamentos mostra quem confirmou. |
| `app/services/aluno_service.py` | `excluir_aluno` recusa aluno que tem cobrança (ver "Excluir aluno", abaixo). |
| `app/services/plano_tela_service.py` | Só passou a usar `helpers/dinheiro.py`. |
| `app/blueprints/alunos/routes.py` | `novo` gera a cobrança da matrícula e vai para a tela de receber; `renovar` e `pagamentos` deixaram de ser pontes. |
| `app/blueprints/pagamentos/routes.py` | As 3 telas antigas viraram redirecionamentos (pergunta 4). |
| `app/blueprints/pendentes.py`, `app/__init__.py` | `cobrancas.diaria` e `cobrancas.lembrete_lote` saíram das telas "em construção"; o blueprint novo é registrado. |
| `app/templates/cobranca/receber.html` | **7 ajustes marcados** para o PIX manual (ver seção 8). É o único template alterado. |
| `tests/test_cobrancas.py` | **Novo.** 38 testes. |
| `tests/conftest.py`, `tests/test_alunos.py`, `tests/test_isolamento.py`, `tests/test_painel.py` | Adaptados ao formato novo. |
| `tests/navegador/cobranca_navegador.py`, `tests/navegador/_base.py` | **Novos.** Teste do fluxo no navegador e o ajudante que semeia um pagamento. |
| `tests/navegador/alunos_navegador.py`, `painel_navegador.py`, `planos_navegador.py` | Só a semente de pagamento e, no de alunos, o passo depois de salvar. |

Continuam no repositório, **sem uso**, até o layout antigo sair: `app/blueprints/pagamentos/form.py`, os 3 templates de `app/blueprints/pagamentos/templates/` e `app/services/pagamento_service.py`.

### Rotas

| Endereço | Endpoint | O que faz |
|---|---|---|
| `GET /cobrancas/<id>/receber` | `cobrancas.receber` | a tela única de receber (matrícula, renovação e diária) |
| `POST /cobrancas/<id>/confirmar` | `cobrancas.confirmar` | cria o pagamento e marca a cobrança como paga |
| `GET /cobrancas/<id>/depois` | `cobrancas.depois` | "Cobrar depois": só avisa e sai; a cobrança já está em aberto |
| `GET /cobrancas/<id>/status` | `cobrancas.status` | JSON com o estado (o front consulta) |
| `GET /cobrancas/matricula/<aluno_id>` | `cobrancas.receber_matricula` | leva à cobrança em aberto do aluno; se não houver, à tela de renovar. **Não cria nada** (é GET) |
| `POST /cobrancas/diaria` | `cobrancas.diaria` | cria a cobrança da diária avulsa e leva para receber |
| `GET, POST /alunos/<id>/renovar` | `alunos.renovar` | escolhe o plano e gera a cobrança da renovação |
| `GET /alunos/<id>/pagamentos` | `alunos.pagamentos` | extrato (tela e `?formato=csv`) |
| `POST /cobrancas/<id>/pix`, `/cancelar-pix` | `cobrancas.pix`, `cobrancas.cancelar_pix` | PIX automático: **ainda não existe**. Avisam e voltam para a tela |
| `POST /cobrancas/lembrete` | `cobrancas.lembrete_lote` | cobrança em lote pelo WhatsApp: **ainda não existe** (entra com mensagens) |

Tudo de `cobrancas.*`, mais `alunos.renovar` e `alunos.pagamentos`: só dono e recepção. Instrutor recebe 403.

### Regras (estão no começo de `cobranca_service.py` e de `situacao_service.py`)

- **Um aluno tem no máximo uma cobrança em aberto.** Gerar outra (renovar de novo, mudar de ideia) atualiza a que existe. Sem isso, dois toques em "renovar" criariam duas dívidas.
- **É matrícula enquanto o aluno nunca pagou nada**; depois disso, renovação.
- **Período:** matrícula começa na data de início do aluno; renovação começa no vencimento atual ou, se já venceu, hoje. O fim é o começo mais a duração do plano.
- **Valor congelado** na cobrança.
- **Confirmar duas vezes não cria dois pagamentos** (toque duplo, página recarregada).
- **Quem paga volta a ser aluno ativo**, como no front de exemplo.
- **Valor recebido:** vem do campo `valor_recebido` e é gravado em `valor_pago` (pergunta 5). Vazio = o valor da cobrança. Formato brasileiro; `100.00` é recusado.

### Excluir aluno

Antes, quem impedia apagar um aluno com pagamento era o banco, porque `pagamentos.aluno_id` era obrigatório. Como a cobrança aceita aluno vazio (diária avulsa), o SQLAlchemy passaria a **zerar o aluno das cobranças e apagar o aluno**, transformando o histórico dele em "diárias avulsas". Peguei isso num teste que já existia. Correção em dois lugares: `AlunoService.excluir_aluno` confere antes e recusa, e o relacionamento tem `passive_deletes='all'`, para o SQLAlchemy nunca zerar por conta própria.

## 6. O que NÃO muda

- `alunos`, `planos`, `contas`, `instrutores`: nenhuma coluna.
- Para os dados que já existem, vencimento de cada aluno e total recebido são os mesmos antes e depois da migration (há checagem para os dois no teste da migration).
- As rotas antigas de aluno, plano, ficha e exercício.

## 7. As 6 perguntas e as respostas do Diogo

Todas respondidas com "ok" no PR #22.

| # | Decisão |
|---|---|
| 1 | **Não guardar `atrasada`** no status. É calculado na hora: pendente com data passada. |
| 2 | **Diária avulsa na mesma tabela** `cobrancas`, com `aluno_id` e `plano_id` vazios. |
| 3 | **`conta_id` também em `pagamentos`**, repetindo o da cobrança. |
| 4 | **Telas antigas de pagamento viram redirecionamentos**; os arquivos ficam até o layout antigo sair. |
| 5 | Coluna **`valor_pago`**; a rota converte o campo `valor_recebido` do front. |
| 6 | Pagamento antigo sem forma: **`nao_informada`**. Detalhe que apareceu ao escrever a migration: a tela antiga gravava `cartao` (sem separar débito de crédito). Esse valor é **mantido como estava** e aparece como "Cartão" no extrato. |

## 8. Ajustes no template `cobranca/receber.html` (diferem do Drive)

O template do Drive só conhece o PIX automático: com ele desligado, a opção PIX fica desabilitada ("Não configurado") e a tela convida a "Ligar o PIX agora". Como o PIX do lançamento é manual, o template do **repositório** tem 7 ajustes, todos marcados com `{# [back-09-cobranca] ... #}` e controlados por uma variável nova, `pix_manual`:

1. `pix_manual` com valor padrão falso (quem não passar a variável vê o comportamento original);
2. a forma que vem escolhida é PIX também quando o PIX é manual;
3. a opção PIX fica habilitada;
4. o texto embaixo de "PIX" é "Você confirma", como nas outras formas;
5. o aviso "PIX ainda não está ligado" e o botão "Ligar o PIX agora" não aparecem;
6. bloco novo "Receber por PIX", com o aviso "Essa confirmação é sua", e o botão "Já recebi o PIX";
7. no computador, o texto "O QR aparece aqui" vira "Confirme depois de receber".

**Para o Adauto:** levar esses 7 ajustes para o front do Drive, senão a próxima cópia do template os apaga.

## 9. Como foi testado

- **`pytest`: 214 de 214** (38 novos em `tests/test_cobrancas.py`). Cobre: tela de receber com PIX manual; confirmar nas 4 formas; não duplicar pagamento; valor recebido diferente; 5 confirmações inválidas; cobrança cancelada; quem paga fica em dia; cobrança que ainda não começou não deixa pendente; painel (recebido e em aberto); reativar ao pagar; não excluir aluno com cobrança (rota nova e antiga); renovar (novo vencimento, troca de plano, sem cobrar, sem empilhar, 5 planos inválidos); valor congelado; faturamento pelo plano da época; diária (válida e 3 inválidas); extrato na tela e em CSV; instrutor 403 em 11 rotas; outra academia 404 em 13 rotas; GET nunca cria cobrança; telas antigas redirecionando.
- **Migration num Postgres temporário** (criado e apagado pelo script; nunca o banco do `.env`): **21 checagens**, com 4 pagamentos antigos de 2 academias dentro. Sobe; cada pagamento ganha a sua cobrança; matrícula e renovação certas; forma vazia vira `nao_informada` e `cartao` fica; **o vencimento de cada aluno e o total recebido são os mesmos de antes**; `flask db check` sem diferença; desce e **os 4 pagamentos voltam idênticos**; o banco volta a bater com o modelo antigo; sobe de novo.
- **Navegador (Playwright):** cobrança **33 de 33**, alunos 32 de 32, planos 31 de 31, painel 74 de 74, login 60 de 60. Celular de 390 px com toque (claro) e computador de 1440 px (escuro): receber com PIX manual, trocar de forma, confirmar, popup de sucesso, perfil em dia, renovar trocando de plano, extrato, renovar sem cobrar, cobrar depois e, no computador, diária avulsa pelo painel. Fotos abertas e conferidas.
- **Varredura de todas as rotas GET por papel**, comparada com a `front-05-cobranca`: mudaram só as rotas desta branch. Os dois erros 500 antigos continuam iguais dos dois lados.

## 10. Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Como está | Evidência |
|---|---|---|
| Isolamento entre academias | Cobrança e pagamento têm `conta_id` e toda consulta passa por `da_conta(...)`. Cobrança ou aluno de outra academia: 404 em 13 rotas, sem alterar nada. Plano de outra academia não serve para renovar. | `test_cobranca_e_aluno_de_outra_academia_dao_404`, caso `DE_FORA` de `test_renovar_com_plano_invalido_nao_gera_nada` |
| Papéis no servidor | `exigir_papel_em` no blueprint inteiro de cobrança (vale para rota futura); `papel_requerido` em renovar e extrato | `test_instrutor_nao_entra_em_nada_de_dinheiro` |
| CSRF e métodos | Confirmar, diária, renovar e PIX são POST, com `csrf_token` nos formulários. Nenhum GET cria ou altera: `receber_matricula` e `depois` só leem. | `test_status_cobrar_depois_e_atalho_da_matricula`, `test_nenhuma_rota_get_apaga_ou_altera_dados` |
| Dinheiro | `Decimal` e `Numeric(10,2)`; formato conferido antes de converter; valor da cobrança nunca vem do formulário (vem do plano) | `test_confirmacao_invalida_nao_quita`, `test_valor_da_cobranca_fica_congelado` |
| Origem da confirmação | Todo pagamento grava `origem_confirmacao` e quem confirmou; nunca um "pago sim/não" solto | `test_confirmar_cria_o_pagamento_e_quita_a_cobranca` |
| Redirecionamento | Nenhuma rota redireciona para endereço vindo do navegador | — |
| Planilha | Células do extrato protegidas contra fórmula, como na lista de alunos | `extrato_csv` |
| SQL | ORM; na migration, SQL com parâmetros | — |

## 11. Como revisar

```bash
git fetch origin
git diff origin/front-05-cobranca..origin/back-09-cobranca --stat
git diff origin/front-05-cobranca..origin/back-09-cobranca -- app/ migrations/
```

Ordem de leitura sugerida: `models.py` (as duas classes), a migration, `situacao_service.py`, `cobranca_service.py`, `cobrancas/routes.py`, e por último os ajustes em `alunos/routes.py` e `painel_service.py`.

Para rodar: **faça backup do banco**, depois `flask db upgrade`.

## 12. Riscos

- **A migration converte a tabela de pagamentos.** Foi testada com ida e volta e dados dentro, mas é a primeira que transforma dado existente desde a `back-06`. Backup antes.
- **O downgrade perde dado novo:** cobranças em aberto deixam de existir e pagamento de diária avulsa é apagado. Está escrito na migration.
- **Mais alunos aparecem como pendentes:** quem é matriculado e fica no "cobrar depois" passa a contar como pendente (antes aparecia "em dia"). É o comportamento certo, mas muda o número do painel.
- **Pagamentos antigos ficam com hora 00:00 e com o plano atual do aluno**, porque o formato antigo não guardava nem a hora nem o plano.
- **Hora do pagamento:** é a hora do servidor. Em produção o servidor precisa estar no fuso de Brasília (variável `TZ`), senão "confirmado às 14h32" sai com 3 horas a mais. Anotado para a `back-20-producao`.
- **Não há estorno nem cancelamento de cobrança pela tela.** O status `cancelada` existe no banco e as telas o respeitam, mas nenhum botão o grava ainda.
- **Comprovante por WhatsApp e impressão**, na tela de sucesso, são botões de demonstração do front.
