# back-17-personal — variante Personal Trainer: pacotes de sessões, saldo e agenda

| | |
|---|---|
| **Branch** | `back-17-personal` |
| **Sai de** | `front-13-personal` (que só traz os 10 templates, copiados do Drive) |
| **Data** | 12/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefa** | 5.11 da lista "Tarefas do backend — Diogo": variante Personal Trainer |
| **Decisões usadas** | D1 (o lançamento inclui personal trainers); A1 (migration na branch, só rodada em banco de teste); D14 (mensagem gratuita). **D12 segue em aberto** e foi implementada como no front (seção 3). |
| **Tem migration** | **Sim:** `migrations/versions/b17f3a4b5c60_personal_pacotes_e_sessoes.py`. Colunas novas (todas aceitam vazio) e a tabela `sessoes`. |
| **Dependência nova** | **Nenhuma.** |

## Resumo

A conta criada como "personal trainer" (em `/criar-conta`) passa a ter o sistema dela:

- **Pacotes** no lugar de planos: o personal vende sessões, não mensalidade.
- **Saldo de sessões** no lugar de vencimento: o aluno "tem 5 sessões", e não "vence dia 10".
- **Agenda de sessões** no lugar do check-in: marcar, marcar presença (abate 1 do saldo), remarcar e cancelar.
- **Painel próprio** (pacotes acabando, sessões de hoje, ticket por pacote), **configurações próprias** (CPF, CREF, locais de atendimento) e a **fila de mensagens** com a sessão de amanhã.

**A conta de academia não muda.** É o mesmo código e as mesmas rotas; cada ponto pergunta "esta conta é de personal?" (`pacote_service.e_personal()`) e só então troca a tela ou a regra. A varredura de rotas com conta de academia só mostrou diferença na agenda (que agora devolve a academia ao painel).

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/models.py` | `Conta.cpf`, `cref`, `locais_ativos`; `Plano.quantidade_sessoes`; `Cobranca.quantidade_sessoes`; modelo novo `Sessao`. |
| `migrations/versions/b17f3a4b5c60_personal_pacotes_e_sessoes.py` | **Novo.** A migration. |
| `app/services/pacote_service.py` | **Novo.** O saldo e o "pacote atual" do aluno. **É o arquivo mais importante da branch.** |
| `app/services/agenda_service.py` | **Novo.** Marcar, concluir, cancelar, repetição semanal, locais. |
| `app/services/personal_service.py` | **Novo.** O que só o painel e as configurações do personal têm. |
| `app/blueprints/agenda/` | **Novo.** As 5 rotas da agenda. |
| `app/services/situacao_service.py` | `linha_do_aluno` ganha o saldo e a regra de "pendente" do personal (`_com_pacote`). |
| `app/services/cobranca_service.py` | A cobrança guarda as sessões da compra; a tela de cobrança fala em pacote. |
| `app/services/plano_tela_service.py`, `app/blueprints/planos/routes.py` | Na conta de personal: formulário de pacote, outros templates, outra palavra nos avisos. |
| `app/blueprints/alunos/routes.py` | `alunos.renovar` na conta de personal: tela e aviso de pacote. |
| `app/blueprints/painel/routes.py` | Conta de personal recebe `personal/painel.html`. |
| `app/blueprints/config/routes.py`, `app/services/config_service.py` | Tela de configurações do personal; `config.salvar` grava o perfil; rota nova `config.locais`; dois textos padrão de mensagem. |
| `app/services/mensagem_service.py` | Na conta de personal: sessão de amanhã no lugar de avaliação de amanhã. |
| `app/services/aluno_tela_service.py`, `app/services/aluno_service.py`, `app/helpers/contexto.py` | Perfil mostra o saldo; aluno com sessão não é excluído; `academia.cpf` e `academia.cref` chegam aos templates. |
| `app/blueprints/pendentes.py`, `app/__init__.py` | Sai a linha "em construção" da agenda; registra o blueprint. |
| `app/templates/personal/painel.html` | **5 ajustes marcados** (seção 8). |
| `tests/test_personal.py` | **Novo.** 43 testes. |
| `tests/conftest.py` | Ajudantes `criar_personal`, `criar_pacote`, `criar_compra`, `criar_sessao`. |
| `tests/navegador/personal_navegador.py` | **Novo.** Teste no navegador, celular e computador. |

## Cada mudança: antes, depois e por quê

### 1. Banco

| Onde | Coluna | Para quê |
|---|---|---|
| `planos` | `quantidade_sessoes` | Na conta de personal o plano é um pacote: quantas sessões ele dá. `duracao_dias` continua e vira a validade (90 dias ao criar). Na academia fica vazio. |
| `cobrancas` | `quantidade_sessoes` | Quantas sessões **aquela compra** deu, congelado na venda, como o valor. Mudar o pacote depois não mexe em quem já comprou. |
| `contas` | `cpf`, `cref` | O personal é pessoa física. |
| `contas` | `locais_ativos` | Locais de atendimento ligados ("estudio,casa"). Vazio = todos. |
| `sessoes` (nova) | `conta_id`, `aluno_id`, `instrutor_id`, `data`, `hora`, `duracao`, `local`, `repete`, `status`, `abateu`, `concluida_em`, `criado_em` | A agenda. |

**Diferença do documento "Esquema-Backend":** ele propunha uma tabela `pacotes_sessoes` com um contador de sessões usadas. Não criei: o saldo é **calculado** (seção 2), e um contador gravado é mais um número para ficar errado. Se a decisão D12 mudar para "o que sobra não soma", aí a tabela passa a ser necessária.

### 2. O saldo (leia isto primeiro)

Não existe coluna "saldo". Ele é calculado toda vez:

```
saldo = sessões COMPRADAS − sessões que ABATERAM
```

- **Compradas:** a soma de `cobrancas.quantidade_sessoes` do aluno, de toda cobrança não cancelada, **paga ou em aberto**. A sessão é creditada na venda; o que falta receber aparece como "pendente".
- **Abateram:** as sessões **concluídas** com `abateu = verdadeiro`.

Regras que saem daí:

- **Só sessão concluída consome.** Cancelada não consome; agendada ainda não consumiu.
- **Sessão fechada sem saldo fica fora do pacote** (`abateu = falso`): não vira "dívida de sessão" que o próximo pacote pagaria.
- **O "pacote atual"** mostrado nas telas é o da última compra: `total` é o que o aluno tinha ao comprar (sobra + sessões novas) e `usadas` é o que abateu desde então.

### 3. Renovar: o que sobrou SOMA (decisão D12, ainda em aberto)

Renovar é comprar outro pacote. Como o saldo é a soma das compras menos o que abateu, **as sessões que sobraram somam nas novas**. É a regra que o front de exemplo adotou e a tela diz isso ao aluno ("O que sobrou não se perde").

**D12 continua para o Adauto e o Diogo confirmarem com o cliente.** Se a resposta for "não soma", muda o `pacote_service` e a frase do template.

Outro detalhe: enquanto a cobrança de uma renovação está **em aberto**, renovar de novo **troca** essa compra (não cria duas pendentes), que é como a cobrança já funcionava na academia.

### 4. Quem é "pendente" na conta de personal

Na academia, pendente é quem passou do vencimento. No personal não há vencimento: **pendente é quem tem cobrança em aberto**. O pacote passar da validade (90 dias) **não** é dívida.

Nas listas, o texto "vence em…" vira o saldo: "sobram 5 sessões", "sobra 1 sessão", "sem saldo", "sessão avulsa" ou "pacote encerrado" (inativo).

### 5. Pacotes

- Mesmas rotas de planos (`planos.lista`, `novo`, `editar`, `alternar`), templates `personal/pacotes.html` e `personal/pacote_form.html`.
- O formulário manda `quantidade_sessoes` (1 a 100) e não manda `duracao_dias`.
- "Sessão avulsa" é o pacote de 1 sessão: não entra em "pacotes acabando".
- Se uma conta de **academia** mandar `quantidade_sessoes` no formulário, é ignorado.

### 6. Agenda

| Endereço | Endpoint | Antes |
|---|---|---|
| `GET /agenda` | `agenda.index` | "em construção" |
| `GET /agenda/<id>` | `agenda.detalhe` | não existia |
| `GET, POST /agenda/nova` | `agenda.nova` | não existia |
| `POST /agenda/<id>/concluir` | `agenda.concluir` | não existia |
| `POST /agenda/<id>/cancelar` | `agenda.cancelar` | não existia |
| `POST /configuracoes/locais` | `config.locais` | não existia |

- **Marcar:** aluno ativo da conta; de hoje a um ano; horários de 06:00 a 21:30, de meia em meia hora; duração de 30, 45, 60 ou 90 minutos; local entre os ligados em Configurações (local desligado cai no primeiro ligado). **O mesmo profissional não fica com duas sessões no mesmo dia e horário.**
- **Remarcar:** muda a mesma sessão (não cria outra). Só vale para sessão agendada do mesmo aluno.
- **Concluir ("marcar presença"):** no dia da sessão ou depois (sessão que ficou sem fechar). Abate 1 do saldo se havia saldo. Tocar duas vezes não abate duas.
- **Cancelar:** só por POST, com confirmação num popup. Não abate. Sessão já fechada não se cancela.
- **"Toda semana":** ao **concluir** uma sessão semanal, o sistema marca a da semana seguinte (mesmo horário e local), se o horário estiver livre. Cancelar interrompe a repetição. Assim a agenda não é inundada com meses de sessões.
- **Conta de academia** que abrir a agenda recebe um aviso e volta ao painel; POST responde 404.

**O sistema não avisa o aluno.** Por isso a sessão nasce `agendada` e a tela não mostra "já confirmou" nem "ainda não confirmou" (esses estados, no desenho, dependem de um lembrete automático). O lembrete da véspera está na fila de Mensagens.

### 7. Painel, configurações, cobrança e mensagens

- **Painel:** os mesmos números da academia (`montar_painel`) mais: **pacotes acabando** (saldo de até 2, sem avulso), **sessões hoje**, **ticket por pacote**, e "em risco" começa por quem está na última sessão.
- **Configurações:** abas Perfil, Locais, Mensagens, Cobrança e Metas. `config.salvar` grava nome, CPF (conferido pelos dígitos), CREF, telefone, e-mail e cidade. `config.locais` exige pelo menos um local ligado.
- **Cobrança:** mesma tela. Para compra de pacote, `c.termo = 'pacote'`: o template (que já previa isso) troca "mensalidade" por "pacote" e somem "dias" e "vencimento".
- **Mensagens:** filtros Aniversários, **Sessões de amanhã** e Cobranças. Dois textos padrão mudam (cobrança fala em pacote; aniversário fala na primeira pessoa). O texto que a conta gravou continua valendo.

### 8. Templates

Os 10 templates vieram do Drive na `front-13-personal`. Só `personal/painel.html` mudou, com 5 ajustes marcados `{# [back-17-personal] ... #}`, os mesmos que o painel da academia já tinha. **Adauto: leve para o front.**

1. Botão de WhatsApp da tabela era demonstração: virou link.
2. Variação do faturamento negativa não leva "+", e sem mês anterior não aparece.
3. Variação de matrículas negativa não leva "+".
4. Sem meta cadastrada, some a frase "meta de … em amarelo".
5. Sem base de comparação, some o selo "% no ano".

## A migration

`b17f3a4b5c60_personal_pacotes_e_sessoes.py`, depois da `b16e2f3a4b50`. Acrescenta as cinco colunas (com `batch_alter_table`) e cria `sessoes`. **Não toca em nenhum dado:** planos, cobranças e contas que já existem ficam com as colunas novas vazias. O downgrade remove as colunas e a tabela (agenda e saldos deixam de existir).

## Como foi testado

- **`pytest`: 465 de 465** (43 novos em `tests/test_personal.py`): painel do personal e da academia; pacotes (lista, formulário, criar, editar, 7 inválidos, academia não ganha sessões); saldo (compra, abate, cancelada, fora do pacote, quem nunca comprou); lista e perfil com o saldo; pendente é quem deve; tela de renovar; renovar soma e troca a compra pendente; cobrança de pacote até "quitado"; pacote de outra conta ou inativo; agenda vazia e só para personal; marcar; 5 sessões inválidas; mesmo horário, inativo, outra conta, local desligado; remarcar; concluir uma vez só; sessão futura e atrasada; sem saldo; cancelar; semanal; agrupamento por dia e aviso de última sessão; detalhe; marcar e renovar; configurações, CPF inválido, locais; textos padrão; fila de mensagens; isolamento; sem login; GET não grava; exclusão.
- **Migration num Postgres temporário** (criado e apagado pelo teste): **17 checagens**, incluindo que planos, cobranças e contas existentes não mudam.
- **Navegador (Playwright):** personal **55 de 55**, celular (390 px, toque, claro) e computador (1440 px, escuro): painel e menu próprios, criar pacote, marcar sessão, marcar presença, lembrete na fila, cancelar, renovar com o novo saldo recalculado na tela, cobrança de pacote, perfil e locais. As telas da academia foram rodadas de novo, sem mudança: login 60 de 60, painel 78 de 78, alunos 32 de 32, planos 31 de 31, cobrança 33 de 33, frequência 31 de 31, relatórios 28 de 28, configurações 29 de 29, equipe 34 de 34, treinos 79 de 79, avaliações 68 de 68, mensagens 34 de 34.
- **Varredura de rotas por papel** com conta de **academia**, comparada com a `front-13-personal`: só mudou a agenda (de "em construção" para "volta ao painel").

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Como está | Evidência |
|---|---|---|
| Isolamento entre contas | Sessão por `da_conta(Sessao)`; aluno por `da_conta(Aluno)`; pacote por `da_conta(Plano)`. Outra conta: 404 | `test_sessao_de_outra_conta_da_404`, `test_renovar_com_pacote_de_outra_conta_ou_inativo` |
| Id enviado na mão | Pacote de outra conta ou inativo não renova; `remarcar` de outro aluno não mexe; aluno de outra conta dá 404 | `test_remarcar_muda_a_mesma_sessao`, `test_sessao_no_mesmo_horario_inativo_outra_conta_e_local_desligado` |
| Variante errada | Academia não entra na agenda nem grava locais; não ganha `quantidade_sessoes` | `test_agenda_vazia_e_so_para_personal`, `test_locais_de_atendimento`, `test_plano_de_academia_nao_ganha_sessoes` |
| Saldo não vem do cliente | Nenhum formulário manda saldo: ele é calculado das compras e das sessões | `test_saldo_e_o_que_comprou_menos_o_que_abateu` |
| Ação repetida | Concluir duas vezes abate uma; renovar com cobrança em aberto troca a compra | `test_concluir_abate_uma_do_saldo_uma_vez_so`, `test_renovar_soma_o_que_sobrou` |
| CSRF e método | Todo formulário manda `csrf_token`; concluir e cancelar só por POST | `test_cancelar_nao_abate` (GET dá 405) |
| GET não grava | 12 telas abertas, nada muda | `test_sem_login_e_get_nao_grava` |
| Validação | CPF pelos dígitos; data, horário, duração e local conferidos no servidor | `test_configuracoes_do_personal`, `test_sessao_invalida_avisa_e_nao_grava` |
| Papéis | Planos, renovação e locais seguem as travas que já existiam (dono e recepção; locais só o dono) | rotas |

## Como revisar

```bash
git fetch origin
git diff origin/front-13-personal..origin/back-17-personal --stat
git diff origin/front-13-personal..origin/back-17-personal -- app/ migrations/
```

Ordem sugerida: `pacote_service.py` (o texto do começo explica o saldo); `models.py` e a migration; `situacao_service.py` (`_com_pacote`); `cobranca_service.py` (3 trechos marcados); `agenda_service.py` e `agenda/routes.py`; o resto são os desvios "se for personal".

## Para decidir (Adauto e Diogo)

1. **D12: o que sobra do pacote soma ao renovar?** Implementado que **soma**, como o front diz. Confirmar com o cliente.
2. **Validade do pacote.** Todo pacote nasce com 90 dias e o formulário não pergunta. Hoje a validade **não bloqueia nada** (saldo não expira). Decidir se sessão vence.
3. **Falta sem avisar ("no-show").** O desenho tem o estado "Faltou", mas não tem botão. Hoje o personal marca presença (abate) ou cancela (não abate). Se falta deve abater, precisa de um botão no front.
4. **Confirmação do aluno.** "Confirmada", "A confirmar" e "Remarcada" dependem de resposta a lembrete automático. Sem ele, o card "A confirmar" da agenda fica em 0. Dá para ter um botão manual "aluno confirmou", se o front tiver.
5. **Grade de horários:** fixa, de 06:00 a 21:30, de meia em meia hora (32 botões no celular). Se quiser a grade por profissional, é um campo novo.
6. **"Marcar e avisar o aluno":** o botão do front diz "avisar", e o sistema não avisa. Sugestão: trocar o texto do botão para "Marcar sessão".
7. **Inatividade automática** ("vira inativo depois de X dias sem renovar") usa a data da última compra **mais a validade**. Um aluno com saldo, mas que comprou há muito tempo, pode virar inativo. Na conta de personal talvez a regra deva olhar a última sessão.
8. **Equipe na conta de personal:** as rotas de convite continuam existindo, mas a tela de configurações do personal não tem a aba Equipe. Personal com mais de um profissional fica para depois.
9. **Relatórios administrativos** são a mesma tela da academia e falam em "mensalidade" e "vencimento" em alguns pontos.
10. **O perfil do aluno** mostra o saldo na linha que se chama "Vencimento" (o template é o mesmo da academia).

## Riscos

- **É a maior branch do projeto** (três serviços novos e desvios em nove arquivos). O risco para a academia foi contido pelo desenho (tudo atrás de `e_personal()`) e conferido pela suíte inteira e pela varredura de rotas.
- **O saldo é recalculado a cada tela** (três consultas por requisição, guardadas durante a requisição). Para um personal, com dezenas de alunos, é irrelevante; não foi pensado para milhares de alunos.
- **Trocar o tipo da conta** (academia ↔ personal) depois de ter dados não tem tela e não é suportado: planos sem `quantidade_sessoes` não dariam saldo.
- **Sessão semanal** só anda quando a anterior é concluída: se o personal esquecer de marcar presença, a semana seguinte não aparece sozinha.
