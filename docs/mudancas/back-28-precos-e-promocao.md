# back-28-precos-e-promocao — preço final do Vale Tec, com "preço de lançamento, 50% de desconto"

| | |
|---|---|
| **Branch** | `back-28-precos-e-promocao` |
| **Sai de** | `main` (8a334eb, depois do PR #51 do Diogo) |
| **Data** | 17/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Decisão** | Adauto e Diogo, 17/10/2026: "o preço final para academia e personal é 59,99 academia e 29,99 personal, eles já estão com 50% de desconto e pode deixar pra sempre assim, não vai ser por quem criar primeiro, queremos que o pessoal ache que o preço está baixo agora" |
| **Tem migration** | Não |
| **Dependência nova** | Não |

> **Histórico desta branch:** a primeira versão (17/10/2026, mais cedo) dava 50% só às 10 primeiras contas, com uma coluna nova no banco, uma migration e botões no /admin. Na mesma data a decisão mudou para a regra abaixo, e tudo aquilo saiu **antes do PR**: a branch não mexe no banco nem no /admin.

## O que mudou

1. **Preço cobrado** (`PRECOS`, em `app/services/assinatura_service.py`), igual para todas as contas:
   - academia **R$ 59,99** por mês (antes 49,99, provisório);
   - personal **R$ 29,99** por mês (antes 24,99).
2. **Como o preço aparece:** "**Preço de lançamento: 50% de desconto**", com o preço de tabela riscado: academia ~~R$ 119,98~~ e personal ~~R$ 59,98~~ (`PRECOS_DE_TABELA`).
   - **Criar conta:** aviso verde com os dois preços e os de tabela riscados.
   - **Assinatura:** o preço com o de tabela riscado e o aviso "Você paga R$ 59,99 por mês em vez de R$ 119,98".
   - **Pagar por PIX:** "(preço de lançamento, 50% de desconto)". O código PIX cobra R$ 59,99 / R$ 29,99.
   - **Aviso do topo** (teste acabando, mensalidade vencendo): "Preço de lançamento, com 50% de desconto."
3. **Desligar o desconto:** `DESCONTO_DE_LANCAMENTO = 0` no `assinatura_service.py`. As telas param de mostrar o preço riscado e o aviso; o preço cobrado continua o de `PRECOS`.

## Como era antes

- Preço provisório (49,99 / 24,99), sem nenhum aviso de desconto.
- A tela de criar conta não falava de preço.

## Arquivos

| Arquivo | Mudança |
|---|---|
| `app/services/assinatura_service.py` | `PRECOS` novos, `PRECOS_DE_TABELA`, `DESCONTO_DE_LANCAMENTO`, `preco_de_tabela()`; `situacao()` devolve também `preco_de_tabela` e `desconto`; os avisos do topo lembram o desconto |
| `app/blueprints/auth/routes.py` | A tela de criar conta recebe `promo` (preços em texto, com espaço que não quebra entre "R$" e o número) |
| `app/templates/auth/criar_conta.html` | Aviso do preço de lançamento (**levar para o Drive**) |
| `app/templates/assinatura/index.html`, `assinatura/_pagar.html` | Preço de tabela riscado e aviso (templates que nasceram no repositório) |
| `tests/test_precos.py` | **Novo** (7 testes) |
| `tests/test_assinatura.py`, `tests/navegador/assinatura_navegador.py` | Preços novos; a tela de criar conta e a assinatura com o desconto |

## Como foi testado

- `pytest` inteiro: **525 passaram**. `tests/test_precos.py` confere:
  - o preço cobrado e o de tabela, e que o desconto anunciado bate com a conta (59,99 é 50% de 119,98);
  - que **12 contas criadas em sequência** pagam o mesmo preço (não existe mais "as primeiras");
  - as telas de criar conta, assinatura e personal;
  - o código PIX com R$ 59,99;
  - o aviso do topo;
  - que, com `DESCONTO_DE_LANCAMENTO = 0`, nenhuma tela mostra o preço riscado.
- Navegador `assinatura_navegador.py`: **42/42** (celular 390 px e desktop 1440 px escuro). Inclui criar uma conta pela tela e ver R$ 59,99 com ~~R$ 119,98~~. `admin_navegador.py`: 18/18.

## Como revisar

```bash
git fetch origin
git diff origin/main..origin/back-28-precos-e-promocao --stat
git diff origin/main..origin/back-28-precos-e-promocao -- app/services/assinatura_service.py
```

## Riscos

- **Preço "de" que nunca é cobrado.** Anunciar "de R$ 119,98 por R$ 59,99" quando ninguém paga R$ 119,98 pode ser visto como **desconto fictício**, uma forma de publicidade enganosa pelo Código de Defesa do Consumidor (art. 37). O Procon multa essa prática no varejo, e academia pequena pode ser tratada como consumidora. O texto dos termos (`back-32`) diz que o preço de tabela existe e que o desconto não tem data para acabar. **Está na lista de pontos para o advogado.** Se ele preferir, basta `DESCONTO_DE_LANCAMENTO = 0` e anunciar só "preço de lançamento".
- **Acabar com o desconto um dia** é aumento de preço: os termos pedem aviso com 30 dias.
