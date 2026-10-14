# back-23-ranking-frequencia — ranking de presença do mês na tela de Frequência

| | |
|---|---|
| **Branch** | `back-23-ranking-frequencia` |
| **Sai de** | `back-22-ajustes-de-produto` |
| **Data** | 14/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Pedido** | Adauto, 13/10/2026: "Colocar ranking dos alunos que mais compareceram à academia no mês". Onde: na tela de Frequência (resposta de 14/10/2026) |
| **Tem migration** | Não: os dados já existem na tabela `frequencias` |
| **Dependência nova** | Não |

## Resumo

A tela de Frequência ganhou o card **"Ranking do mês"**: os 10 alunos ativos que mais vieram no mês corrente, com a posição, o nome (que leva ao perfil) e quantos dias vieram.

## Regras

- **Conta dias, não entradas.** Quem passou duas vezes no mesmo dia conta um dia. Assim o ranking mede assiduidade, não toques no botão.
- **Só o mês corrente**, do dia 1 até agora. Vira o mês, o ranking recomeça.
- **Só alunos ativos** e **só da própria academia** (o filtro de conta de sempre).
- **Empate divide a posição:** 1º, 2º, 2º, 4º. Para desempatar a ordem na tela: mais entradas no total, depois o nome.
- **Mês sem nenhuma entrada:** o card aparece com "Nenhuma entrada registrada este mês ainda.", sem inventar ranking.
- Quem vê: todo mundo que abre a tela de Frequência (dono, recepção e instrutor).

## Arquivos

| Arquivo | O que mudou |
|---|---|
| `app/services/frequencia_service.py` | Função nova `ranking_do_mes()`, constantes `RANKING_TAMANHO = 10` e `MESES`; o contexto da tela leva o `ranking` |
| `app/templates/frequencia/index.html` | **Card novo marcado** (`{# [back-23-ranking-frequencia] ... #}`), antes da tabela de check-ins. Usa só classes que já existem (`card`, `agora-list`, `chip`, `avatar`) |
| `tests/test_frequencia.py` | 2 testes novos |
| `tests/navegador/frequencia_navegador.py` | 2 checagens novas: o card aparece, lista quem veio, leva ao perfil e não estoura a largura |

## Template para levar ao Drive

`frequencia/index.html`: o card "Ranking do mês". No desktop ocupa a largura toda, entre "Entradas por hora / Na academia agora" e "Check-ins de hoje"; no celular fica depois de "Na academia agora". Sem a variável `ranking`, o card não aparece (o mock do Drive continua igual).

## Como foi testado

- `pytest`: bateria inteira, com 2 testes novos: dias contados (duas entradas no mesmo dia = um dia), empate dividindo a posição, aluno inativo, mês passado e outra academia fora; o card na tela, vazio e com aluno, e a recepção também vendo.
- Navegador (celular 390 px claro e desktop 1440 px escuro): `frequencia_navegador.py` 35 de 35, com as checagens novas. Conferido na captura de tela do desktop.

## Como revisar

```bash
git fetch origin
git diff origin/back-22-ajustes-de-produto..origin/back-23-ranking-frequencia -- app/
```

## Para decidir depois (não trava nada)

- **Tamanho do ranking:** 10 alunos. Muda em `RANKING_TAMANHO`.
- **Mostrar também no painel ou no app do aluno** (quando existir): hoje fica só na Frequência, como o Adauto pediu.

## Riscos

- Nenhum dado muda. A consulta lê as entradas do mês da academia; para uma academia com milhares de entradas no mês continua leve, mas, se um dia pesar, dá para trocar por uma contagem feita no banco.
