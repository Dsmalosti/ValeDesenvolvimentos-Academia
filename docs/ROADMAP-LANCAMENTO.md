# Roadmap de lançamento — Vale Tec

Fonte de verdade do progresso: o que falta para o **primeiro cliente** usar o sistema, na ordem em que será feito.
O `CLAUDE.md` diz *como* trabalhar; este arquivo diz *o que* fazer e *onde paramos*.

| | |
|---|---|
| **Atualizado em** | 10/10/2026 |
| **Estado** | Fase A em andamento. Feito tudo o que não depende de autorização (até a `back-03`); **parado na `back-04`, esperando as respostas da seção [O que está parado esperando o Adauto](#o-que-está-parado-esperando-o-adauto).** |
| **Base** | `main` em `9b61934` |
| **Referências** | `Tarefas do backend — Diogo.md` (os números 1.1, 3.2 etc. deste roadmap vêm de lá), `Integracao-Front-Back.md`, `Esquema-Backend.md`, `Acesso-e-Mensagens.md`, `Front-Personal.md` |

## Como ler

- Cada linha das tabelas é **uma branch e um PR** para o Diogo, na ordem. Cada branch sai da anterior.
- `front-NN-<tela>` traz só templates e estáticos, copiados fiéis do `vale-tec-front`. Sozinha ela não muda nada para quem usa.
- `back-NN-<assunto>` mexe no backend e é o que faz a tela funcionar. Toda `back-*` leva `docs/mudancas/<branch>.md`.
- **⏸** marca o que a regra 4 do `CLAUDE.md` manda perguntar ao Adauto antes: dependência nova, migration, mudança de modelo, apagar arquivo do Diogo, configuração de produção. Cada ⏸ aponta para uma autorização **A1, A2…**
- **D1, D2…** são decisões de negócio do Adauto; **T1, T2…** são decisões técnicas com o Diogo. Uma branch com decisão em aberto não começa.
- Uma branch só é marcada `[x]` com testes passando, smoke de rotas igual ou melhor que a `main`, doc escrito e push feito.

## Onde estamos

| | Branch | O que entrega | PR | Estado |
|---|---|---|---|---|
| [x] | `front-01` | Tela de login nova, correção de popups do iPhone, `CLAUDE.md` e skills | [#8](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/8) → `main` | Aguardando revisão do Diogo |
| [x] | `back-01-auth-login` | Login e logout de verdade (tarefas 1.1 a 1.5) | [#9](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/9) → `front-01` | Aguardando revisão do Diogo |
| [x] | `back-02-limpeza` | Defeitos que quebravam telas, `print()` com dados, `.gitignore`, primeiros testes automáticos | [#10](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/10) → `back-01-auth-login` | Aguardando revisão do Diogo |
| [x] | `back-03-isolamento` | Uma academia não enxerga a outra; login obrigatório em tudo; nenhum GET apaga dados | [#11](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/11) → `back-02-limpeza` | Aguardando revisão do Diogo |

O backend de hoje cobre cerca de 25 das 81 rotas que o front usa. Já existem, no formato antigo: alunos, planos, exercícios, fichas e um CRUD de pagamentos com situação de inadimplência. Não existem: cobrança no formato do front, frequência, relatórios, configurações, avaliações, mensagens, convite e a variante Personal.

## Fase A — Fundação

Nenhuma tela logada do front novo entra antes disto. São as tarefas das etapas 1 a 4 da lista do Diogo.

| | Branch | O que entrega | Tarefas | Pronto quando | Trava |
|---|---|---|---|---|---|
| [x] | `back-02-limpeza` | Redirect para rota inexistente nos exercícios, `/excuir/` nas fichas, `print()` com dados de formulário, contagem de ativos do painel, `.gitignore`. Pasta `tests/`. | 2.1, 2.2, 2.4, parte da 2.5 | Feito. | — |
| [x] | `back-03-isolamento` | Uma academia não enxerga nada da outra: as consultas passam por um filtro de conta único; login obrigatório em todas as rotas; nenhuma rota GET apaga ou altera dados. Sem migration. | 3.1 (parte), 3.3, 3.4 | Feito, com 15 testes "conta A × conta B". Ficou para a `back-05` o que pede migration: exercício com dono e unicidade de e-mail e CPF por academia. | — |
| [ ] | `back-04-repo-e-config` | Tira do git os 100 `.pyc` e o `instance/database.db`. Limpa o `requirements.txt` (o `mysql-connector` não instala em Python novo) e cria o `requirements-dev.txt` com o `pytest`. Um nome só para a variável do banco. `SECRET_KEY` sem valor padrão. | 2.5, 1.7, 2.3, 3.8 | `git ls-files` sem `.pyc`; `pip install -r requirements.txt` roda limpo num ambiente novo; o app não sobe se faltar segredo. | ⏸ A2, A3, A4 |
| [ ] | `back-05-contas-e-papeis` | Separa **conta** (a academia) de **usuário** (dono, recepção, instrutor). Coluna `papel` e bloqueio no servidor das telas de dono. E-mail e CPF de aluno únicos por academia. Exercício com dono. `instrutor_id` obrigatório. | 3.2, 3.5, 3.6 | Dois usuários da mesma conta veem os mesmos alunos; o instrutor recebe 403 em relatórios e configurações. | ⏸ A1; T1; D1 |
| [ ] | `front-02-layout` | O layout das telas logadas: `base.html` novo, cabeçalho, menu, rodapé e páginas de erro. O `base.html` antigo é renomeado (não apagado) para as telas antigas continuarem abrindo até serem trocadas. | — | Os arquivos batem com os do Drive; as telas antigas continuam iguais. | ⏸ A5 |
| [ ] | `back-06-layout` | O que todo template novo precisa: `usuario` e `academia` em toda página, páginas de erro 403/404/500, avisos nas categorias do front, e os endereços do menu respondendo "em construção" para o layout não quebrar. | 4.2, 4.4, parte da 3.7 | Uma página de teste com o layout novo abre sem erro no celular e no PC, claro e escuro. | depende da `back-05` |

## Fase B — Telas, na ordem de uso do cliente

Cada tela são duas branches: a `front-NN` (templates) e a `back-NN` que sai dela (rotas, regras e banco). As rotas antigas do Diogo são renomeadas para os nomes do front (tarefa 4.1) na branch da tela correspondente. Todas dependem da autorização A1 (migrations), menos o painel.

| | Branches | O que o cliente passa a fazer | Tarefas | Pronto quando | Trava |
|---|---|---|---|---|---|
| [ ] | `front-03-painel` + `back-07-painel` | Abrir o sistema e ver o resumo do dia: alunos ativos e inativos, novas matrículas, vencimentos, notificações. O instrutor vê o painel sem os números de dinheiro. Os cards de faturamento e de ausentes mostram "sem dado" até a cobrança e a frequência existirem. | 5.1, 4.1 | Os números batem com o banco de teste; métrica sem dado aparece como "sem dado", nunca como zero. | — |
| [ ] | `front-04-alunos` + `back-08-alunos` | Cadastrar, buscar, editar e inativar aluno; ver a página do aluno; exportar a lista. Datas em `dd/mm/aaaa` (hoje todo cadastro falharia na validação). | 4.1, 4.3, 4.4 | Fluxo completo de cadastro → edição → inativação no celular; busca sem recarregar a página. | ⏸ A1; T3; foto do aluno fica para depois do lançamento |
| [ ] | `front-05-planos` + `back-09-planos` | Criar, editar, pausar e reativar planos. Valor digitado como `R$ 1.234,56`. | 4.1, 4.3, 5.4 | Plano pausado some do cadastro de aluno e continua nos alunos que já o têm. | ⏸ A1 |
| [ ] | `front-06-cobranca` + `back-10-cobranca` | Receber a mensalidade: matrícula, renovação (recalcula vencimento e valor), confirmação em PIX, débito, crédito ou dinheiro, diária avulsa, histórico de pagamentos do aluno. No lançamento o PIX é **manual** (a recepção confere e confirma). | 5.2 | Matricular → cobrar → confirmar nas 4 formas → valor certo no painel. Cada pagamento guarda quem confirmou e como. | ⏸ A1; reconciliar com a tabela `pagamentos` que o Diogo já criou; D3 |
| [ ] | `front-07-frequencia` + `back-11-frequencia` | Registrar a entrada do aluno em um toque; ver quem sumiu há mais de 15 dias; exportar. | 5.3 | Aluno sem nenhuma entrada aparece como "sem dado", não como "0 acessos". Ligar e desligar o check-in persiste. | ⏸ A1 |
| [ ] | `front-08-relatorios` + `back-12-relatorios` | Fechamento do mês: recebido por forma de pagamento, inadimplência, custos e ponto de equilíbrio, exportação em CSV. Só dono e recepção. | 5.8 | Os totais batem com os cards do painel e com a soma dos pagamentos de teste. | ⏸ A1 |
| [ ] | `front-09-config` + `back-13-config` | Dados da academia, horário, metas, modelos de mensagem, recebimento e funcionalidades ligadas. | 5.9 | Cada aba salva e o valor aparece nas outras telas (nome da academia no cabeçalho, meta no painel). | ⏸ A1 |
| [ ] | `front-10-equipe` + `back-14-equipe` | O dono convida a recepção e os instrutores; a pessoa cria a senha pelo link; "esqueci a senha". | 5.10 | Convite vencido ou já usado dá 404; o convidado entra já na conta certa e com o papel certo. | ⏸ A1; D6, D9 |

### Módulos que o front já tem e não estão na ordem acima

Entram no primeiro cliente só se a decisão D8 disser que sim. Se ficarem de fora, o item do menu mostra "em construção" ou é escondido.

| | Branches | O que é | Tarefas | Observação |
|---|---|---|---|---|
| [ ] | `front-11-treinos` + `back-15-treinos` | Exercícios e fichas de treino dentro da página do aluno. | 5.5 | O backend antigo já tem as tabelas; muda o fluxo. Sem esta branch, o instrutor perde as telas antigas de ficha quando o layout novo assumir. |
| [ ] | `front-12-avaliacoes` + `back-16-avaliacoes` | Avaliação física: agendar, registrar, comparar. | 5.6 | ⏸ A1. IMC e RCQ calculados no servidor; é medição, não diagnóstico. |
| [ ] | `front-13-mensagens` + `back-17-mensagens` | Mensagens do dia pelo WhatsApp (link `wa.me`, custo zero). | 5.7 | ⏸ A1. |
| [ ] | `front-14-personal` + `back-18-personal` | Variante Personal Trainer: agenda de sessões e pacotes. | 5.11 | ⏸ A1. Só se o primeiro cliente for personal (D1). |

## Fase C — Revisão de segurança

Com a skill `saas-flask-seguranca`, seção por seção, cada item marcado com evidência (arquivo e linha, ou teste). Falha P0 bloqueia o lançamento.

| | Branch | O que entrega | Tarefas | Trava |
|---|---|---|---|---|
| [ ] | `back-19-seguranca` | Limite de tentativas no login e nas rotas de senha e convite. Cabeçalhos de segurança, HTTPS forçado e CSP. Prazo de validade da sessão. Mesma mensagem para "conta desativada" e "senha errada" (hoje o login revela que a conta existe). Remoção do popup de perfil do login, já que o papel passa a vir do banco. Botão "Entrar com digital" escondido. | 1.6, 3.7 | ⏸ A6 |
| [ ] | `back-20-lgpd` | Opt-in de WhatsApp por aluno, exportar e excluir os dados de um aluno (só o dono), logs sem CPF e telefone, links de termos e política na criação de conta. | 3.9 | ⏸ A1; D7 |
| [ ] | (sem branch) Checklist final | Rodar a checklist completa da skill, o teste "conta A × conta B" em todas as rotas, `pip-audit`, e conferir que `.env` nunca entrou no histórico. Relatório com severidade e correção de cada achado. | — | — |

## Fase D — Deploy de produção

| | Item | O que é | Trava |
|---|---|---|---|
| [ ] | `back-21-producao` | Postgres no lugar do SQLite: todas as migrations rodadas do zero num Postgres de teste; configuração de produção conferida (`DEBUG` desligado, cookies seguros, segredos só em variável de ambiente). | 3.10; ⏸ A4; D4 |
| [ ] | Ambiente | Contratar hospedagem e banco, apontar o domínio, HTTPS, variáveis de ambiente, backup automático do banco e teste de restauração. | D4, D5 |
| [ ] | Ensaio geral | Roteiro manual completo em produção com uma conta de teste: criar conta → cadastrar aluno → matricular → cobrar → registrar entrada → fechar o mês. No iPhone e no Android de verdade. | — |
| [ ] | Entrada do cliente | Criar a conta do primeiro cliente, importar os alunos dele se houver planilha, treinar quem vai usar. | D9, D10 |

## O que está parado esperando o Adauto

Três listas. A primeira é a que destrava mais trabalho: sem **A1**, quase nada depois da `back-03` pode ser feito.

### Autorizações (regra 4 do `CLAUDE.md`)

São "pode ou não pode". O Claude não faz nenhuma sem um sim explícito.

| # | Autorização pedida | O que muda e qual o risco | Destrava |
|---|---|---|---|
| A1 | **Criar migrations e mudar modelos do banco dentro das branches.** | Cada branch que precisar traz o arquivo de migration e a mudança no `models.py`, para o Diogo revisar no PR. Nenhuma migration é rodada em banco de verdade: só em SQLite e Postgres de teste. Risco: migration mal feita perde dado quando for aplicada; por isso cada uma leva teste de ida e volta e o Diogo aprova antes. | `back-05` e quase toda a Fase B |
| A2 | **Tirar do git os 100 `.pyc` e o `instance/database.db`.** | Os arquivos continuam no disco de cada um; só deixam de ser versionados. O `database.db` pode ter e-mail e senha criptografada de quem testou, e continua no histórico do GitHub mesmo depois. Risco: quem dependia do `database.db` versionado para rodar localmente precisa criar o próprio banco. | `back-04` |
| A3 | **Mexer no `requirements.txt`:** tirar o `mysql-connector==2.2.9` (não instala em Python 3.12 ou mais novo) e criar um `requirements-dev.txt` com o `pytest`. | Se a produção for Postgres, o `mysql-connector-python` também pode sair. Risco: se alguém ainda usa MySQL localmente, o projeto dele para de conectar. | `back-04` |
| A4 | **Mexer na configuração de produção:** um nome só para a variável do banco (`DATABASE_URL`) e `SECRET_KEY` sem valor padrão. | Hoje o código lê `DATABASE_URI` e o `ProductionConfig` lê `DATABASE_URL`. Risco: cada um precisa renomear a variável no próprio `.env`, senão o app não sobe. | `back-04`, `back-21` |
| A5 | **Renomear o `base.html` do Diogo** para `base_antigo.html` e ajustar a linha `extends` das telas antigas. | Nada é apagado. As telas antigas continuam abrindo até cada uma ser trocada. Risco: baixo; o smoke de rotas pega se alguma quebrar. | `front-02` |
| A6 | **Duas dependências novas:** Flask-Limiter (limite de tentativas de senha) e Flask-Talisman (cabeçalhos de segurança e HTTPS). | São pequenas e padrão de mercado. Risco: o Flask-Limiter precisa de um lugar para guardar a contagem; em produção com mais de um processo isso pede Redis ou o próprio banco. | `back-19` |
| A7 | **Alinhar o banco local do Adauto** (Postgres `academia_db`). | Ele está marcado numa versão de migration que só existe numa branch antiga (`c4a1e9d27b35`), e por isso não tem a tabela `pagamentos`: as três telas de pagamentos dão erro 500 na máquina dele. O conserto é remarcar a versão e rodar a migration de pagamentos. Não apaga dados. | Só o ambiente local |
| A8 | **Instalar o Playwright** no ambiente local (não entra no `requirements.txt`). Baixa um Chromium de uns 150 MB. | A skill `saas-qa-release` pede teste com toque de verdade no celular. Sem ele, os testes de navegador são feitos no navegador embutido do Claude, que não simula toque. | Qualidade dos testes de tela |

### Decisões do Adauto

Decisões de negócio ou de conta externa. Nenhuma é técnica: só você pode responder.

| # | Decisão | O que trava | Sugestão | Até quando |
|---|---|---|---|---|
| D1 | **Quem é o primeiro cliente:** academia ou personal trainer? Quantas pessoas vão usar (só o dono, ou recepção e instrutores também)? | A ordem inteira da Fase B e se a equipe (`back-14`) é obrigatória | Academia, com a variante Personal depois | Antes de `back-05` |
| D2 | **Preço do Vale Tec** para a academia (mensalidade, teste grátis, cobrança por aluno ou fixa) e como você vai cobrar o cliente. | Não trava código do lançamento; trava a conversa de venda e o contrato | Preço fixo mensal no piloto, cobrado por fora do sistema | Antes da entrada do cliente |
| D3 | **PIX:** lançar com confirmação manual (a recepção confere o comprovante) ou só com PIX automático? Se automático, qual PSP (Asaas, Mercado Pago ou Efí) e ele aceita pessoa física sem CNPJ? | `back-10-cobranca` | Lançar com PIX manual; PIX automático depois do piloto | Antes de `back-10` |
| D4 | **Hospedagem e banco de produção:** onde o backend e o Postgres vão rodar e quanto você aceita pagar por mês. A Vercel de hoje só serve o mock do front. | `back-21-producao` e o ambiente | Levantar 2 ou 3 opções com preço antes de decidir | Antes da Fase D |
| D5 | **Domínio** do sistema (ex.: `app.valetec.com.br`). | Cookies seguros, link do convite, e-mails, e mais tarde o login com digital | Registrar já: demora a propagar e é barato | Antes da Fase D |
| D6 | **Provedor de e-mail** para convite e "esqueci a senha". | `back-14-equipe` | Escolher junto com o domínio | Antes de `back-14` |
| D7 | **Termos de uso e política de privacidade (LGPD):** quem escreve, e o contrato com a academia dizendo que ela é a dona dos dados dos alunos e o Vale Tec só os processa. | `back-20-lgpd` e a entrada do cliente | Texto revisado por advogado antes do primeiro cliente pagante | Antes da Fase C |
| D8 | **Quais módulos extras entram no primeiro cliente:** fichas de treino, avaliação física, mensagens do dia. | Tamanho da Fase B | Fichas entram (o instrutor usa todo dia e o backend antigo já tem); avaliação e mensagens depois | Antes de `front-11` |
| D9 | **Como o primeiro cliente recebe o acesso:** você cria a conta dele à mão, ou ele se cadastra sozinho pela tela "Criar conta"? | Se `back-14-equipe` precisa estar pronta no lançamento | Conta criada por você no piloto; auto-cadastro depois | Antes de `back-14` |
| D10 | **Dados que o cliente já tem:** importar a planilha de alunos dele ou ele cadastra do zero? | A entrada do cliente | Importar por você, uma vez, com conferência | Antes da entrada do cliente |
| D11 | **Suporte e backup:** quem atende o cliente e em que horário; quanto tempo de dado ele pode perder num desastre. | A rotina de backup do ambiente | Backup diário, guardado por 30 dias | Antes da Fase D |

### Decisões técnicas (Adauto com o Diogo)

| # | Decisão | O que trava | Sugestão |
|---|---|---|---|
| T1 | Tabela `contas` separada, ou `conta_id` apontando para o dono? | `back-05` e tudo depois | Tabela `contas`: é onde ficam os dados da academia |
| T2 | O Diogo revisa branch por branch, na ordem, ou em lotes? PR empilhado só anda se o anterior for aprovado. Hoje há 4 PRs na fila. | O ritmo de todo o roadmap | Combinar um dia fixo de revisão |
| T3 | Aluno: `ativo` sim/não, ou `status` (ativo, pausado, cancelado)? | `back-08` e o relatório de cancelamento | `status`, se o motivo de cancelamento for entrar nos relatórios |
| T4 | Qualquer pessoa pode abrir `/instrutores/cadastro/` e criar uma conta de academia nova. Fica aberto até o lançamento ou fecha já? | `back-05` | Fechar quando a D9 for respondida |

## Depois do primeiro cliente

Nada aqui trava o lançamento: login com digital (depende do domínio), PIX automático com webhook, upload de fotos, PDF e Excel, WhatsApp pela API oficial, melhorias de ficha e tema por usuário.

## Achados em aberto

Coisas vistas durante o trabalho que ainda não têm dono. Cada uma já está encaixada numa branch acima.

| Achado | Onde | Vai em |
|---|---|---|
| `/instrutores/painel/` dá erro 500 para quem está logado: o formulário chama `alunos.excluirAlunos`, uma exclusão em massa que nunca foi criada | `main` | Some com o painel novo (`back-07`) |
| O painel antigo mostra `237` fixo em "Pagamentos pendentes" e "Planos a vencer" | `notificacao.html` | Some com o painel novo (`back-07`) |
| O login diz "Usuário desativado" antes de conferir a senha, o que revela que a conta existe | `auth_service.py` | `back-19` |
| O logout antigo (`/instrutores/sair/`) é por GET: qualquer site consegue deslogar o usuário | `main` | Some com o cabeçalho antigo (`back-06`) |
| O popup de perfil do login fecha com Esc ou "voltar" antes do primeiro toque, deixando o formulário sem perfil | front | Some com a remoção do popup (`back-19`) |
| Erro "Transition was skipped" no console ao sair da tela de login para uma tela do layout antigo | front (transição entre páginas) | Conferir de novo depois de `back-06` |
| A checagem de e-mail repetido ao editar aluno olha todas as academias e, pela mensagem, revela que o e-mail existe em outra | `aluno_service.py` | `back-05` (tarefa 3.5) |
| O exercício não tem dono: é um catálogo único que qualquer academia logada edita e apaga | `models.py` | `back-05` |
| Aluno ou plano antigo sem dono (`instrutor_id` vazio) fica invisível, e as fichas dele também. Conferir no banco de produção antes do deploy | banco | `back-05` e Fase D |

## Registro de atualizações

| Data | O que mudou |
|---|---|
| 10/10/2026 | Criado na Etapa 0. `front-01` (PR #8) e `back-01-auth-login` enviadas. |
| 10/10/2026 | OK do Adauto para seguir com o que não depende de decisão. `back-02-limpeza` enviada. A limpeza que depende de autorização virou a `back-04-repo-e-config`, e as branches seguintes foram renumeradas. Entrou a seção "O que está parado esperando o Adauto". |
| 10/10/2026 | `back-03-isolamento` enviada. Entraram os achados sobre exercício sem dono e registros antigos sem dono. |
| 10/10/2026 | PRs abertos: #9 (`back-01`), #10 (`back-02`) e #11 (`back-03`). |
