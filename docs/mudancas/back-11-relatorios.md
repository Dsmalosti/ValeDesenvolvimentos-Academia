# back-11-relatorios — painel administrativo: fechamento do mês, custos, retenção e risco

| | |
|---|---|
| **Branch** | `back-11-relatorios` |
| **Sai de** | `front-07-relatorios` (que só traz os 2 templates, copiados do Drive) |
| **Data** | 12/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefa** | 5.8 da lista "Tarefas do backend — Diogo": relatórios e ponto de equilíbrio |
| **Tem migration** | **Sim:** `migrations/versions/b11f7a8b9c00_custos_e_data_de_inativacao.py`. Cria `custos` e acrescenta `alunos.data_inativacao`. Não apaga nem converte dado. |

## Resumo

O menu "Administrativo" (só dono e recepção) deixa de ser "em construção" e mostra, numa página:

- **faturamento por forma de pagamento** e receita dos últimos 12 meses;
- **ponto de equilíbrio**: o recebido contra os **custos fixos**, que o dono cadastra na própria tela;
- **fechamento**: recebido, a receber, em atraso, custos e quanto sobrou ou faltou;
- **lançamentos** do período, com filtro e planilha (CSV);
- com o check-in ligado, o **mapa de movimento** por dia e horário;
- **quanto tempo o aluno fica**, **este mês contra o anterior** e **quem está mais perto de cancelar**.

A regra desta branch: **número que o banco não sustenta não é inventado**. Onde falta história, o bloco diz "sem dado".

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/models.py` | Modelo novo `Custo`; coluna nova `Aluno.data_inativacao`, preenchida sozinha quando `ativo` muda. |
| `migrations/versions/b11f7a8b9c00_custos_e_data_de_inativacao.py` | **Novo.** A migration. |
| `app/services/relatorio_service.py` | **Novo.** Todas as contas da tela. |
| `app/blueprints/relatorios/routes.py` | **Novo.** As rotas `relatorios.*`. |
| `app/services/painel_service.py` | O gráfico "Alunos ativos por mês" passa a contar quem saiu depois daquele mês. |
| `app/blueprints/pendentes.py`, `app/__init__.py` | `relatorios.index` e `relatorios.admin` saíram das telas "em construção". |
| `app/templates/relatorios/admin.html` | **13 ajustes marcados** (seção "Ajustes no template"). |
| `tests/test_relatorios.py` | **Novo.** 21 testes. |
| `tests/conftest.py` | Ajudante `criar_custo`. |
| `tests/navegador/relatorios_navegador.py` | **Novo.** Teste no navegador. |

## Cada mudança: antes, depois e por quê

### 1. Rotas

| Endereço | Endpoint | Antes |
|---|---|---|
| `GET /relatorios/painel` | `relatorios.admin` | tela "em construção" |
| `GET /relatorios` | `relatorios.index` | tela "em construção". Agora leva ao painel administrativo: o próprio front juntou as duas telas e tirou o botão do menu |
| `GET /relatorios/exportar?formato=csv` | `relatorios.exportar` | não existia |
| `POST /relatorios/custos` | `relatorios.custo_salvar` | não existia |
| `POST /relatorios/custos/<id>/excluir` | `relatorios.custo_excluir` | não existia |

Todas só para dono e recepção (`exigir_papel_em` no blueprint inteiro). `?periodo=` aceita `semana`, `mes`, `3m`, `6m`, `9m` e `ano`.

**Excel e PDF ainda não existem.** Os botões estão na tela; o servidor avisa que por enquanto sai CSV. Gerar os dois pede bibliotecas novas (regra 4) e já estava combinado para depois do primeiro cliente.

### 2. Tabela `custos`

`id`, `conta_id`, `descricao` (até 100 letras) e `valor` (por mês). É a tabela citada na tarefa 5.8. Limite de 60 custos por conta.

### 3. Coluna `alunos.data_inativacao`

O banco não guardava **quando** um aluno foi desativado. Sem isso não dá para dizer quanto tempo um aluno ficou, nem quantos saíram em cada mês.

A coluna é preenchida e apagada **sozinha** sempre que `ativo` muda (função `_marca_a_inativacao`, em `models.py`, logo depois da classe `Aluno`). Fica ali, e não em cada rota, porque `ativo` muda em vários lugares: o botão de desativar, o botão de status da tela antiga e a reativação ao pagar. Assim nenhum deles esquece.

**Quem já estava inativo antes desta branch fica sem data**, e por isso fica **de fora** das contas de retenção e de churn. A alternativa seria inventar uma data.

### 4. De onde vem cada número

| Bloco | Conta |
|---|---|
| Recebido e formas | Soma de `pagamentos.valor_pago` no período. Débito e crédito aparecem juntos como "Cartão", que é o que o filtro do front oferece. |
| "+11% vs ..." | Mês: contra o mês passado **até o mesmo dia** (comparar meio mês com um mês inteiro daria sempre "piorou" na primeira quinzena). Outros períodos: contra o trecho de mesmo tamanho logo antes. Sem base, o selo não aparece. |
| Ponto de equilíbrio | Recebido menos os custos. Os custos são mensais: num período de 3 meses o mínimo é 3 vezes a soma; numa semana, 7/30 dela. |
| A receber, em atraso, ticket | **Os mesmos números do painel** (a tela chama o `painel_service`), para as duas telas nunca discordarem. |
| Receita mês a mês | Últimos 12 meses. A linha tracejada é a média, até existir meta de faturamento (Configurações). |
| Lançamentos | Pagamentos do período (pago) e cobranças em aberto hoje (em aberto, ou em atraso se o período já começou). |
| Mapa de movimento | Entradas dos últimos 28 dias, em faixas de 3 horas, de 0 (vazio) a 4 (lotado) em relação à faixa mais cheia. |
| Quanto tempo o aluno fica | Para cada marco (30, 60, 90, 180, 365 dias): dos alunos matriculados há pelo menos esse tempo, quantos por cento continuaram até lá. Marco sem aluno na base não aparece. |
| Este mês contra o anterior | Churn (quem saiu no mês, sobre quem era ativo no começo dele), inadimplência e ausentes. Cada linha só aparece se der para calcular **os dois meses**. |
| Quem está mais perto de cancelar | Nota de 0 a 100 por aluno ativo. Aparece quem tem menos de 50. |

**A nota de risco** (função `_nota_de_risco`): começa em 100 e perde 3 pontos por dia de pagamento atrasado (até 60), 2 pontos por dia além de uma semana sem vir (até 50, só com check-in) e 10 pontos nos primeiros 30 dias de casa. É uma regra simples e explicável, não uma previsão estatística; os pesos estão num lugar só e são fáceis de mudar.

### 5. Gráfico "Alunos ativos por mês" do painel

Antes contava só os alunos ativos **hoje**: quem tinha saído sumia de todos os meses, e a curva nunca caía. Agora conta também quem foi desativado depois do fim de cada mês. Estava anotado no roadmap como achado da `back-04`.

## Ajustes no template `relatorios/admin.html` (diferem do Drive)

O template do Drive tem textos presos ao exemplo ("setembro", "acima do mínimo") e assume que sempre há dado. Os ajustes, todos marcados com `{# [back-11-relatorios] ... #}`:

1. "recebidos em setembro" virou "recebidos {{ periodo_txt }}";
2. o selo de variação só aparece se houver o que comparar;
3. sem nada recebido, a barra de formas dá lugar a "Nenhum pagamento recebido";
4. ponto de equilíbrio: "acima" ou "abaixo" do mínimo, em verde ou vermelho; sem custos, pede para cadastrar;
5. a linha de comparação do ticket só aparece se houver mês anterior;
6. retenção: "Sem dado ainda" quando não há histórico;
7. comparação com o mês anterior: "Sem dado ainda" quando não há dois meses;
8. risco: "Ninguém com nota abaixo de 50 agora";
9. "Setembro de 2026" virou o mês ou o período de verdade;
10. a linha "Custos fixos" do fechamento usa o custo do período escolhido;
11. "Sobrou no mês" vira "Faltou", em vermelho, quando falta;
12. "Último fechamento" só aparece se houver (o sistema ainda não guarda);
13. "Lançamentos de setembro" virou "Lançamentos {{ periodo_de }}".

**Para o Adauto:** levar esses ajustes para o front do Drive, senão a próxima cópia os apaga.

## A migration

`b11f7a8b9c00_custos_e_data_de_inativacao.py`, depois da `b10e6f7a8b90`.

- **Sobe:** cria `custos`; acrescenta `alunos.data_inativacao`, vazia para todos.
- **Desce:** apaga a tabela (os custos cadastrados se perdem) e a coluna.
- **Depois do pull, rodar `flask db upgrade`.**

## Como foi testado

- **`pytest`: 257 de 257** (21 novos em `tests/test_relatorios.py`): academia nova não inventa número; formas (débito + crédito = cartão) e ticket igual ao do painel; períodos e variação; custos (criar, editar, remover, 6 inválidos); ponto de equilíbrio acima, abaixo e na proporção do período; lançamentos, filtro e CSV sem dado de outra academia; Excel e PDF avisam; instrutor 403 em 5 rotas; custo de outra academia não aparece nem é alterado; data de inativação (desativar, pagar, botão antigo); gráfico de ativos do painel; retenção só com quem tem histórico; churn e ausentes; nota de risco; mapa de movimento.
- **Migration num Postgres temporário:** 12 checagens. Sobe, o aluno inativo antigo fica sem data, `flask db check` sem diferença, desce, o banco volta a bater com o modelo anterior, sobe de novo.
- **Navegador (Playwright):** relatórios **28 de 28**; frequência 31 de 31, cobrança 33 de 33, alunos 32 de 32, planos 31 de 31, painel 74 de 74, login 60 de 60. Celular de 390 px com toque (claro) e computador de 1440 px (escuro). Fotos abertas e conferidas.
- **Varredura de todas as rotas GET por papel**, comparada com a `front-07-relatorios`: mudaram só as rotas desta branch.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Como está | Evidência |
|---|---|---|
| Isolamento entre academias | `custos` tem `conta_id`; toda consulta passa por `da_conta(...)`. Custo de outra academia não aparece, não é editado nem removido. Lançamentos e planilha só da própria academia. | `test_custo_de_outra_academia_nao_aparece_nem_pode_ser_mexido`, `test_lancamentos_filtro_e_csv` |
| Papéis no servidor | `exigir_papel_em` no blueprint inteiro (vale para rota futura) | `test_instrutor_nao_ve_nada_do_administrativo` |
| CSRF e métodos | Salvar e remover custo são POST, com `csrf_token` | — |
| Dinheiro | `Decimal` e `Numeric(10,2)`; formato brasileiro conferido | `test_custo_invalido_nao_grava` |
| Filtros vindos da URL | `periodo`, `forma` e `situacao` só aceitam os valores conhecidos; o resto é ignorado | `test_periodo_muda_o_que_entra_na_conta`, `test_lancamentos_filtro_e_csv` |
| Planilha | Células protegidas contra fórmula | `exportar_csv` |

## Como revisar

```bash
git fetch origin
git diff origin/front-07-relatorios..origin/back-11-relatorios --stat
git diff origin/front-07-relatorios..origin/back-11-relatorios -- app/ migrations/
```

Ordem sugerida: `models.py` (`Custo`, `data_inativacao` e a função logo depois de `Aluno`), a migration, `relatorio_service.py` (o texto do começo diz de onde vem cada bloco), `relatorios/routes.py`.

## Para decidir (Adauto)

1. **Os pesos da nota de risco** (3 por dia de atraso, 2 por dia sem vir, 10 para novato). São um ponto de partida.
2. **Excel e PDF** do fechamento: ficam para depois do lançamento, como combinado? Pedem bibliotecas novas.

## Riscos

- **Quem der pull sem rodar `flask db upgrade`** vê erro em toda tela que lê alunos.
- **Retenção e churn começam vazios** e vão ganhando sentido com o tempo: só contam alunos desativados a partir desta branch.
- **A tela faz várias consultas** (ela refaz as contas do painel para usar os mesmos números). Com centenas de alunos é rápido; com dezenas de milhares valeria guardar o resultado por alguns minutos.
- **"Último fechamento"** não aparece: o sistema não guarda quando a planilha foi baixada.
- **Metas** (linha tracejada dos gráficos) dependem das Configurações (`back-12`); até lá a linha é a média.
