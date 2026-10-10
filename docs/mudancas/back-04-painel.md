# back-04-painel — o painel do front novo funcionando no backend real

| | |
|---|---|
| **Branch** | `back-04-painel` |
| **Sai de** | `front-02-painel` (que traz só os templates) |
| **Data** | 10/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefas da lista "Tarefas do backend — Diogo"** | 4.2 (contexto global), parte da 5.1 (painel), parte da 3.7 (páginas de erro) e o começo da 4.1 (nomes de rota do front) |
| **Fica de fora** | Notificações, painel do instrutor, metas, frequência e avaliações: dependem de tabelas que ainda não existem. |

## Resumo

Antes desta branch só a tela de login era do front novo; depois de entrar, tudo era o front antigo. Agora, depois do login, abre o **painel novo**, com o layout novo (menu lateral no PC, barra de abas e gaveta no celular) e com os números calculados do banco.

As outras telas ainda são as antigas. O menu novo leva a elas por pontes temporárias; as seções que ainda não têm backend mostram "Em construção".

**Nenhuma migration, nenhuma dependência nova, nenhum arquivo apagado.**

## Arquivos

| Arquivo | Tipo | O que mudou |
|---|---|---|
| `app/blueprints/painel/routes.py` | novo | blueprint `painel`: `index` em `/` e `notificacoes` |
| `app/services/painel_service.py` | novo | calcula todos os números do painel, só da conta logada |
| `app/helpers/contexto.py` | novo | `usuario`, `academia` e `oferecer_digital` em todo template |
| `app/helpers/erros.py` | novo | páginas de erro 403, 404 e 500 do front |
| `app/blueprints/pendentes.py` | novo, **temporário** | endpoints das seções sem backend ("em construção") |
| `app/templates/em_construcao.html` | novo, **temporário** | a página "em construção" |
| `app/__init__.py` | alterado | registra o que foi criado acima |
| `app/routes.py` | alterado | `main.homepage` saiu de `/` e virou atalho para o painel |
| `app/blueprints/auth/routes.py` | alterado | depois do login vai para `painel.index` |
| `app/blueprints/{alunos,planos,exercicios}/routes.py` | alterado | pontes temporárias, no fim de cada arquivo |
| `app/templates/painel/index.html` | alterado | 6 ajustes para dado que o backend ainda não tem (lista abaixo) |
| `tests/test_painel.py`, `tests/navegador/painel_navegador.py` | novo | testes |

Toda linha alterada em arquivo que já existia tem o comentário `[back-04-painel]`.

## Cada mudança: antes, depois e por quê

### 1. A página inicial

- **Antes:** `/` era `main.homepage`, com a tela inicial antiga (`templates/index.html`).
- **Depois:** `/` é `painel.index`, com `templates/painel/index.html`. O `main.homepage` continua existindo, em `/inicio-antigo/`, e só redireciona para o painel.
- **Por quê manter o `main.homepage`:** as telas antigas ainda o usam em links e redirects. Sem ele, elas dariam `BuildError`.
- **O que ficou sem uso:** `templates/index.html`, `notificacao.html` (o antigo) e `services/dashboard_service.py`. Não apaguei: são arquivos do Diogo. Saem quando a última tela antiga for trocada.

### 2. De onde vem cada número (`painel_service.py`)

Tudo usa `da_conta(...)`, o filtro único da `back-03`. Regras, para o número do card e a lista que ele abre nunca discordarem:

| Indicador | Como é calculado |
|---|---|
| Alunos ativos e inativos | coluna `ativo` |
| Vencimento do aluno | a maior `data_vencimento` entre os pagamentos dele |
| Inadimplência | alunos ativos com vencimento anterior a hoje; o valor é a soma do preço do plano de cada um |
| Vencem este mês | alunos ativos, ainda em dia, com vencimento neste mês |
| Faturamento do mês | soma dos pagamentos com `data_pagamento` no mês |
| Variação do faturamento | contra o mês anterior. Sem pagamento no mês anterior, o selo não aparece |
| Ticket médio | faturamento do mês ÷ alunos ativos |
| Novas matrículas | `data_cadastro` no mês; o selo é a diferença para o mês anterior |
| Aniversários | alunos ativos que fazem aniversário hoje |
| De onde vem o faturamento | pagamentos do mês agrupados pelo plano atual do aluno |

**Atenção, Diogo — decisões que tomei e você pode querer mudar:**

- **Aluno sem nenhum pagamento registrado não conta como inadimplente.** Não há vencimento para comparar. É o mesmo critério do seu `PagamentoService.status_pagamento` (`sem_pagamento`).
- **O valor da inadimplência é o preço do plano**, não o valor do último pagamento.
- **Tudo é calculado em Python**, depois de buscar alunos, planos e pagamentos da conta. Para uma academia de algumas centenas de alunos é rápido; se crescer, vira consulta agregada no banco.

### 3. O que ainda NÃO dá para calcular

| O quê | Por quê | O que a tela mostra |
|---|---|---|
| Ausentes há mais de 15 dias | não existe frequência | o card não aparece (`checkin_ativo` falso) |
| Meta de alunos e de faturamento | não existe Configurações | a linha e a frase da meta não aparecem |
| Notificações | módulo não criado | sino sem bolinha; a tela mostra "Em construção" |
| Avaliação do dia | módulo não criado | a aba não aparece no popup de avisos |
| Histórico de alunos ativos por mês | o banco não guarda quando um aluno foi inativado | **aproximação**: para cada mês, quantos dos alunos ativos hoje já estavam cadastrados. Quem saiu no caminho não aparece |

A regra do projeto é "sem dado não vira zero": onde não há dado, o serviço devolve `None` e a tela esconde o item.

### 4. `usuario` e `academia` em todo template (tarefa 4.2)

- **Antes:** não existia. O cabeçalho, o menu e o rodapé do front novo leem essas variáveis em toda página.
- **Depois:** `app/helpers/contexto.py` registra um `context_processor`.
- **PROVISÓRIO, e é importante saber:**
  - `academia.nome` é o texto fixo **"Minha academia"**. O banco não tem onde guardar o nome da academia;
  - todo usuário é tratado como **dono** (`papel`). Não existe a coluna;
  - `checkin_ativo` e `pix_ligado` são falsos, porque os módulos não existem.
- Tudo isso passa a vir do banco na `back-06-contas-e-papeis`, que pede migration. Só as funções `_usuario()` e `_academia()` mudam.

### 5. Seções sem backend e pontes (`pendentes.py`)

O menu e o painel chamam `url_for()` para todas as seções. Endpoint que não existe dá `BuildError` e a página inteira vira erro 500. Por isso:

- **"Em construção"** (11 endpoints): `config.index`, `relatorios.index`, `relatorios.admin`, `mensagens.index`, `frequencia.index`, `avaliacoes.agenda`, `avaliacoes.agendar`, `avaliacoes.registrar`, `agenda.index`, e os dois envios do painel (`cobrancas.diaria` e `cobrancas.lembrete_lote`), que avisam "ainda não está disponível" e voltam. Mais `painel.notificacoes`.
- **Pontes para as telas antigas** (10 endpoints): `alunos.lista`, `alunos.novo`, `alunos.buscar`, `alunos.detalhe`, `alunos.renovar`, `alunos.acesso_busca`, `planos.lista`, `planos.novo`, `exercicios.lista` e `treinos.biblioteca`. Cada uma só redireciona para a rota antiga equivalente (a `alunos.acesso_busca`, que alimenta um popup, devolve um aviso de "ainda não disponível"); nenhuma mexe em dado.
- **Endereços:** são os do contrato do front (`/alunos`, `/planos/novo`, `/configuracoes`…). As rotas antigas (`/alunos/listar/` etc.) continuam iguais.
- **É temporário.** Cada linha sai na branch que criar a tela de verdade.

### 6. Páginas de erro (parte da tarefa 3.7)

- **Antes:** endereço inexistente mostrava a página branca padrão do Flask.
- **Depois:** `errors/403.html`, `404.html` e `500.html` do front. Nenhuma mostra dado técnico. O 500 também desfaz a transação pendente do banco.

## Os 6 ajustes no template do painel

O `painel/index.html` foi escrito para o servidor de exemplo, que sempre tem todos os dados. Com dado real faltando, apareceria "+None%" e "meta None" na tela. Cada ajuste está marcado com `{# [back-04-painel] ... #}` no arquivo.

| # | Trecho | Ajuste |
|---|---|---|
| 1 | selo do card "Faturamento" | some se não houver mês anterior; fica vermelho e sem o "+" quando caiu |
| 2 | selo do card "Novas matrículas" | variação negativa não leva o "+" |
| 3 | card "Avaliações de hoje" (desktop) | **escondido**: o template tinha o número `2` fixo |
| 4 | frase "meta N marcada em amarelo" | some se não houver meta |
| 5 | selo "+N% no ano" | some se não houver base; negativo não leva o "+" |
| 6 | popup "Avaliações de hoje" | **escondido**: tinha os nomes fixos "Camila Duarte" e "Pedro Henrique" |

**Atenção, Adauto:** o `vale-tec-front` do Drive é só leitura e não foi tocado. Estes 6 ajustes existem **só no repositório**. Se o `painel/index.html` for copiado do Drive de novo, eles se perdem. Vale levá-los para o Drive.

## Botões que ainda são demonstração

O front tem botões que só mostram um aviso na tela e não fazem nada de verdade. Não mudei: são parte do desenho e viram ação real na branch de cada módulo.

- "WhatsApp aberto para …" (tabela de alunos e popups);
- "Mensagens de parabéns enviadas" e "Lembretes de renovação enviados" (popup de avisos);
- a mensagem sugerida de aniversário, com "10% de desconto", é texto fixo do template.

Os botões de WhatsApp dos popups "Vencem este mês" e "Novas matrículas" são de verdade: abrem o `wa.me` com o telefone do aluno.

## Como foi testado

- **`pytest`: 49 de 49.** Os 19 novos (`tests/test_painel.py`) cobrem:
  - cada indicador, com uma academia montada com situações conhecidas e a data fixada;
  - as listas batendo com os números;
  - os dois gráficos;
  - que nada de outra conta entra em nenhum número;
  - academia vazia, sem nenhum aluno, não quebra;
  - a página abre no layout novo e não deixa "None" escapar para a tela;
  - as 9 pontes, as telas pendentes e a página 404.
- Os testes da `back-03` continuam passando sem mudança de regra. Entre eles, o que percorre **todas** as rotas do app e exige login: as rotas novas entraram sozinhas.
- **Navegador (Playwright): painel 66 de 66, login 60 de 60.** Celular de 390 px com toque e desktop de 1440 px, claro e escuro:
  - entrar pela tela de login e cair no painel novo;
  - popup de avisos abre sozinho e fecha;
  - nenhum "None" na tela, sem rolagem lateral, gráfico desenhado;
  - card abre o popup com a lista;
  - gaveta e barra de abas no celular, menu lateral no PC;
  - "Configurações" mostra "Em construção" no layout novo;
  - "Alunos" leva à tela antiga;
  - sair volta ao login, e o painel pede login de novo.
- **Smoke de rotas** contra a `back-03`: nenhuma rota que já existia mudou de status; só entraram as novas.
- **Não testado:** iPhone de verdade; o painel do instrutor (não existe ainda).

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Situação |
|---|---|
| Isolamento entre contas (§1) | Todas as consultas do painel usam `da_conta`. Há teste com duas academias. |
| Login obrigatório | `exigir_login_em(painel_blueprint)`; pendentes e pontes com `@login_required` ou dentro de blueprint protegido. Coberto pelo teste que percorre todas as rotas. |
| GET que altera dado (§4) | Nenhum. Pontes e pendentes só leem ou redirecionam; os dois envios do painel são POST com CSRF. |
| Papéis (§2) | **Não existe.** Todo usuário vê o painel completo, com os números de dinheiro. Entra na `back-06`. |
| Páginas de erro sem dado técnico (§5) | Feito para 403, 404 e 500. |
| Dado de usuário em atributo HTML | O gráfico usa `tojson\|forceescape`, como a skill pede. Nomes de aluno passam pelo escape padrão do Jinja. |

## Como revisar

```bash
git fetch origin
git diff origin/front-02-painel..origin/back-04-painel -- app     # backend e os 6 ajustes do template
git diff origin/front-02-painel..origin/back-04-painel -- tests   # testes
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests -q
```

Sugestão de leitura: `app/services/painel_service.py` primeiro (é onde estão as regras de negócio), depois `app/blueprints/pendentes.py`.

## Riscos

- **A tela inicial mudou para todo mundo.** Quem entra passa a ver o painel novo em vez da tela antiga. As telas antigas continuam acessíveis pelo menu novo.
- **Experiência misturada.** Painel novo, demais telas antigas, com visual diferente. É esperado até cada tela ser trocada.
- **Números novos na tela.** Faturamento e inadimplência passam a aparecer com base nos pagamentos registrados. Se os pagamentos antigos não foram lançados no sistema, os números saem baixos.
- **"Minha academia"** aparece como nome até a `back-06`.
