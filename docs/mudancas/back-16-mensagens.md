# back-16-mensagens — a fila de mensagens do dia pelo WhatsApp (custo zero)

| | |
|---|---|
| **Branch** | `back-16-mensagens` |
| **Sai de** | `front-12-mensagens` (que só traz o template, copiado do Drive) |
| **Data** | 12/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefa** | 5.7 da lista "Tarefas do backend — Diogo": mensagens do dia |
| **Decisões usadas** | **D14** (mensagem gratuita e fácil para o dono); A1 (migration na branch, só rodada em banco de teste) |
| **Tem migration** | **Sim:** `migrations/versions/b16e2f3a4b50_mensagens_enviadas.py`. Cria `mensagens_enviadas`. Não altera tabela existente. |
| **Dependência nova** | **Nenhuma.** |

## Resumo: como ficou o envio de mensagem, de graça

A pergunta do Adauto era: *como mandar mensagem para os alunos sem custo e de um jeito fácil para o dono?*

A resposta desta branch: **o sistema prepara, a pessoa só toca.**

1. Todo dia, a tela **Mensagens** mostra a **fila do dia**: quem faz aniversário hoje, quem tem avaliação física amanhã e quem está com a mensalidade vencida.
2. Cada linha já vem com o **texto escrito**, com o nome do aluno, a data, a hora e o valor no lugar.
3. O botão **"Enviar no WhatsApp"** abre o WhatsApp de quem está usando (no celular ou no WhatsApp Web), já na conversa do aluno, com a mensagem pronta. A pessoa toca em enviar.
4. A linha vira **"Enviada hoje"** para toda a equipe.

**Custo: zero.** Não usa a API do WhatsApp, não precisa de conta na Meta nem de número novo: sai do WhatsApp que a academia já usa. **O limite** é que alguém precisa tocar em cada mensagem; o WhatsApp não deixa um site enviar sozinho nem em lote sem a API paga. Envio automático fica para depois do lançamento (seção "Para decidir").

Os textos são os **modelos de Configurações > Mensagens** (da `back-12`): se a academia mudou o texto lá, é o texto dela que aparece aqui.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/models.py` | Modelo novo `MensagemEnviada`, no fim do arquivo. |
| `migrations/versions/b16e2f3a4b50_mensagens_enviadas.py` | **Novo.** A migration. |
| `app/services/mensagem_service.py` | **Novo.** Monta a fila e grava o envio. |
| `app/blueprints/mensagens/` | **Novo.** As 2 rotas. |
| `app/blueprints/pendentes.py` | Saiu a linha de `mensagens` ("em construção"). |
| `app/__init__.py` | Registra o blueprint `mensagens`. |
| `app/blueprints/cobrancas/routes.py` | `cobrancas.lembrete_lote` deixa de responder "ainda não disponível": leva à fila. |
| `app/services/painel_service.py` | Os avisos do painel passam a levar o telefone do aluno. |
| `app/templates/_notificacao.html`, `alunos/detalhe.html`, `alunos/lista.html`, `painel/index.html` | **Ajustes marcados:** botões de WhatsApp que eram demonstração viraram links (seção 5). |
| `tests/test_mensagens.py` | **Novo.** 25 testes. |
| `tests/navegador/mensagens_navegador.py` | **Novo.** Teste no navegador, celular e computador. |
| `tests/navegador/painel_navegador.py` | 1 checagem trocada: "Mensagens" era o exemplo de tela "em construção"; agora o exemplo é a central de notificações. |

## Cada mudança: antes, depois e por quê

### 1. Rotas

| Endereço | Endpoint | Quem | Antes |
|---|---|---|---|
| `GET /mensagens` | `mensagens.index` | todos | "em construção" |
| `POST /mensagens/enviada` | `mensagens.enviada` | todos | não existia |
| `POST /cobrancas/lembrete` | `cobrancas.lembrete_lote` | dono e recepção | avisava "ainda não disponível" |

`/mensagens/enviada` é chamada pelo JavaScript do front em segundo plano, com um JSON `{"id": "cobranca-12"}` e o código CSRF no cabeçalho `X-CSRFToken`. Sem o código, o servidor recusa (tem teste).

### 2. Quem entra na fila

| Motivo | Regra | Texto usado |
|---|---|---|
| **Aniversário** | Aluno **ativo** que faz aniversário hoje. Quem nasceu em 29/02 entra em 28/02 nos anos sem 29. | modelo `aniversario` |
| **Avaliação** | Aluno **ativo** com avaliação física **marcada para amanhã** e ainda em aberto (da `back-15`). | modelo `avaliacao` |
| **Cobrança** | Aluno **ativo** com a mensalidade vencida (a mesma regra de "pendente" do painel), do mais atrasado para o menos. | modelo `cobranca` |

Variáveis trocadas: `[nome]` (primeiro nome), `[academia]`, `[data]`, `[hora]`, `[valor]`, `[plano]` e `[dias]`.

**Cobrança não vira perseguição:** quem recebeu a cobrança ontem ou anteontem **sai da fila de hoje** e volta no terceiro dia (no máximo uma a cada 3 dias, como pede o documento "Acesso e Mensagens").

Os modelos `sumido` e `boasvindas` existem nas Configurações, mas ainda não têm fila (ver "Para decidir"). `sessao` é do Personal (`back-17`).

### 3. Quem vê o quê

- **Dono e recepção:** a fila inteira.
- **Instrutor:** aniversários e avaliações. **Não vê cobrança** (nem a linha, nem o filtro, nem o valor), e não consegue marcar uma cobrança como enviada mesmo chamando o endereço na mão. É a mesma regra do resto do sistema: dinheiro é do dono e da recepção.

### 4. O registro do envio (`mensagens_enviadas`)

Colunas: `conta_id`, `aluno_id`, `tipo`, `referencia` (o id do aluno ou do horário da avaliação), `data`, `enviada_em`, `enviada_por_id`.

- **Não guarda o texto nem o telefone.** Só quem tocou, para quem, de que tipo e quando.
- A combinação (conta, tipo, referência, dia) é única no banco: tocar duas vezes, ou duas pessoas tocarem ao mesmo tempo, grava uma linha só.
- O servidor **só aceita marcar o que está na fila de hoje de quem está logado**. É isso que impede marcar aluno de outra academia, aluno inativo ou um id inventado.
- O sistema **não sabe se a pessoa de fato enviou** no WhatsApp: ele registra o toque no botão. A tela diz "Enviada hoje"; quem quiser, toca em "Enviar de novo".
- Se o aluno for excluído (cadastro feito por engano), os registros dele vão junto. É só um histórico de toques, não impede a exclusão.

### 5. Botões de WhatsApp que eram demonstração

O front tinha vários botões que só mostravam um aviso ("WhatsApp aberto para Ana") sem abrir nada. Viraram links de verdade, com ajustes marcados `{# [back-16-mensagens] ... #}`. **Adauto: leve para o front.**

| Onde | Antes | Agora |
|---|---|---|
| `alunos/detalhe.html` (2 botões "WhatsApp", desktop e celular) | aviso | abre a conversa do aluno |
| `alunos/lista.html` (ícone na tabela) | aviso | abre a conversa do aluno |
| `painel/index.html` (ícone na tabela de alunos) | aviso | abre a conversa do aluno |
| `_notificacao.html` (cada linha do aviso do painel: em risco, aniversário, renovação) | aviso | abre a conversa do aluno |
| `_notificacao.html` ("Enviar mensagem para todos", "Enviar lembrete de renovação") | aviso "enviadas" | leva à fila de mensagens |

Aluno sem telefone: o botão continua sendo botão e avisa "não tem telefone cadastrado".

**"Cobrança WhatsApp" do painel** (o popup de cobrança em lote): o botão de enviar leva à fila, onde a cobrança de cada atrasado já está escrita. A seleção de alunos e o texto digitado no popup **não são usados** (ver "Para decidir").

### 6. O aviso do topo da tela

O template tem dois textos: "Você toca, o WhatsApp abre pronto" e "Lembretes automáticos ligados: … esta fila sai sozinha às 9h". O segundo descreve o envio automático, que **não existe**. Por isso o servidor manda sempre `lembretes_auto = False`, mesmo com a chave "Lembretes" de Configurações ligada (ela nasce ligada). A tela diz o que o sistema faz hoje.

## A migration

`b16e2f3a4b50_mensagens_enviadas.py`, depois da `b15d1e2f3a40`. Cria a tabela, as chaves estrangeiras, a regra de unicidade e dois índices. O downgrade apaga a tabela (some o histórico de "enviada"; nada mais muda).

## Como foi testado

- **`pytest`: 422 de 422** (25 novos em `tests/test_mensagens.py`): os três motivos com o texto certo; link do WhatsApp com o texto; texto personalizado (e HTML digitado não vira HTML); fila vazia; o aviso do topo não promete envio automático; avaliação que não é amanhã ou não está em aberto; gravar o envio e ver como enviada em outro usuário; 8 ids que não estão na fila; cobrança que não volta no dia seguinte; envio sem CSRF recusado; instrutor sem cobrança; outra academia; sem login; GET não grava; cobrança em lote; botões que viraram links; aluno sem telefone; excluir aluno leva o registro.
- **Migration num Postgres temporário** (criado e apagado pelo teste): **18 checagens**, incluindo a regra de "uma por dia" no banco.
- **Navegador (Playwright):** mensagens **34 de 34**, celular (390 px, toque, claro) e computador (1440 px, escuro): chegar pelo menu, filtros, tocar em enviar (abre o `wa.me` com o texto, a linha vira "Enviada hoje" e continua assim depois de recarregar), "Editar textos", links do perfil e do aviso do painel, cobrança em lote. **O teste não sai para a internet:** o endereço `wa.me` é respondido pelo próprio teste. As outras telas foram rodadas de novo: login 60 de 60, painel 78 de 78, alunos 32 de 32, planos 31 de 31, cobrança 33 de 33, frequência 31 de 31, relatórios 28 de 28, configurações 29 de 29, equipe 34 de 34, treinos 79 de 79, avaliações 68 de 68.
- **Varredura de rotas por papel**, comparada com a `front-12-mensagens`: nenhuma rota mudou de resposta (a de mensagens já respondia 200, como "em construção").

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Como está | Evidência |
|---|---|---|
| Isolamento entre academias | A fila é montada com `da_conta(...)`; marcar só aceita linha da fila de quem está logado | `test_outra_academia_nao_ve_nem_marca` |
| Papéis | Instrutor não vê nem marca cobrança; `cobrancas.lembrete_lote` segue 403 para ele | `test_instrutor_nao_ve_nem_marca_cobranca`, `test_cobranca_em_lote_do_painel_leva_a_fila` |
| CSRF em chamada JSON | `X-CSRFToken` obrigatório | `test_envio_sem_csrf_e_recusado` |
| Id enviado na mão | Id fora da fila, de aluno inativo, de tipo que não existe ou gigante: 404, nada gravado | `test_so_marca_o_que_esta_na_fila_de_hoje` (8 casos) |
| Texto do usuário na tela | O modelo de mensagem é digitado pela academia: sai com o escape do Jinja na tela e codificado no endereço do WhatsApp | `test_texto_personalizado_nas_configuracoes_vale_na_fila` |
| Link que abre outra aba | `target="_blank"` sempre com `rel="noopener"` | os 5 templates |
| Dados pessoais | O registro não guarda texto nem telefone. O telefone só aparece no endereço `wa.me`, que abre no aparelho de quem usa; o servidor não envia nada a terceiros | `MensagemEnviada` |
| GET não grava | Abrir a fila não grava nada | `test_abrir_a_tela_nao_grava_nada` |

**Para a `back-19-lgpd`:** o documento de mensagens pede uma caixa "aceita receber avisos pelo WhatsApp" no cadastro do aluno. Na fila manual o aluno entra de qualquer forma (quem envia é uma pessoa, pelo WhatsApp dela); o aceite passa a ser obrigatório quando houver envio automático. A caixa entra na `back-19`.

## Como revisar

```bash
git fetch origin
git diff origin/front-12-mensagens..origin/back-16-mensagens --stat
git diff origin/front-12-mensagens..origin/back-16-mensagens -- app/ migrations/
```

Ordem sugerida: `models.py` (fim do arquivo) e a migration; `mensagem_service.py` (o texto do começo explica a fila); `mensagens/routes.py`; os 4 templates.

## Para decidir (Adauto e Diogo)

1. **Envio automático (fase 2).** Pede a API oficial do WhatsApp (Cloud API da Meta): número exclusivo, textos aprovados pela Meta e custo por mensagem (cerca de R$ 10 por mês para uma academia de 250 alunos, pela conta do documento "Acesso e Mensagens"). É decisão de produto e de preço; o que foi feito aqui continua valendo como base (mesma fila, mesmos textos).
2. **A chave "Lembretes automáticos" de Configurações** hoje não muda nada. Sugestão: esconder no front até a fase 2, ou trocar o nome.
3. **Aluno sumido e boas-vindas.** Os dois modelos de texto existem, mas o front da fila só tem três filtros. Incluir "sumido" (quem não vem há 15 dias, com o check-in ligado) e "boas-vindas" (matrícula de hoje) é pequeno no backend; precisa de dois filtros a mais no front.
4. **O popup "Cobrança WhatsApp" do painel** deixa selecionar alunos e digitar um texto, e nada disso é usado: o botão leva à fila, com o texto dos modelos. O texto de exemplo do popup ainda diz "da Vale Tec". Sugestão: o front trocar o popup por um link direto para a fila.
5. **"Comprovante" na tela de pagamento recebido** (`cobranca/receber.html`) continua como botão de demonstração. Dá para virar link do WhatsApp com um texto de recibo; não entrou porque mexe na tela de cobrança.
6. **Texto padrão do aniversário:** o documento de mensagens tinha "Aproveite 10% na próxima renovação"; o padrão do sistema (da `back-12`) não promete desconto. Cada academia pode pôr o que quiser no texto dela.

## Riscos

- **"Enviada" é o toque, não a entrega.** Se a pessoa abrir o WhatsApp e desistir, a linha fica como enviada. "Enviar de novo" resolve.
- **Fila grande:** numa academia com muita inadimplência, a fila de cobrança pode ter dezenas de linhas, uma por toque. É o preço do custo zero.
- **Sem horário:** a fila não some fora do horário comercial; quem decide a hora de mandar é a pessoa.
- **Telefone errado no cadastro** abre a conversa errada (ou nenhuma). O sistema não confere se o número tem WhatsApp.
