# back-28-precos-e-promocao — preços confirmados e promoção de lançamento

| | |
|---|---|
| **Branch** | `back-28-precos-e-promocao` |
| **Sai de** | `main` (8a334eb, depois do PR #51 do Diogo) |
| **Data** | 17/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Decisão** | Adauto e Diogo, 17/10/2026: "R$ 59,99 academia e R$ 29,99 personal — confirmado, e coloque que está em promoção 50% de preço dos dois para os primeiros 10 clientes" |
| **Tem migration** | Sim: `b28f9a0b1c20` (uma coluna nova em `contas`). Autorização A1 do Diogo |
| **Dependência nova** | Não |

## O que mudou

1. **Preço da mensalidade**: academia **R$ 59,99** (era 49,99) e personal **R$ 29,99** (era 24,99). Fica em `PRECOS`, em `app/services/assinatura_service.py`.
2. **Promoção de lançamento**: as **10 primeiras contas criadas** ganham **50% de desconto**: academia R$ 29,99 e personal R$ 14,99.
   - A conta ganha a promoção no momento em que é criada, pela tela `/criar-conta` ou pelo `flask criar-conta`.
   - O desconto vale enquanto a conta existir (ver "Decisões que ficaram" abaixo).
   - Arredondamento para **baixo** no centavo: 59,99 ÷ 2 = 29,995, e o cliente paga **29,99**, nunca mais que a metade.
3. **Onde a promoção aparece:**
   - Tela de **criar conta**: aviso verde com os preços com desconto e quantas vagas restam. Some quando as vagas acabam.
   - Tela de **assinatura**: preço com desconto, preço cheio riscado e o aviso "Promoção de lançamento: 50% de desconto".
   - **PIX copia e cola**: já sai com o valor da promoção.
   - **Aviso do topo** (teste acabando ou mensalidade vencendo): lembra o desconto.
   - **Painel de admin**: selo "Promoção 50%" na lista e na conta, e "X de 10 vagas usadas" no topo da lista.
4. **Controle do admin** (`/admin/contas/<id>`): botões **"Dar a promoção"** e **"Tirar a promoção"**.
   - Servem para corrigir à mão uma conta de teste ou repetida que pegou uma vaga.
   - Dar só funciona se ainda houver vaga.
   - Fica registrado em `acoes_admin`.
5. **`flask admin-do-sistema --email ...`**: se a conta da pessoa tinha pegado uma vaga, a vaga é devolvida. A conta de um admin não paga.

## Por quê

O preço provisório (49,99 / 24,99) foi trocado pelo confirmado. A promoção é para atrair os primeiros clientes. Ela fica gravada em cada conta, e não calculada pela ordem de criação, por dois motivos:
- o desconto não muda se uma conta mais antiga for apagada;
- o admin pode corrigir conta por conta.

## Como era antes

- Toda conta pagava o mesmo preço por modelo, sem desconto.
- A tela de criar conta não falava de preço.

## Arquivos

| Arquivo | Mudança |
|---|---|
| `app/models.py` | `Conta.desconto_promocional` (inteiro, %, padrão 0) |
| `migrations/versions/b28f9a0b1c20_promocao_de_lancamento.py` | Cria a coluna. As contas que já existem ficam com 0 |
| `app/services/assinatura_service.py` | `PRECOS` novos, `VAGAS_DA_PROMOCAO = 10`, `DESCONTO_DA_PROMOCAO = 50`, `preco_cheio()`, `preco()` com desconto, `vagas_da_promocao()`, `entrar_na_promocao()`; `situacao()` devolve também `preco_cheio` e `desconto` |
| `app/services/acesso_service.py`, `app/cli.py` | A conta nova entra na promoção se houver vaga; `admin-do-sistema` devolve a vaga |
| `app/services/admin_service.py`, `app/blueprints/admin/routes.py` | `mudar_promocao()` e a rota `POST /admin/contas/<id>/promocao` |
| `app/blueprints/auth/routes.py` | A tela de criar conta recebe `promo` (vagas e preços) |
| Templates | `auth/criar_conta.html`, `assinatura/index.html`, `assinatura/_pagar.html`, `admin/index.html`, `admin/conta.html` (marcados com `[back-28-precos-e-promocao]`) |

**Para o Drive (Adauto):** o aviso verde da promoção em `auth/criar_conta.html` é o único ajuste num template que veio do Drive. Os outros são templates que nasceram no repositório.

**Para encerrar a promoção:** `VAGAS_DA_PROMOCAO = 0` no `assinatura_service.py`. Quem já ganhou continua com o desconto; o admin tira conta por conta, se precisar.

## Como foi testado

- `pytest` inteiro: **532 passaram**. Arquivo novo `tests/test_promocao.py`, com 14 testes:
  - preços e arredondamento;
  - a 1ª conta ganha a promoção e a 11ª não;
  - conta apagada devolve a vaga;
  - `flask criar-conta`;
  - as telas, o PIX com o valor da promoção e o aviso do topo;
  - o personal;
  - o admin dá e tira, não dá sem vaga, e quem não é admin recebe 404;
  - virar admin devolve a vaga.
- Testes antigos de assinatura atualizados para os preços novos.
- Navegador (`tests/navegador/assinatura_navegador.py`): **42/42**, no celular (390 px, toque, claro) e no desktop (1440 px, escuro). Confere a tela de criar conta com a promoção, a criação da conta pela tela e a assinatura com R$ 29,99 e o preço cheio riscado. Sem rolagem lateral e com o console limpo. `admin_navegador.py`: 18/18.
- Migration num Postgres descartável (`qa/testa_migration_b28.py`): **12/12**. Testa o upgrade, as contas antigas com 0, o padrão 0 em conta inserida sem a coluna, o `flask db check`, o downgrade e o upgrade de novo.
- Varredura de todas as rotas GET por papel (dono, recepção, instrutor): igual à `main`, 0 problemas.

## Como revisar

```bash
git fetch origin
git diff origin/main..origin/back-28-precos-e-promocao --stat
git diff origin/main..origin/back-28-precos-e-promocao -- app/services/assinatura_service.py app/models.py migrations/
```

## Riscos

- **Vagas queimadas por contas falsas**: o cadastro é aberto. Quem criar 10 contas de mentira tira a promoção dos clientes de verdade. O cadastro tem limite por IP (`back-18`) e o admin tira a promoção das contas falsas; a vaga volta para a próxima conta criada.
- **Contas que já existiam antes da migration ficam sem promoção.** Em produção o banco nasce vazio, então não muda nada. Na demonstração e no banco local, as contas antigas pagam o preço cheio até o admin dar a promoção.

## Decisões que ficaram (estão na lista do Adauto)

- **Até quando vale o desconto?** Fiz "enquanto a conta continuar ativa", que é o mais simples de anunciar. Se for por um tempo (ex.: 12 meses), muda uma linha e o texto dos termos.
- **O cliente piloto conta como uma das 10 vagas?** Do jeito que está, conta, se criar a conta antes de as vagas acabarem.
