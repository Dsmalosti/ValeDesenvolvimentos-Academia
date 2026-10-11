# back-09-cobranca — PROPOSTA de esquema (aguardando o OK do Diogo)

| | |
|---|---|
| **Branch** | `back-09-cobranca` |
| **Sai de** | `front-05-cobranca` (que só traz os 3 templates da cobrança, copiados do Drive) |
| **Data** | 10/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Estado** | **Só proposta.** Nenhuma linha de código, modelo ou migration foi escrita. O Diogo pediu para ver o esquema antes (resposta 10: "B, mostrar o esquema no PR antes"). Quando ele aprovar, este mesmo arquivo vira o doc da branch. |
| **Tarefa** | 5.2 da lista "Tarefas do backend — Diogo": cobrança, renovação e diária |

## Diogo: o que eu preciso de você

Ler as seções 2 e 3 (as duas tabelas) e responder as **6 perguntas da seção 7**. Cada uma já vem com a minha recomendação; basta "ok" ou "prefiro a outra". Depois disso eu escrevo o modelo, a migration e as rotas.

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
| `forma` | String(20) | não | `pix`, `debito`, `credito` ou `dinheiro` | `forma_pagamento` atual; se estiver vazio, `nao_informada` (valor que só existe em linha antiga) |
| `valor_pago` | Numeric(10,2) | não | quanto entrou. Pode ser diferente do valor da cobrança. | `valor` atual |
| `data_pagamento` | DateTime | não | dia **e hora** (o front mostra "confirmado às 14h32"). **(mudou: hoje é só data)** | a data atual, com hora 00:00 |
| `origem_confirmacao` | String(20) | não | `manual` (alguém da recepção confirmou) ou `webhook` (o banco avisou). No lançamento, sempre `manual`. | `manual` |
| `confirmado_por_instrutor_id` | Integer, FK `instrutores.id` | sim | quem confirmou, quando é manual | `instrutor_id` atual |
| `referencia_externa` | String(100) | sim | código da transação no banco. Fica vazio até existir PIX automático. | vazio |
| `observacao` | Text | sim | anotação livre. **(mantida: já existe hoje e o documento não tinha)** | `observacao` atual |

**Saem da tabela** (passam para a cobrança): `aluno_id`, `instrutor_id`, `valor`, `data_vencimento`, `forma_pagamento`.

## 4. Como a migration vai funcionar

Uma migration só (`b09…`), escrita à mão, depois da `b08c3d4e5f60`:

1. Cria `cobrancas`.
2. Para **cada linha** de `pagamentos`, cria uma cobrança `paga`: mesmo aluno e conta; plano = o plano atual do aluno (é a melhor informação que existe); `tipo` = `matricula` para o primeiro pagamento do aluno e `renovacao` para os seguintes; `valor`, `data_vencimento` e quem registrou copiados; `data_inicio` = a data do pagamento.
3. Em `pagamentos`: acrescenta as colunas novas, preenche com os valores da tabela acima, liga cada linha à sua cobrança e só então remove as colunas antigas.
4. **Downgrade:** devolve as colunas antigas a partir da cobrança e apaga `cobrancas`. Pagamento de diária avulsa (sem aluno) não tem como voltar para o formato antigo e é apagado no downgrade; isso fica escrito na migration.

Teste, como nas outras: num Postgres temporário, com pagamentos antigos dentro, conferindo que nenhum valor muda, que `flask db check` não acha diferença, e ida e volta (upgrade, downgrade, upgrade).

Pela sua resposta 12, não há banco de produção nem dado real: o que existe para converter são dados de teste.

## 5. O que o resto da branch vai fazer (depois do OK)

| Endereço | Endpoint | O que faz |
|---|---|---|
| `GET /cobrancas/matricula/<aluno_id>` | `cobrancas.receber_matricula` | cria a cobrança da matrícula (ou reaproveita a pendente) e leva para a tela de receber |
| `GET /cobrancas/<id>/receber` | `cobrancas.receber` | a tela única de receber |
| `POST /cobrancas/<id>/confirmar` | `cobrancas.confirmar` | confirma o recebimento (`forma`, `valor_recebido`) e marca a cobrança como paga |
| `GET /cobrancas/<id>/depois` | `cobrancas.depois` | deixa a cobrança em aberto |
| `GET /cobrancas/<id>/status` | `cobrancas.status` | o front consulta para saber se já foi paga |
| `POST /cobrancas/diaria` | `cobrancas.diaria` | diária avulsa |
| `GET, POST /alunos/<id>/renovar` | `alunos.renovar` | escolhe o plano, calcula o novo vencimento e gera a cobrança |
| `GET /alunos/<id>/pagamentos` | `alunos.pagamentos` | extrato do aluno (tela e CSV) |

Dono e recepção recebem e veem extrato; instrutor não (403), como já é com as outras telas de dinheiro.

**Ficam para depois do lançamento** (decisão já tomada: PIX manual): `cobrancas.pix` e `cobrancas.cancelar_pix` (gerar QR Code e esperar o banco) e o aviso automático do banco. As duas rotas vão existir e responder "PIX automático ainda não disponível", porque o template as cita. Por isso a proposta **não** cria agora colunas de QR Code, validade do código ou identificador do banco: entram quando houver um provedor escolhido, numa migration própria.

`cobrancas.lembrete_lote` (cobrança em lote por WhatsApp) entra com o módulo de mensagens.

## 6. O que NÃO muda

- `alunos`, `planos`, `contas`, `instrutores`: nenhuma coluna.
- Os números do painel continuam os mesmos para os dados de hoje. Vai haver teste comparando antes e depois da migration.
- As telas antigas de pagamento: ver pergunta 4.

## 7. Perguntas para o Diogo

| # | Pergunta | Minha recomendação |
|---|---|---|
| 1 | Guardar `atrasada` no `status`, como estava no `Esquema-Backend.md`? | **Não guardar.** "Atrasada" depende da data de hoje: para ficar certa no banco, precisaria de uma tarefa rodando todo dia. Calcular na hora (pendente + data passada) nunca fica errado. |
| 2 | Diária avulsa na mesma tabela `cobrancas`, com `aluno_id` e `plano_id` vazios, ou numa tabela separada? | **Mesma tabela.** O front usa uma tela única de receber para os três casos, e o faturamento soma tudo junto. O custo é deixar as duas colunas aceitarem vazio; a aplicação exige as duas quando o `tipo` não é `diaria`. |
| 3 | `conta_id` também em `pagamentos`, repetindo o da cobrança? | **Sim.** É a regra da `back-06`: toda tabela de negócio tem `conta_id` e toda consulta passa pelo mesmo filtro. |
| 4 | O que fazer com as telas antigas de pagamento (`/pagamentos/registrar/<aluno>`, `/pagamentos/listar/<aluno>`, `/pagamentos/situacao/`)? Elas usam as colunas que saem. | **Redirecionar** as três para as telas novas (receber, extrato, lista de alunos filtrada por pendentes) e **manter os arquivos** até o layout antigo sair. A alternativa é reescrevê-las para o formato novo, que é trabalho em tela que vai ser apagada. |
| 5 | Nomes das colunas: fico com `forma` e `valor_pago` (do `Esquema-Backend.md`) ou uso os nomes dos campos do formulário do front (`forma` e `valor_recebido`)? | **`valor_pago`**, como no documento que você aprovou. A rota faz a ponte entre `valor_recebido` (campo) e `valor_pago` (coluna), com comentário. |
| 6 | Pagamento antigo sem forma de pagamento: gravar o quê? | **`nao_informada`**, só para linha antiga. Inventar "dinheiro" seria registrar uma coisa que ninguém disse. |

## 8. Pendência do front (Adauto)

O PIX do lançamento é **manual**: a recepção confere no aplicativo do banco e confirma. Mas o template `cobranca/receber.html` **desliga o botão PIX** quando o PIX automático não está ligado ("Não configurado") e só deixa confirmar débito, crédito e dinheiro. Do jeito que está, **não dá para registrar um pagamento em PIX no lançamento**.

O backend vai aceitar `forma=pix` com confirmação manual. Falta o front ter esse caminho: a opção PIX habilitada, com o texto "Você confirma", e o botão de confirmar. É ajuste no front do Drive; depois eu copio de novo.

## 9. Riscos

- **A migration mexe na tabela de pagamentos existente.** É a mais delicada até aqui: por isso o esquema vem antes, e por isso o teste de ida e volta com dados dentro.
- **Mais alunos vão aparecer como pendentes**: quem foi matriculado e nunca pagou passa a ter uma cobrança em aberto (hoje aparece como "em dia"). Isso é o comportamento certo, mas muda o número do painel a partir do primeiro "cobrar depois".
- **Pagamentos antigos ficam com hora 00:00** e com o plano atual do aluno, porque o formato antigo não guardava nem a hora nem o plano.
