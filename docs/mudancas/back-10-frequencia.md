# back-10-frequencia — check-in, quem sumiu e bloqueio de acesso

| | |
|---|---|
| **Branch** | `back-10-frequencia` |
| **Sai de** | `front-06-frequencia` (que só traz os 3 templates, copiados do Drive) |
| **Data** | 12/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefa** | 5.3 da lista "Tarefas do backend — Diogo": frequência e check-in |
| **Tem migration** | **Sim:** `migrations/versions/b10e6f7a8b90_frequencias_e_acesso.py`. Cria `frequencias`, acrescenta `alunos.acesso_liberado` e liga o check-in nas contas do modelo "academia". Não apaga nem converte dado. |

## Resumo

A recepção passa a **registrar a entrada do aluno em um toque** (busca pelo nome ou CPF, sem catraca). Com as entradas guardadas, o sistema mostra:

- quem está **na academia agora** e as entradas por hora do dia;
- quem **sumiu há mais de 15 dias** (card "Ausentes" do painel e alerta de aluno em risco);
- a **assiduidade** de cada aluno, no perfil;
- a planilha dos check-ins do dia.

O botão **Bloquear** do perfil, que só mostrava um aviso, passou a funcionar: aluno bloqueado não entra.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/models.py` | Modelo novo `Frequencia`; coluna nova `Aluno.acesso_liberado`. |
| `migrations/versions/b10e6f7a8b90_frequencias_e_acesso.py` | **Novo.** A migration. |
| `app/services/frequencia_service.py` | **Novo.** Registrar entrada, números da tela, sugestões, ausentes, assiduidade e CSV. |
| `app/blueprints/frequencia/routes.py` | **Novo.** As rotas `frequencia.*`. |
| `app/blueprints/alunos/routes.py` | `acesso` (bloquear/liberar) e `acesso_busca` (popup do painel) deixaram de ser avisos de "ainda não disponível". |
| `app/services/aluno_tela_service.py` | O perfil passa a trazer `acesso_liberado` e `freq` de verdade. |
| `app/services/painel_service.py` | Card "Ausentes", lista de ausentes e alunos em risco por frequência. |
| `app/services/aluno_service.py` | `excluir_aluno` também recusa aluno com entradas registradas. |
| `app/cli.py` | Conta nova do modelo "academia" nasce com o check-in ligado. |
| `app/blueprints/pendentes.py`, `app/__init__.py` | `frequencia.index` saiu das telas "em construção"; o blueprint novo é registrado. |
| `app/templates/alunos/detalhe.html` | **1 ajuste marcado** (ver "Sem dado", abaixo). É o único template alterado. |
| `tests/test_frequencia.py` | **Novo.** 24 testes. |
| `tests/conftest.py` | Ajudantes `criar_entrada` e `ligar_checkin`. |
| `tests/navegador/frequencia_navegador.py` | **Novo.** Teste no navegador. |
| `tests/navegador/_base.py` | Ajudantes comuns dos testes de navegador (cenários, login, checagens finais). |

## Cada mudança: antes, depois e por quê

### 1. Tabela `frequencias`

Uma linha para cada **entrada**: `conta_id`, `aluno_id`, `data_hora_entrada`, `origem` (`recepcao` ou `app`) e `instrutor_id` (quem registrou). É a tabela do `Esquema-Backend.md` (seção 4.1), com duas colunas a mais: `conta_id` (toda tabela de negócio tem, desde a `back-06`) e `origem` (o front mostra "Recepção" ou "App").

**Não existe coluna "presente sim/não".** Faltar é não ter linha. Daí a regra que vale para a branch inteira, e que é a do `Esquema-Backend.md`:

> Quem não tem nenhuma entrada registrada é **"sem dado"**, nunca "0 acessos".

Na prática: aluno que nunca teve entrada não aparece como ausente; no perfil dele o cartão diz "Sem dado"; e uma academia que acabou de ligar o check-in vê "—" no card de ausentes, não "0".

### 2. Rotas

| Endereço | Endpoint | Quem pode | Antes |
|---|---|---|---|
| `GET /frequencia` | `frequencia.index` | todos | tela "em construção" |
| `GET /frequencia?q=...&partial=1` | (o mesmo) | todos | não existia. Busca ao vivo: devolve só o pedaço com as sugestões |
| `POST /frequencia/checkin` | `frequencia.checkin` | todos | não existia |
| `GET /frequencia/exportar` | `frequencia.exportar` | dono e recepção | não existia |
| `POST /alunos/<id>/acesso` | `alunos.acesso` | dono e recepção | só avisava "ainda não disponível" |
| `GET /alunos/acesso/busca?q=` | `alunos.acesso_busca` | dono e recepção | devolvia um aviso fixo |

O instrutor **registra entrada** (é trabalho do dia a dia), mas não exporta a planilha nem bloqueia acesso.

Com o check-in **desligado** na conta, as três rotas de `/frequencia` avisam e voltam ao painel, e o menu nem mostra o item (isso já era do front).

### 3. Regras (estão no começo de `frequencia_service.py`)

| Regra | Valor | Por quê |
|---|---|---|
| "Na academia agora" | quem entrou há menos de **90 minutos** | O sistema não registra saída. 90 minutos é uma duração comum de treino. |
| Toque repetido | menos de **60 minutos** desde a última entrada do mesmo aluno não cria outra | Dois toques no botão, ou a recepção registrando quem já tinha entrado, inflariam os números. |
| Ausente | aluno **ativo** cuja última entrada foi há **mais de 15 dias** | É o texto do card do front. |
| Assiduidade | em quantos dos últimos 30 dias o aluno veio, **sobre 30** | Simples de explicar. Ver "Para decidir", abaixo. |
| Sugestões sem busca | alunos ativos que costumam chegar perto desta hora e ainda não entraram hoje; sem histórico, os últimos cadastrados | O front de exemplo mostrava três alunos fixos. |

**Mensalidade atrasada não barra a entrada.** O aluno entra e a recepção recebe o aviso "mensalidade pendente: vale avisar na saída", como no front de exemplo. Quem barra é o botão Bloquear, que é uma decisão da recepção.

Entrada recusada (e nada é gravado): aluno inativo, aluno bloqueado, aluno que não existe ou que é de outra academia.

### 4. Bloquear e liberar acesso

Coluna nova `alunos.acesso_liberado` (sim/não, padrão sim). O nome é o que o front usa. Bloquear **não** mexe em matrícula nem em cobrança: só faz o check-in recusar a entrada.

Depois de bloquear ou liberar, a tela volta **para o perfil do aluno**. O front de exemplo voltava "para onde o navegador veio"; não fiz assim porque aceitar um endereço informado pelo navegador é uma brecha para levar o usuário a outro site.

### 5. Check-in ligado por padrão nas academias

A coluna `contas.checkin_ativo` existe desde a `back-06`, sempre desligada, e a tela para ligar só chega com as Configurações (`back-12`). Para a frequência poder ser usada desde já:

- a migration liga o check-in nas contas do modelo **academia** (as do modelo personal continuam desligadas);
- conta nova de academia já nasce com ele ligado (`app/cli.py`).

### 6. Painel

- Card **"Ausentes há mais de 15 dias"**: o número, a lista que ele abre e o "—" quando ainda não há nenhuma entrada.
- **Alunos em risco** passa a somar quem está com pagamento atrasado e quem sumiu (antes, só pagamento).
- Com o check-in desligado, nada muda no painel.

### 7. "Sem dado" no perfil (o ajuste no template)

`alunos/detalhe.html` mostrava o cartão de frequência sempre que o check-in estava ligado, e quebraria para um aluno sem entradas (ele lê `freq.pct`). O ajuste, marcado com `{# [back-10-frequencia] ... #}`: aluno sem nenhuma entrada vê um cartão pequeno "Sem dado: nenhuma entrada registrada ainda"; os demais veem o cartão original, sem mudança.

## A migration

`b10e6f7a8b90_frequencias_e_acesso.py`, depois da `b09d5e6f7a80`.

- **Sobe:** cria `frequencias` (com dois índices: por conta e data, e por aluno e data); acrescenta `alunos.acesso_liberado`, com os alunos existentes liberados; liga `checkin_ativo` nas contas do modelo academia.
- **Desce:** apaga `frequencias` (as entradas registradas se perdem) e a coluna. O check-in das contas **não** é desligado de volta: não há como saber quais já estavam ligadas.
- **Depois do pull, rodar `flask db upgrade`.**

## Como foi testado

- **`pytest`: 236 de 236** (24 novos em `tests/test_frequencia.py`, contando os casos de cada teste): entrada em um toque; toque repetido; 5 entradas recusadas; pendência não barra; instrutor registra e não exporta; números da tela (entradas, na academia, pico, barras por hora); dia sem entrada não inventa pico; busca ao vivo só da própria academia; sugestões pelo horário; CSV só do dia e só da academia; check-in desligado; "sem dado" no painel e no perfil; ausente só quem tem entrada e sumiu (15 dias exatos ainda não conta; inativo não conta); assiduidade; bloquear e liberar; busca do popup; aluno de outra academia (404); não excluir aluno com entrada.
- **Migration num Postgres temporário:** 14 checagens, com uma conta academia e uma personal. Sobe; o aluno antigo fica liberado; o check-in liga só na academia; `flask db check` sem diferença; desce; o banco volta a bater com o modelo anterior; sobe de novo.
- **Navegador (Playwright):** frequência **31 de 31**; cobrança 33 de 33, alunos 32 de 32, planos 31 de 31, painel 74 de 74, login 60 de 60. Celular de 390 px com toque (claro) e computador de 1440 px (escuro). Fotos abertas e conferidas.
- **Varredura de todas as rotas GET por papel**, comparada com a `front-06-frequencia`: mudaram só as rotas desta branch.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Como está | Evidência |
|---|---|---|
| Isolamento entre academias | `frequencias` tem `conta_id` e toda consulta passa por `da_conta(...)`. Check-in de aluno de outra academia é tratado como "não encontrado"; busca, sugestões, planilha e popup só trazem a própria academia; bloquear aluno de fora dá 404. | casos `de_outra_academia` de `test_entrada_recusada_nao_grava`, `test_busca_ao_vivo_devolve_so_o_pedaco_e_so_da_propria_academia`, `test_exportar_csv_dos_checkins_de_hoje`, `test_acesso_de_aluno_de_outra_academia_da_404` |
| Papéis no servidor | `papel_requerido` em exportar, bloquear e na busca do popup | `test_instrutor_tambem_registra_entrada_mas_nao_exporta`, `test_busca_do_popup_de_acesso` |
| CSRF e métodos | Check-in e bloquear são POST, com `csrf_token` nos formulários | `test_bloquear_e_liberar_acesso` (GET responde 405) |
| Redirecionamento | Nenhuma rota redireciona para endereço vindo do navegador (seção 4) | — |
| Planilha | Células protegidas contra fórmula | `exportar_csv` |
| LGPD | Hora de entrada e saída de uma pessoa é dado pessoal. Fica na conta da academia, só a equipe dela vê, e entra na exportação e na exclusão de dados do aluno (`back-19-lgpd`). | — |

## Como revisar

```bash
git fetch origin
git diff origin/front-06-frequencia..origin/back-10-frequencia --stat
git diff origin/front-06-frequencia..origin/back-10-frequencia -- app/ migrations/
```

Ordem sugerida: `models.py` e a migration, `frequencia_service.py` (o texto do começo traz as regras), `frequencia/routes.py`, e os trechos marcados em `painel_service.py` e `alunos/routes.py`.

## Para decidir (Adauto)

1. **Como medir assiduidade.** Hoje é "dias em que veio, sobre 30". Quem treina 3 vezes por semana aparece com cerca de 43%, o que pode parecer baixo. Alternativa: medir contra uma meta (por exemplo, 3 vezes por semana = 100%). É uma linha de código; depende do que você quer mostrar ao dono.
2. **Tempos:** 90 minutos para "na academia agora" e 60 minutos para ignorar toque repetido. Dá para trocar.

## Riscos

- **Quem der pull sem rodar `flask db upgrade`** vê erro em toda tela que lê alunos (a coluna nova).
- **A migration liga o check-in em toda conta do modelo academia.** O menu passa a mostrar "Frequência" e o painel troca o card "Ticket médio" por "Ausentes". Enquanto não houver tela de Configurações, não há como desligar pela tela.
- **Não há registro de saída:** "na academia agora" é uma estimativa.
- **Aluno com entrada registrada não pode ser excluído** (como já era com quem tem cobrança). A exclusão de verdade dos dados de um aluno é assunto da `back-19-lgpd`.
- **A origem "app"** (check-in feito pelo próprio aluno) é aceita pelo servidor, mas não existe aplicativo do aluno: todas as entradas de hoje vêm da recepção.
- **"Hoje" é o dia do servidor** (mesma observação de fuso da `back-09`).
