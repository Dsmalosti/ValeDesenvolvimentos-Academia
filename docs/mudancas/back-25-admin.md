# back-25-admin — painel de administração do Vale Tec

| | |
|---|---|
| **Branch** | `back-25-admin` |
| **Sai de** | `back-24-assinatura` |
| **Data** | 14/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Decisões** | Respostas do Adauto em 14/10/2026: os admins são ele e o Diogo (adauto.netto2005@gmail.com e dsmalosti@gmail.com); o painel mostra, por conta, alunos ativos, último acesso, pagamentos registrados, dias de teste restantes e o relatório de entrada e saída; o admin **vê, bloqueia e entra na conta como se fosse o dono** |
| **Autorização usada** | A1 (Diogo, 10/10/2026): mudar o modelo e criar migration dentro da branch |
| **Tem migration** | **Sim:** `b25d7e8f9a00_painel_de_administracao.py` (nenhum dado existente muda) |
| **Dependência nova** | Não |

## Resumo

Endereço novo **`/admin`**, só para administradores:

1. **Lista de todas as contas**, com cartões no topo (em teste, pagando, vencidas ou bloqueadas, receita por mês) e filtro por situação. Por conta: situação da assinatura e dias de teste, alunos ativos, último acesso (com o selo "parada" se ninguém usa há mais de 7 dias), pagamentos registrados no mês, entradas e saídas do mês e check-ins do mês.
2. **Página de cada conta**, com os mesmos números, a equipe, as mensalidades pagas e o histórico do que os admins fizeram nela. Ações:
   - **Confirmar pagamento** (meses e valor) — libera a conta na hora;
   - **Mudar o fim do teste grátis** — por exemplo, o cliente piloto com 3 meses no total;
   - **Bloquear agora**, com motivo (o cliente vê), e **Retirar o bloqueio**;
   - **Entrar na conta como o dono** — um aviso azul no topo de toda tela lembra que é um admin, com o botão "Voltar ao painel de administração";
   - **Apagar a conta**, só depois dos 30 dias em que os dados ficam guardados, digitando o nome da conta.
3. **Tudo o que um admin faz fica registrado** (quem, em qual conta, o quê, quando), inclusive entrar e sair da conta de um cliente.

## Quem é admin, e por que só pela linha de comando

A coluna nova `instrutores.admin_sistema` só é ligada assim, no servidor:

```bash
flask --app main admin-do-sistema --email adauto.netto2005@gmail.com
flask --app main admin-do-sistema --email dsmalosti@gmail.com
```

A pessoa precisa ter um login no sistema antes (pela tela `/criar-conta`). **Por que não pelo e-mail direto no código:** qualquer pessoa pode criar conta, e o sistema não confere se o e-mail é de quem diz ser. Se o admin fosse "quem tem o e-mail X", um estranho que criasse uma conta com esse e-mail antes de vocês viraria admin. Pela linha de comando, só quem tem acesso ao servidor decide.

## O "relatório de entrada e saída"

Como o Adauto não detalhou, ficou assim (fácil de mudar):

- **Entradas do mês:** a soma dos pagamentos de alunos que a conta registrou no mês.
- **Saídas do mês:** os custos fixos que a conta cadastrou (aluguel, energia...), que já são mensais.
- **Saldo:** entradas menos saídas.

Se a ideia era outra (por exemplo, academias que **entraram e saíram** do Vale Tec no mês), a lista já mostra "contas novas este mês" e as bloqueadas; dá para virar um relatório próprio.

## Regras que valem para o app inteiro

- **O admin nunca é barrado pelo bloqueio**, nem na própria conta, nem dentro da conta de um cliente bloqueado (para poder ajudar). O dono continua bloqueado.
- **Conta que tem admin não pode ser bloqueada nem apagada** pelo painel.
- **Último acesso:** cada pessoa tem a hora do último uso gravada (no máximo uma vez a cada 10 minutos). O tempo em que o admin está dentro da conta de um cliente **não conta** como acesso do cliente.
- **Quem não é admin recebe "página não encontrada" (404)** no `/admin`, como nas outras áreas protegidas: nem fica sabendo que a tela existe.

## Apagar a conta

Só aparece o botão quando a conta está bloqueada há mais de 30 dias (o prazo que a tela de bloqueio promete ao cliente) e não tem admin. Apaga **tudo** o que é da conta, de todas as tabelas, numa transação só: alunos, planos, cobranças, pagamentos, frequência, fichas e treinos, avaliações, sessões, mensagens, custos, convites, equipe, mensalidades e a própria conta. Fica só a linha "apagou" no registro dos admins, com o nome da conta.

**Por que não é automático:** apagar dado de cliente sem uma pessoa conferir é arriscado demais. A data a partir da qual pode apagar aparece na página da conta.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/models.py` | `User.admin_sistema`, `User.ultimo_acesso_em`, `Conta.bloqueio_manual_em`, `Conta.bloqueio_motivo`, modelo novo `AcaoAdmin` (sem chave estrangeira, de propósito) |
| `migrations/versions/b25d7e8f9a00_...py` | **Nova.** As quatro colunas e a tabela `acoes_admin` |
| `app/services/admin_service.py` | **Novo.** Números de cada conta, ações, entrar e voltar, apagar a conta, último acesso |
| `app/blueprints/admin/routes.py` | **Novo.** As rotas do `/admin`, o último acesso e o aviso de "dentro da conta" |
| `app/templates/admin/index.html`, `conta.html` | **Novos, não vieram do Drive.** Montados só com peças do front |
| `app/services/assinatura_service.py` | O bloqueio à mão entra na situação da conta (vale acima do pagamento) |
| `app/blueprints/assinatura/routes.py` | O admin não é barrado |
| `app/templates/assinatura/bloqueada.html` | **Ajuste marcado:** bloqueio feito pelo suporte mostra o motivo e o contato, sem o PIX |
| `app/templates/base.html` | **Ajuste marcado:** o aviso azul "Você está na conta X como administrador" |
| `app/__init__.py`, `app/cli.py` | Registra o blueprint; comando `flask admin-do-sistema --email ... [--remover]` |
| `tests/test_admin.py` | **Novo.** 11 testes |
| `tests/navegador/admin_navegador.py` | **Novo.** Celular e desktop: lista, conta, entrar como o dono, voltar |

## Como foi testado

- `pytest`: bateria inteira, com 11 testes novos: só admin abre (os outros recebem 404, inclusive nas ações); o comando liga e desliga; os números de cada conta (alunos ativos, pagamentos, entradas, saídas, check-ins, dias de teste); filtro por situação; confirmar pagamento (com vírgula no valor) e mudar o teste, registrados no histórico; bloquear à mão (motivo obrigatório) e retirar; admin nunca barrado e conta de admin não bloqueável; entrar como o dono, ver os alunos do cliente, o painel não abre lá dentro, voltar, e o acesso do admin não conta como do dono; admin dentro de conta bloqueada; último acesso; apagar só depois do prazo, só com o nome certo, e nada da conta sobra em tabela nenhuma enquanto a outra academia fica inteira.
- **Apagar a conta num Postgres temporário** (o SQLite dos testes não cobra as chaves estrangeiras): duas contas com um registro em cada tabela, mais uma mensalidade confirmada por um admin de outra conta. Apagou a primeira sem erro, nada dela sobrou, a segunda ficou inteira.
- Migration num Postgres temporário: 16 checagens (ninguém vira admin, nenhuma conta bloqueada, usuário novo nasce sem ser admin, registro aceita conta que não existe mais, `flask db check`, downgrade e upgrade de novo).
- Navegador (celular 390 px claro e desktop 1440 px escuro): `admin_navegador.py` 18 de 18. No celular, o botão "Entrar na conta como o dono" estava na área de ações do cabeçalho, que só aparece no desktop: foi para dentro do conteúdo.

## Como revisar

```bash
git fetch origin
git diff origin/back-24-assinatura..origin/back-25-admin -- app/ migrations/
```

Ordem sugerida: `admin_service.py` (o texto do começo e `apagar_conta`), `admin/routes.py` (quem entra), `assinatura/routes.py` (o admin não é barrado), `models.py` e a migration.

## Para decidir

1. **O relatório de entrada e saída** é o que está descrito acima? Se não, dizer o que deve aparecer.
2. **Os dois comandos** acima precisam ser rodados no servidor depois do deploy (depois de vocês criarem os logins).

## Riscos

- **Entrar como o dono dá ao admin todos os poderes do dono** naquela conta, como pedido. Tudo fica registrado, e o aviso azul não deixa esquecer.
- **Apagar não tem volta.** A proteção é: só depois do prazo, só conta bloqueada, sem admin, e digitando o nome. Vale ter o backup do banco em dia.
- **O texto da Política de Privacidade** precisa dizer que os administradores veem os dados das contas: fica na branch de LGPD, a próxima.
