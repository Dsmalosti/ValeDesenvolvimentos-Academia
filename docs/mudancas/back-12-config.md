# back-12-config — configurações da academia

| | |
|---|---|
| **Branch** | `back-12-config` |
| **Sai de** | `front-08-config` (que só traz os templates, copiados do Drive) |
| **Data** | 12/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefa** | 5.9 da lista "Tarefas do backend — Diogo": configurações |
| **Tem migration** | **Sim:** `migrations/versions/b12a8b9c0d10_configuracoes_da_conta.py`. Acrescenta 10 colunas em `contas` e cria `modelos_mensagem`. Não apaga nem converte dado. **Leia o aviso sobre a inatividade automática, na seção "A migration".** |

## Resumo

O menu "Configurações" deixa de ser "em construção". O dono passa a:

- trocar **nome, CNPJ, telefone, e-mail, cidade e endereço** da academia (o nome aparece no cabeçalho na hora);
- informar o **horário de funcionamento**;
- **ligar e desligar o check-in** (o que faltava da frequência);
- definir o prazo da **inatividade automática**;
- definir as três **metas**, que viram a linha tracejada dos gráficos;
- personalizar os **modelos de mensagem** de WhatsApp (dono e recepção);
- ver a tela de **recebimento**, com de onde veio cada confirmação de pagamento do mês.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/models.py` | 10 colunas novas em `Conta`; modelo novo `ModeloMensagem`. |
| `migrations/versions/b12a8b9c0d10_configuracoes_da_conta.py` | **Novo.** A migration. |
| `app/services/config_service.py` | **Novo.** Leitura e gravação de cada configuração, e a regra de inatividade. |
| `app/blueprints/config/routes.py` | **Novo.** As rotas `config.*`. |
| `app/blueprints/painel/routes.py` | Ao abrir o painel, roda a regra de inatividade (no máximo uma vez por dia). |
| `app/services/painel_service.py` | Meta de alunos ativos no gráfico; meta de faturamento e "% da meta" no card. |
| `app/services/relatorio_service.py` | Meta de faturamento e de retenção nos gráficos; função `retencao_aos_90_dias()`. |
| `app/blueprints/pendentes.py`, `app/__init__.py` | `config.index` saiu das telas "em construção". |
| `app/templates/config/recebimento.html`, `app/templates/config/_metas.html` | **1 ajuste marcado em cada** (ver "Ajustes nos templates"). |
| `tests/test_configuracoes.py` | **Novo.** 30 testes. |
| `tests/navegador/config_navegador.py` | **Novo.** Teste no navegador. |
| `tests/navegador/painel_navegador.py` | A checagem de "seção ainda em construção" passou a usar Mensagens (Configurações virou tela de verdade). |

## Cada mudança: antes, depois e por quê

### 1. Rotas

| Endereço | Endpoint | Quem pode |
|---|---|---|
| `GET /configuracoes` (`?aba=`) | `config.index` | todos; o instrutor não vê a aba Metas |
| `POST /configuracoes/academia` | `config.salvar` | dono |
| `POST /configuracoes/horario` | `config.horario` | dono |
| `POST /configuracoes/funcionalidade` | `config.funcionalidade` | dono |
| `POST /configuracoes/metas` | `config.metas` | dono |
| `POST /configuracoes/mensagem` | `config.mensagem` | dono e recepção |
| `GET /configuracoes/recebimento` | `config.recebimento` | dono e recepção |
| `POST /configuracoes/recebimento/pix` | `config.pix_alternar` | dono. **Só avisa:** PIX automático ainda não existe |
| `POST /configuracoes/equipe` | `config.membro` | dono. **Só avisa:** convidar e gerenciar a equipe entram na `back-13` |

Antes só existia `config.index`, como tela "em construção". A lista da equipe **aparece** nesta tela (quem tem acesso e com qual papel), mas os botões de convidar, trocar papel e remover ainda só avisam.

### 2. Onde cada coisa fica guardada

Como a tarefa 5.9 pede, dados, horário, metas e funcionalidades são **colunas da conta**:

| Coluna em `contas` | O que é |
|---|---|
| `horario_semana`, `horario_sabado`, `horario_domingo` | texto livre, como aparece para o aluno ("06h - 22h", "Fechado"). Vazio aparece como "Não informado". |
| `meta_alunos_ativos`, `meta_faturamento`, `meta_retencao` | as três metas. Vazio = sem meta. |
| `inatividade_ligada` (padrão sim), `inatividade_dias` (padrão 60) | a regra "o aluno vira Inativo sozinho depois de X dias sem renovar". |
| `inatividade_conferida_em` | último dia em que essa regra rodou para a conta. |
| `lembretes_ligados` (padrão sim) | só é guardado; quem vai usar é o módulo de mensagens. |

`checkin_ativo` e `pix_ligado` já existiam desde a `back-06`.

**Modelos de mensagem** ficam na tabela nova `modelos_mensagem` (`conta_id`, `tipo`, `texto`), com no máximo um por tipo em cada conta. Só existe linha para o modelo que a academia **alterou**; os outros vêm do texto padrão do código. Assim, melhorar um texto padrão chega a todo mundo que não personalizou.

### 3. Metas nos gráficos

| Meta | Onde aparece |
|---|---|
| Alunos ativos | linha do gráfico "Alunos ativos por mês", no painel |
| Faturamento | "% da meta" no card de faturamento do painel, e a linha do gráfico de receita do administrativo (sem meta, a linha é a média) |
| Retenção | linha do gráfico "Quanto tempo o aluno fica" |

Sem meta definida nada disso aparece, como antes.

### 4. Inatividade automática

É a regra que o front descreve: "O aluno vira Inativo sozinho depois de X dias sem renovar a matrícula".

- Desativa o aluno **ativo** cujo vencimento passou há mais de X dias. Não apaga nada, e a data da inativação fica guardada.
- Quem **nunca pagou** não tem vencimento e não é tocado.
- Roda **quando o painel da academia é aberto**, no máximo uma vez por dia por conta. Fiz assim para a regra funcionar sem depender de uma tarefa agendada no servidor, que ainda não existe.

É o único lugar do sistema em que abrir uma tela (um GET) altera dado. É uma rotina automática, a mesma para qualquer pessoa da conta, e repetir não muda o resultado; mesmo assim fica registrado aqui para o Diogo avaliar.

### 5. Validações

- **Dados da academia:** só o nome é obrigatório (até 120 letras). CNPJ, se vier, tem de ter 14 números e é gravado com a pontuação. E-mail, se vier, tem de ter formato válido.
- **Horário:** os três campos preenchidos, até 40 letras cada.
- **Mensagem:** tipo conhecido, texto de 1 a 500 letras (o limite do campo no front).
- **Funcionalidade:** chave conhecida; prazo de inatividade de 15 a 365 dias.
- **Metas:** alunos de 1 a 100.000; faturamento em reais, no formato `35.000,00`; retenção de 1 a 100. Com erro, a tela volta com os avisos e o que foi digitado.

### 6. Recebimento

A tela mostra a situação do PIX automático (desligado) e, no mês, quantos pagamentos foram confirmados pelo banco, quantos em PIX na mão, na maquininha e em dinheiro. O botão "Ligar PIX" **não liga nada**: avisa que o PIX automático depende de um provedor de pagamento, que ainda não foi escolhido.

## Ajustes nos templates (diferem do Drive)

Marcados com `{# [back-12-config] ... #}`:

1. `config/recebimento.html`: "Setembro ·" (fixo) virou o mês de verdade.
2. `config/_metas.html`: a dica da meta de retenção mostrava "Hoje: X%" sempre; sem aluno com 90 dias de matrícula ela diz "sem dado ainda".

**Para o Adauto:** levar os dois para o front do Drive.

## A migration

`b12a8b9c0d10_configuracoes_da_conta.py`, depois da `b11f7a8b9c00`.

- **Sobe:** acrescenta as 10 colunas em `contas` (as contas que já existem ficam com inatividade ligada em 60 dias e lembretes ligados) e cria `modelos_mensagem`.
- **Desce:** remove as colunas e a tabela (as configurações gravadas se perdem).

> **Atenção:** com a inatividade ligada por padrão, na **primeira vez que o painel de cada conta abrir** depois desta branch, os alunos ativos com vencimento passado há mais de 60 dias são desativados. Nada é apagado, e basta um pagamento para o aluno voltar a ativo. Se não quiser esse comportamento num banco com dados, desligue antes: `UPDATE contas SET inatividade_ligada = false`.

## Como foi testado

- **`pytest`: 287 de 287** (30 novos em `tests/test_configuracoes.py`): cada aba abre sem "None"; equipe, modelos padrão e horário "Não informado"; instrutor não vê metas; dados da academia (válidos e 4 inválidos) e o nome novo no painel; horário; modelo de mensagem por academia (a outra academia continua no padrão), 3 inválidos e texto com HTML; ligar e desligar o check-in; inatividade e lembretes; metas nos gráficos do painel e do administrativo; metas inválidas; recebimento; quem pode o quê (recepção e instrutor recebem 403 em 6 rotas); equipe ainda não gerenciável; inatividade automática (desativa quem passou do prazo, poupa quem não passou, quem nunca pagou e a outra academia; roda uma vez por dia; respeita o desligado).
- **Migration num Postgres temporário:** 15 checagens. Sobe; as contas ficam com os padrões; o banco recusa dois modelos do mesmo tipo na mesma conta; `flask db check` sem diferença; desce; volta a bater com o modelo anterior; sobe de novo.
- **Navegador (Playwright):** configurações **29 de 29**; relatórios 28 de 28, frequência 31 de 31, cobrança 33 de 33, alunos 32 de 32, planos 31 de 31, painel 74 de 74, login 60 de 60. Celular de 390 px com toque (claro) e computador de 1440 px (escuro). Fotos abertas e conferidas.
- **Varredura de todas as rotas GET por papel**, comparada com a `front-08-config`: mudou só o que é desta branch.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Como está | Evidência |
|---|---|---|
| Isolamento entre academias | Toda gravação é na conta de quem está logado (`current_user.conta`); não há id de conta vindo do formulário. Modelos de mensagem passam por `da_conta(...)`. A regra de inatividade só toca alunos da conta que abriu o painel. | `test_modelo_de_mensagem_e_por_academia`, `test_quem_nao_renova_ha_mais_de_60_dias_vira_inativo_sozinho` |
| Papéis no servidor | `papel_requerido` em cada rota que grava | `test_so_o_dono_muda_a_academia_e_a_recepcao_so_as_mensagens` |
| CSRF e métodos | Tudo o que grava é POST, com `csrf_token` | — |
| Texto digitado pelo usuário | O Jinja escapa; o modelo de mensagem não vira HTML | `test_texto_da_mensagem_nao_vira_codigo_na_tela` |
| Envio de arquivo | O formulário manda a logo, e o servidor **ignora** o arquivo (nada é gravado em disco). Limite de tamanho de envio continua pendente para a `back-18`. | — |
| Dinheiro | Meta de faturamento em `Decimal`, formato conferido | `test_metas_invalidas_voltam_com_os_avisos` |

## Como revisar

```bash
git fetch origin
git diff origin/front-08-config..origin/back-12-config --stat
git diff origin/front-08-config..origin/back-12-config -- app/ migrations/
```

Ordem sugerida: `models.py` e a migration, `config_service.py`, `config/routes.py`, e os trechos marcados em `painel/routes.py`, `painel_service.py` e `relatorio_service.py`.

## Para decidir (Adauto e Diogo)

1. **Inatividade automática ligada por padrão, com 60 dias.** É o que o front mostra. Preferem que comece desligada?
2. **Rodar a regra ao abrir o painel** (em vez de tarefa agendada). Quando houver servidor de produção, dá para trocar por uma tarefa diária.

## Riscos

- **O aviso da migration, acima:** alunos vencidos há mais de 60 dias são desativados na primeira abertura do painel.
- **A logo não é gravada.** O botão "Trocar logo" abre o seletor, mas o servidor ignora o arquivo. Envio de imagem ficou para depois do lançamento.
- **Recepção e instrutor veem os formulários do dono** (o template não esconde por papel); ao salvar, recebem a página de "sem permissão". Esconder é ajuste de front.
- **"Lembretes automáticos" ainda não faz nada:** o interruptor é guardado e será lido pelo módulo de mensagens.
- **Não há tela para trocar o modelo da conta** (academia ou personal). Isso chega com a variante Personal.
