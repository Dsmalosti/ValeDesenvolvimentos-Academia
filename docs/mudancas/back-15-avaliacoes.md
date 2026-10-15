# back-15-avaliacoes — avaliação física: agendar, registrar e comparar

| | |
|---|---|
| **Branch** | `back-15-avaliacoes` |
| **Sai de** | `front-11-avaliacoes` (que só traz os 5 templates, copiados do Drive) |
| **Data** | 12/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefa** | 5.6 da lista "Tarefas do backend — Diogo": avaliação física |
| **Decisões usadas** | A1 (migration na branch, só rodada em banco de teste); D14 (mensagem gratuita pelo WhatsApp); D15 (LGPD: dado de saúde com acesso restrito) |
| **Tem migration** | **Sim:** `migrations/versions/b15d1e2f3a40_avaliacoes_fisicas.py`. Cria `avaliacoes_agendadas` e `avaliacoes_fisicas`. Não altera tabela existente. |
| **Dependência nova** | **Nenhuma.** |

## Resumo

O módulo de avaliação física do front novo passa a funcionar:

- **Agenda** (`/avaliacoes`): o que está marcado para hoje, amanhã, o resto da semana e mais adiante; o que passou e não foi feito continua à vista.
- **Agendar** (`/avaliacoes/agendar`): escolhe o aluno, o dia, o horário, o avaliador e se a avaliação é inclusa no plano ou avulsa. Remarcar guarda o horário antigo.
- **Registrar** (`/alunos/<id>/avaliacoes/nova`): o assistente de quatro etapas (anamnese, medidas, dobras, testes). **O IMC e a relação cintura/quadril são calculados pelo servidor**, nunca digitados.
- **Resultado** (`/avaliacoes/<id>`): o que mudou desde a avaliação anterior, e o botão que abre o WhatsApp do aluno com o resultado escrito.
- **Histórico** (`/alunos/<id>/avaliacoes`): todas as avaliações do aluno e o gráfico do peso.
- O **perfil do aluno** mostra a última avaliação; o **painel** avisa das avaliações de hoje.

Três regras do módulo: **é medida, não diagnóstico** (o sistema guarda número, não classifica nem tem campo de laudo); **IMC e RCQ só o servidor calcula**; **medidas são dados de saúde**, e só o dono e os instrutores abrem.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/models.py` | Modelos novos `AvaliacaoAgendada` e `AvaliacaoFisica`, no fim do arquivo. |
| `migrations/versions/b15d1e2f3a40_avaliacoes_fisicas.py` | **Novo.** A migration. |
| `app/services/avaliacao_service.py` | **Novo.** Todas as regras. |
| `app/blueprints/avaliacoes/` | **Novo.** As 5 rotas. |
| `app/helpers/whatsapp.py` | **Novo.** Monta o endereço `wa.me` (número com o código do país e texto). A regra estava dentro do `treino_service` (back-14) e veio para cá, porque a avaliação também usa. |
| `app/services/treino_service.py` | Passa a usar o `helpers/whatsapp.py`. O resultado é o mesmo. |
| `app/blueprints/pendentes.py` | Saíram as 3 linhas de `avaliacoes` ("em construção"). |
| `app/__init__.py` | Registra o blueprint `avaliacoes`. |
| `app/services/aluno_tela_service.py` | O cartão "Avaliação física" do perfil deixa de ser sempre vazio. |
| `app/services/painel_service.py` | `alertas.avaliacao_hoje` deixa de ser sempre vazio; entra `alertas.avaliacoes_hoje` (a lista do dia). |
| `app/services/aluno_service.py` | Aluno com avaliação marcada ou feita não pode ser excluído (só desativado). |
| `app/templates/avaliacoes/*.html`, `_notificacao.html`, `painel/index.html` | **Ajustes marcados** (seção 6). |
| `tests/test_avaliacoes.py` | **Novo.** 45 testes. |
| `tests/conftest.py` | Ajudantes `criar_agendamento` e `criar_avaliacao`. |
| `tests/navegador/avaliacoes_navegador.py` | **Novo.** Teste no navegador, celular e computador. |

## Cada mudança: antes, depois e por quê

### 1. Banco

**`avaliacoes_agendadas`** (a agenda): `conta_id`, `aluno_id`, `data`, `hora` ("09:00"), `tipo` (primeira ou reavaliacao), `status`, `avaliador_id`, `observacao`, `cobranca` (inclusa ou avulsa), `criado_por_id`, `criado_em`.

Status: `confirmada` (nasce assim), `a_confirmar`, `remarcada`, `realizada`, `cancelada`. A agenda mostra só os dois primeiros.

**`avaliacoes_fisicas`** (a avaliação feita): os nomes das colunas são os `name` dos campos do formulário do front (regra 7).

| Grupo | Colunas |
|---|---|
| De quem e quando | `conta_id`, `aluno_id`, `data`, `avaliador_id`, `agendamento_id`, `criado_em` |
| Anamnese | `objetivo`, `restricoes`, `medicamentos`, `liberacao_medica` |
| Medidas | `peso_kg` e `altura_cm` (obrigatórios), `cintura_cm`, `quadril_cm`, `braco_d_cm`, `coxa_d_cm`, `torax_cm`, `panturrilha_cm` |
| **Calculadas** | `imc` (sempre), `rcq` (vazio se faltar cintura ou quadril) |
| Dobras (mm) | `dobra_triceps`, `dobra_subescapular`, `dobra_suprailiaca`, `dobra_abdominal`, `dobra_coxa` |
| Testes | `teste_flexao`, `teste_abdominal`, `teste_flexibilidade` |
| Anotação | `anotacao` |

**Diferença do documento "Esquema-Backend":** lá as dobras ficavam num campo JSON e os nomes eram outros (`data_avaliacao`, `circunferencia_cintura_cm`). Aqui cada dobra é uma coluna e os nomes são os do formulário, porque o front já tem os cinco campos fixos e a regra 7 do projeto manda o `name` ser a coluna. Não há campo de diagnóstico, como o esquema pede.

### 2. Rotas

| Endereço | Endpoint | Quem | Antes |
|---|---|---|---|
| `GET /avaliacoes` | `avaliacoes.agenda` | todos | "em construção" |
| `GET, POST /avaliacoes/agendar` | `avaliacoes.agendar` | todos | "em construção" |
| `GET /alunos/<id>/avaliacoes` | `avaliacoes.aluno` | dono e instrutor | não existia |
| `GET, POST /alunos/<id>/avaliacoes/nova` | `avaliacoes.registrar` | dono e instrutor | "em construção" |
| `GET /avaliacoes/<id>` | `avaliacoes.resultado` | dono e instrutor | não existia |

### 3. Quem vê o quê (dado de saúde)

Peso, medidas, restrições e medicamentos são **dados sensíveis pela LGPD**. Regra adotada, num lugar só (`PAPEIS_QUE_AVALIAM`, no serviço):

- **Recepção:** vê a agenda e agenda. **Não abre** o formulário, o histórico nem o resultado. Se tocar num desses botões, recebe o aviso "as medidas são dados de saúde: só o dono e os instrutores abrem" e vai para a agenda. Se tentar **enviar** uma avaliação, recebe 403. No perfil do aluno ela vê a data da última avaliação, sem peso nem IMC. Na agenda, não vê o botão "Iniciar avaliação".
- **Dono e instrutor:** tudo.

É uma decisão de produto que pode mudar (ver "Para decidir"): trocar é mexer numa linha.

### 4. Agendar

- Só aluno **ativo** da própria conta. Outra academia: 404.
- Data no formato dd/mm/aaaa, de hoje até um ano à frente.
- Horários de 06:00 a 20:00, de hora em hora (lista fixa no serviço).
- Avaliador: dono ou instrutor **ativo da conta**. Id de recepção ou de outra academia é recusado.
- **O mesmo avaliador não fica com dois alunos no mesmo dia e horário.**
- **Remarcar** (`?remarcar=<id>`): o horário antigo vira `remarcada` e nasce outro. Só vale para horário em aberto do **mesmo aluno**.
- **Cobrança:** o plano "inclui avaliação" quando `planos.avaliacoes_incluidas` é maior que zero (coluna da `back-08`). A escolha (inclusa ou avulsa) fica gravada no agendamento. **O sistema ainda não gera a cobrança da avulsa**, porque não existe onde o dono informa o preço (ver "Para decidir"). Ao agendar uma avulsa, a tela lembra de registrar o recebimento pela diária avulsa do painel.

### 5. Registrar e calcular

- Números aceitam vírgula ou ponto ("68,4"). Cada medida tem uma faixa plausível (peso de 20 a 400 kg, altura de 80 a 250 cm, perímetros de 10 a 300 cm, dobras de 1 a 99 mm). Fora da faixa é erro de digitação: a tela avisa qual campo e não grava nada. Exemplo real: digitar a altura em metros ("1,67") é recusado.
- `imc = peso / altura²` (1 casa) e `rcq = cintura / quadril` (2 casas), **sempre no servidor**. Se o navegador mandar `imc` ou `rcq`, são ignorados.
- O avaliador é quem está logado; a data é hoje.
- Se a avaliação veio de um horário da agenda (`ag`), ele passa a `realizada`. Horário de outro aluno ou de outra academia é ignorado.
- **Enviar o mesmo formulário duas vezes** (toque duplo, voltar e reenviar) em até 2 minutos não cria duas avaliações.
- Do formulário anterior só vem a **altura**; peso e medidas são medidos de novo.

### 6. Templates

Os 5 templates vieram do Drive na `front-11-avaliacoes`. Ajustes desta branch, todos marcados com `{# [back-15-avaliacoes] ... #}`. **Adauto: leve para o front.**

| Arquivo | Ajuste |
|---|---|
| `avaliacoes/agenda.html` | O mês do subtítulo era fixo ("Setembro"); agora vem do servidor. |
| `avaliacoes/agenda.html` | "Iniciar avaliação" só aparece para quem pode avaliar (`pode_avaliar`). |
| `avaliacoes/agendar.html` | O aviso "Lembretes automáticos" só aparece se o sistema enviar lembrete (hoje não envia). |
| `avaliacoes/agendar.html` | Sem preço cadastrado, a opção avulsa diz "cobrada à parte" e o botão só diz "Agendar avaliação" (2 pontos). |
| `avaliacoes/aluno.html` | O ano do título era fixo ("Peso em 2026"); agora vem do servidor. |
| `avaliacoes/registrar.html` | O bloco de fotos fica escondido enquanto o servidor não guarda fotos (`fotos_ligadas`). |
| `avaliacoes/resultado.html` | "Ajustar a ficha de treino" levava à ficha só os alunos de id 1, 2 e 3 (os do exemplo); agora leva qualquer um. |
| `_notificacao.html` | "Aviso já enviado" aparecia sempre no aviso do painel; agora só quando houver aviso de verdade. |
| `painel/index.html` | O card e o popup "Avaliações de hoje" tinham número e nomes fixos e estavam escondidos desde a `back-04`. Agora mostram as avaliações do dia, e o botão do WhatsApp é um link de verdade. Sem avaliação no dia, o card não aparece. |

Quando a variável não é passada, cada ajuste se comporta como no Drive.

### 7. Perfil do aluno e painel

- **Perfil:** cartão "Avaliação física" com a data da última, peso, IMC e a diferença de peso para a anterior. "Em dia" até 180 dias; depois, "Vencida". Quem nunca foi avaliado não tem o cartão.
- **Painel:** o aviso de entrada ganha a aba "Avaliação" com a próxima do dia. No computador, e com o check-in desligado, o card "Avaliações de hoje" ocupa o lugar que era dele no desenho. (Com o check-in ligado, esse lugar é do card de ausentes.)
- **Agenda:** "Vencidas" conta alunos ativos cuja última avaliação tem mais de 180 dias. "Alunos sem avaliar há 6 meses" soma a isso quem nunca foi avaliado e está cadastrado há mais de 180 dias. Aluno novo, sem avaliação, não entra em nenhum dos dois.

## A migration

`b15d1e2f3a40_avaliacoes_fisicas.py`, depois da `b14c0d1e2f30`. Cria as duas tabelas, com chaves estrangeiras e índices; não toca em nenhuma existente. O downgrade apaga as duas (e as avaliações gravadas).

## Como foi testado

- **`pytest`: 397 de 397** (45 novos em `tests/test_avaliacoes.py`): agenda vazia e com cada grupo; o que não aparece (remarcada, realizada, outra academia); vencidas e sem avaliar; escolha do aluno; formulário; plano que inclui; gravar o horário; 9 agendamentos inválidos; horário ocupado; remarcar; inativo e outra academia; formulário da avaliação; cálculo de IMC e RCQ com o que foi "digitado" ignorado; sem cintura não há RCQ; 10 medidas inválidas; envio duplo; resultado da primeira e da reavaliação (com as cores); histórico; cartão do perfil para cada papel; aviso e card do painel; recepção barrada; 404 para outra academia; sem login; GET não grava; aluno com avaliação não é excluído.
- **Migration num Postgres temporário** (criado e apagado pelo teste): **16 checagens**.
- **Navegador (Playwright):** avaliações **68 de 68**, celular (390 px, toque, claro) e computador (1440 px, escuro): agendar pela tela, validação da data, aviso e card do painel, as quatro etapas com a prévia de IMC e RCQ, resultado com a comparação, histórico com o gráfico, perfil, sem "None", sem rolagem lateral, console limpo. As outras telas foram rodadas de novo, sem mudança: login 60 de 60, painel 74 de 74, alunos 32 de 32, planos 31 de 31, cobrança 33 de 33, frequência 31 de 31, relatórios 28 de 28, configurações 29 de 29, equipe 34 de 34, treinos 79 de 79.
- **Varredura de rotas por papel**, comparada com a `front-11-avaliacoes`: só mudou o que é desta branch.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Como está | Evidência |
|---|---|---|
| Isolamento entre academias | Aluno por `da_conta(Aluno)`; avaliação e horário por `da_conta(...)`. Outra conta: 404 | `test_avaliacao_de_outra_academia_da_404`, `test_agendar_para_inativo_ou_de_outra_academia` |
| Id enviado na mão | Avaliador de outra academia ou da recepção é recusado; `remarcar` e `ag` de outro aluno ou de outra academia não mexem em nada | `test_agendamento_invalido_avisa_e_nao_grava`, `test_remarcar_guarda_o_horario_antigo_como_remarcado`, `test_avaliacao_de_outra_academia_da_404` |
| Papéis / dado de saúde | Só dono e instrutor abrem medidas; a recepção é barrada no servidor (não só no botão) | `test_recepcao_agenda_mas_nao_abre_medidas`, `test_perfil_do_aluno_mostra_a_ultima_avaliacao` |
| Valor calculado não vem do cliente | `imc` e `rcq` enviados no formulário são ignorados | `test_registrar_calcula_imc_e_rcq_no_servidor` |
| Validação | Faixas por medida; `nan`, texto e negativos recusados; limites de tamanho nos textos | `test_medida_invalida_avisa_e_nao_grava` |
| CSRF | Os dois formulários mandam `csrf_token`; tudo que grava é POST | — |
| GET não grava | Abrir qualquer tela (inclusive com `?ag=` e `?remarcar=`) não muda o banco | `test_abrir_telas_nao_grava_nada` |
| Upload | **O servidor não lê os arquivos do formulário.** O bloco de fotos está escondido | `test_formulario_da_avaliacao` |
| Dados pessoais no link | O resultado vai no endereço do WhatsApp, que abre no aparelho de quem usa; o servidor não envia nada a terceiros | `test_resultado_da_primeira_avaliacao` |
| Exclusão | Aluno com avaliação não é apagado (nem a avaliação some em silêncio) | `test_aluno_com_avaliacao_nao_pode_ser_excluido` |

## Como revisar

```bash
git fetch origin
git diff origin/front-11-avaliacoes..origin/back-15-avaliacoes --stat
git diff origin/front-11-avaliacoes..origin/back-15-avaliacoes -- app/ migrations/
```

Ordem sugerida: `models.py` (fim do arquivo) e a migration; `avaliacao_service.py` (o texto do começo traz as três regras); `avaliacoes/routes.py`; `helpers/whatsapp.py`.

## Para decidir (Adauto e Diogo)

1. **A recepção deve abrir as medidas da avaliação?** Hoje não (dado de saúde). Se a academia do primeiro cliente funciona com a recepção medindo, é trocar uma linha (`PAPEIS_QUE_AVALIAM`). Vale levar ao advogado junto com a LGPD.
2. **Preço da avaliação avulsa.** O front mostra "R$ 60,00" fixo de exemplo, mas não existe campo nas Configurações para o dono informar. Com o campo no front, gerar a cobrança ao agendar é pequeno. Até lá: "cobrada à parte", recebida pela diária avulsa.
3. **Fotos da avaliação.** O formulário do front tem frente, lado e costas. Guardar foto pede decidir **onde** (disco do servidor ou serviço de arquivos), limite de tamanho e termo de autorização do aluno. Fica com a `back-18` (upload seguro) e a `back-19` (LGPD).
4. **PDF da avaliação e do histórico.** Os dois botões do front só mostram um aviso. Pede biblioteca nova (regra 4), como o PDF da ficha.
5. **Percentual de gordura.** O front diz que "é calculado pelo sistema" a partir das dobras. As fórmulas usam sexo e idade, e o cadastro do aluno não tem sexo. As dobras ficam gravadas; o percentual não é calculado.
6. **Horários da agenda** fixos de 06:00 a 20:00, de hora em hora. Se precisar de meia hora ou seguir o horário de funcionamento da academia, é ajuste no serviço.
7. **Validade da avaliação: 180 dias** para "em dia" e "vencida". O front fala em "reavaliação de 90 dias" em exemplos e em "6 meses" no card; usei 6 meses.
8. **Quantas avaliações o plano inclui:** o sistema olha só se o plano inclui alguma; **não conta** quantas o aluno já usou no período.
9. Detalhes do front, para o Adauto ver: o assistente mostra uma etiqueta com a faixa do IMC ("Peso normal", "Sobrepeso") enquanto se digita. O servidor não guarda nem repete essa classificação; se a ideia é "medida, não diagnóstico", vale tirar a etiqueta. A regra de cor do resultado (verde ou vermelho) é fixa: peso, IMC e cintura menores são "a favor"; braço e coxa maiores são "a favor". Para um aluno que quer ganhar peso, a cor do peso fica invertida.

## Riscos

- **Dado de saúde no banco sem criptografia de coluna**, como o resto do cadastro. A proteção é o isolamento por conta, o papel e (na produção) o HTTPS e o acesso ao banco. Entra na revisão da `back-19-lgpd`.
- **O aviso do painel abre uma vez por sessão do navegador** (regra do front): quem agenda algo para hoje depois de já ter entrado só vê o aviso no próximo login. O card e a agenda mostram na hora.
- **Sem lembrete automático** para o aluno. O lembrete de véspera entra com o módulo de mensagens (`back-16`), como link do WhatsApp.
- **Não há botão de cancelar** um horário no front: o caminho é remarcar. Horário que passou sem avaliação fica em "Não realizadas" até ser remarcado ou a avaliação ser feita.
