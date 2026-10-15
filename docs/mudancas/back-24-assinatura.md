# back-24-assinatura — teste grátis, mensalidade por PIX e bloqueio automático

| | |
|---|---|
| **Branch** | `back-24-assinatura` |
| **Sai de** | `back-23-ranking-frequencia` |
| **Data** | 14/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Decisões** | Respostas do Adauto em 14/10/2026: teste grátis de 2 meses a partir da criação da conta; academia R$ 49,99 e personal R$ 24,99 por mês (**o Diogo precisa confirmar**); pagamento por PIX; bloqueio automático 7 dias depois do vencimento, mostrando o motivo e o código para pagar; dados guardados por 1 mês depois do bloqueio; qualquer pessoa pode criar conta |
| **Autorização usada** | A1 (Diogo, 10/10/2026): mudar o modelo e criar migration dentro da branch |
| **Tem migration** | **Sim:** `b24c6d7e8f90_assinatura_teste_e_mensalidades.py` |
| **Dependência nova** | **Não.** O código PIX é montado sem biblioteca |
| **Configuração nova** | **Sim, opcional:** `VALE_TEC_PIX_CHAVE`, `VALE_TEC_PIX_NOME`, `VALE_TEC_PIX_CIDADE`, `VALE_TEC_SUPORTE_EMAIL`, `VALE_TEC_SUPORTE_WHATSAPP` (ver `.env.example`) |

## Resumo

Antes desta branch qualquer conta usava o Vale Tec para sempre, sem pagar. Agora:

1. **Conta nova tem 2 meses de teste grátis**, contados da criação.
2. **Nos últimos 7 dias** do teste (ou do mês pago), o dono vê um aviso amarelo no topo de toda tela, com o link "Ver como pagar".
3. **Venceu:** aviso vermelho no topo para toda a equipe ("avise o responsável"), e tudo continua funcionando por **7 dias**.
4. **Depois de 7 dias, a conta é bloqueada sozinha.** Qualquer tela leva à tela "Sua conta está bloqueada", sem o menu: diz o motivo, até quando os dados ficam guardados (30 dias), mostra o **"PIX copia e cola"** com o valor certo e o contato do suporte. Só abrem essa tela, o sair, os termos e a política.
5. **A tela `/assinatura`** mostra a situação, o preço, o PIX e os pagamentos confirmados.
6. **Quem confirma o pagamento é uma pessoa**: o painel de administração (próxima branch) ou o comando `flask assinatura-paga`. Pagando, a conta volta na hora, com tudo como estava.

## Como o sistema decide

Nada disso precisa de tarefa agendada no servidor: é calculado a cada acesso (`app/services/assinatura_service.py`).

```
vencimento = o mais tarde entre o fim do teste (contas.teste_ate) e o fim do período pago (contas.pago_ate)

até o vencimento ................ "Teste grátis" ou "Em dia"   (aviso amarelo ao dono nos últimos 7 dias)
até 7 dias depois ............... "Vencida"                    (aviso vermelho para todos; tudo funciona)
depois disso .................... "Bloqueada"                  (só a tela de pagamento)
dados guardados até ............. 30 dias depois do bloqueio
```

**Pagamento:** quem paga antes do bloqueio continua do vencimento antigo (não ganha os dias de atraso). Quem paga depois do bloqueio começa a contar do dia do pagamento.

## Por que PIX com confirmação manual (e não uma empresa de pagamento)

O Adauto pediu "PIX, na conta do MEI ou num gateway, o que for melhor". Para o lançamento, a recomendação é **PIX direto na conta do MEI, com confirmação manual**:

- **Custo zero.** Gateway cobra por PIX recebido (em geral perto de 1% ou um valor fixo por cobrança) e às vezes mensalidade.
- **Sem dependência nova nem integração.** O código "PIX copia e cola" é montado pelo próprio sistema, no padrão do Banco Central (há teste com o exemplo do manual do Banco Central).
- **Volume pequeno no começo.** Conferir meia dúzia de PIX por mês no aplicativo do banco e clicar em "confirmar" é rápido.

**Quando mudar para um gateway:** quando passar de umas 30 contas pagando, ou quando conferir à mão começar a atrasar a liberação. Aí o gateway confirma sozinho, por aviso automático (webhook), e libera a conta na hora. A troca fica isolada em `assinatura_service.codigo_pix()` e `registrar_pagamento()`.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/models.py` | `Conta.teste_ate` (nasce com hoje + 2 meses), `Conta.pago_ate`, constante `MESES_DE_TESTE_GRATIS`, modelo novo `Mensalidade` |
| `migrations/versions/b24c6d7e8f90_...py` | **Nova.** As duas colunas, a tabela `mensalidades` e o fim do teste das contas que já existem (data de criação + 2 meses) |
| `app/services/assinatura_service.py` | **Novo.** As regras: preço, fim do teste, situação, aviso do topo, código PIX, registrar pagamento, mudar o fim do teste |
| `app/helpers/pix.py` | **Novo.** Monta o "PIX copia e cola" (BR Code do Banco Central), sem biblioteca |
| `app/helpers/datas.py` | **Novo.** `somar_meses` (31/01 + 1 mês = 28/02) |
| `app/blueprints/assinatura/routes.py` | **Novo.** A tela `/assinatura`, o bloqueio (antes de cada pedido) e o aviso do topo (`aviso_assinatura`) |
| `app/templates/assinatura/index.html`, `bloqueada.html`, `_pagar.html` | **Novos, não vieram do Drive.** Montados só com peças do front (card, chip, note, tile, botões) |
| `app/templates/base.html` | **Ajuste marcado:** o aviso do topo, antes do conteúdo de cada tela |
| `app/__init__.py` | Registra o blueprint |
| `app/cli.py` | Comandos novos: `flask assinaturas`, `flask assinatura-paga --conta N [--meses M] [--valor V]`, `flask assinatura-teste --conta N --ate AAAA-MM-DD` |
| `config.py`, `.env.example` | Chave PIX, nome e cidade do PIX, e-mail e WhatsApp do suporte (todas opcionais) |
| `tests/test_assinatura.py` | **Novo.** 13 testes |
| `tests/navegador/assinatura_navegador.py` | **Novo.** Celular e desktop: aviso, tela de pagamento, copiar o código, conta bloqueada, sair |

## O que o Adauto precisa configurar

- **`VALE_TEC_PIX_CHAVE`**: a chave PIX da conta do MEI que vai receber (o CNPJ só com números, se for essa a chave). Sem ela, a tela diz "O código PIX ainda não está disponível aqui. Fale com o suporte".
- **`VALE_TEC_SUPORTE_WHATSAPP`**: o número de WhatsApp da Vale, com 55 na frente, quando estiver decidido. Sem ele, a tela mostra só o e-mail.
- **Cliente piloto (3 meses grátis no total):** `flask assinatura-teste --conta N --ate AAAA-MM-DD`, ou pelo painel de administração.

## Templates para levar ao Drive

- `base.html`: o aviso do topo (marcado `[back-24-assinatura]`; sem a variável, nada muda).
- Três templates novos em `assinatura/` (não existem no Drive).

## Como foi testado

- `pytest`: bateria inteira, com 13 testes novos: `somar_meses`; o código PIX confere com o exemplo do Banco Central (CRC `1D3D`) e tem valor, nome e cidade no formato certo; conta nova com 2 meses; aviso só ao dono nos últimos dias; vencida avisa e funciona; bloqueada só abre a tela de pagamento (e envio de formulário é recusado sem gravar nada); outra conta não é afetada; PIX na tela só com a chave configurada, só para o dono, e com o preço do personal; pagar em dia e depois do bloqueio; isolamento; sem login; os três comandos.
- Migration num Postgres temporário: 16 checagens (contas existentes ganham o fim do teste, conta sem data de criação, tabela com chave estrangeira, `flask db check`, downgrade e upgrade de novo).
- Navegador (celular 390 px claro e desktop 1440 px escuro): `assinatura_navegador.py` 30 de 30, mais login, painel e personal. Capturas conferidas.

## Como revisar

```bash
git fetch origin
git diff origin/back-23-ranking-frequencia..origin/back-24-assinatura -- app/ migrations/ config.py
```

Ordem sugerida: `assinatura_service.py` (o texto do começo explica as regras), `assinatura/routes.py` (o bloqueio), `models.py` e a migration, `helpers/pix.py`.

## Para decidir

1. **Diogo: o preço** (R$ 49,99 academia e R$ 24,99 personal). Fica em `PRECOS`, no topo de `assinatura_service.py`.
2. **A chave PIX e o WhatsApp do suporte** (configuração acima).
3. **Apagar os dados depois de 30 dias de bloqueio:** a tela já diz a data. Apagar de fato fica no painel de administração, como ação de um admin (nada é apagado sozinho).

## Riscos

- **Contas que já existem** (nos bancos de desenvolvimento) ganham o teste a partir da data de criação. Uma conta criada há mais de 2 meses e 7 dias fica **bloqueada** assim que a migration rodar. Para liberar: `flask assinatura-teste --conta N --ate AAAA-MM-DD`. Em produção não há conta antiga.
- **O bloqueio vale para todo mundo da conta**, inclusive a recepção. É o comportamento pedido.
- **Data de criação em UTC:** `contas.criado_em` é gravado em UTC; perto da meia-noite o teste pode começar no dia seguinte. A diferença é de no máximo um dia.
