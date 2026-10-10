# Roadmap de lançamento — Vale Tec

Fonte de verdade do progresso: o que falta para o **primeiro cliente** usar o sistema, na ordem em que será feito.
O `CLAUDE.md` diz *como* trabalhar; este arquivo diz *o que* fazer e *onde paramos*.

| | |
|---|---|
| **Atualizado em** | 10/10/2026 |
| **Estado** | Fase B em andamento: as telas de **alunos** (`front-03` + `back-07`) e de **planos** (`front-04` + `back-08`) estão prontas, cada uma com uma migration pequena. A próxima é a **cobrança** (`front-05-cobranca` + `back-09-cobranca`): o Diogo pediu para ver o esquema das tabelas antes. Faltam decisões de conta externa (hospedagem, domínio, e-mail). |
| **Base** | `main` em `9b61934` |
| **Referências** | `Tarefas do backend — Diogo.md` (os números 1.1, 3.2 etc. deste roadmap vêm de lá), `Integracao-Front-Back.md`, `Esquema-Backend.md`, `Acesso-e-Mensagens.md`, `Front-Personal.md` |

## Como ler

- Cada linha das tabelas é **uma branch e um PR** para o Diogo, na ordem. Cada branch sai da anterior.
- `front-NN-<tela>` traz só templates e estáticos, copiados fiéis do `vale-tec-front`. Sozinha ela não muda nada para quem usa.
- `back-NN-<assunto>` mexe no backend e é o que faz a tela funcionar. Toda `back-*` leva `docs/mudancas/<branch>.md`.
- **A1, A2…** são as autorizações que a regra 4 do `CLAUDE.md` exige (dependência nova, migration, mudança de modelo, apagar arquivo do Diogo, configuração de produção). Todas as listadas aqui já foram dadas; um **⏸** marca o que ainda precisaria de pergunta.
- **D1, D2…** são decisões de negócio do Adauto (as já respondidas estão em "Decisões já tomadas"); **T1, T2…** são decisões técnicas com o Diogo. Uma branch com decisão em aberto não começa.
- Uma branch só é marcada `[x]` com testes passando, smoke de rotas igual ou melhor que a `main`, doc escrito e push feito.

## Onde estamos

| | Branch | O que entrega | PR | Estado |
|---|---|---|---|---|
| [x] | `front-01` | Tela de login nova, correção de popups do iPhone, `CLAUDE.md` e skills | [#8](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/8) → `main` | Aguardando revisão do Diogo |
| [x] | `back-01-auth-login` | Login e logout de verdade (tarefas 1.1 a 1.5) | [#9](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/9) → `front-01` | Aguardando revisão do Diogo |
| [x] | `back-02-limpeza` | Defeitos que quebravam telas, `print()` com dados, `.gitignore`, primeiros testes automáticos | [#10](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/10) → `back-01-auth-login` | Aguardando revisão do Diogo |
| [x] | `back-03-isolamento` | Uma academia não enxerga a outra; login obrigatório em tudo; nenhum GET apaga dados | [#11](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/11) → `back-02-limpeza` | Aguardando revisão do Diogo |
| [x] | `docs-01-decisoes-e-termos` | Decisões do Adauto no roadmap, rascunhos dos termos de uso e da política de privacidade, teste de navegador do login (Playwright) | [#12](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/12) → `back-03-isolamento` | Aguardando revisão do Diogo |
| [x] | `front-02-painel` | Layout das telas logadas e painel do front novo (só templates); o `base.html` antigo virou `base_antigo.html` | [#13](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/13) → `docs-01-decisoes-e-termos` | Aguardando revisão do Diogo |
| [x] | `back-04-painel` | O painel novo funcionando com os dados do banco; pontes para as telas antigas; páginas de erro novas | [#14](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/14) → `front-02-painel` | Aguardando revisão do Diogo |
| [x] | `back-05-repo-e-config` | `.pyc` e `database.db` fora do git; `requirements.txt` limpo e `requirements-dev.txt`; `DATABASE_URL` como nome único; `SECRET_KEY` sem valor padrão | [#15](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/15) → `back-04-painel` | Aguardando revisão do Diogo |
| [x] | `back-06-contas-e-papeis` | Tabela `contas`; `conta_id` em alunos, planos, pagamentos e exercícios; papéis com bloqueio no servidor; e-mail e CPF únicos por academia; cadastro aberto fechado; `flask criar-conta`. **Tem migration.** | [#16](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/16) → `back-05-repo-e-config` | Aguardando revisão do Diogo |
| [x] | `front-03-alunos` | Templates das telas de alunos do front novo (lista, perfil, cadastro, edição, busca), cópia fiel do Drive | PR a abrir → `back-06-contas-e-papeis` | Enviada; falta abrir o PR |
| [x] | `back-07-alunos` | As telas de alunos funcionando com o banco: lista com filtros, cadastro e edição validados no servidor, perfil, busca ao vivo, exportar, desativar. **Tem migration** (4 colunas em `alunos`). | PR a abrir → `front-03-alunos` | Enviada; falta abrir o PR |
| [x] | `front-04-planos` | Templates das telas de planos do front novo (lista e formulário), cópia fiel do Drive | PR a abrir → `back-07-alunos` | Enviada; falta abrir o PR |
| [x] | `back-08-planos` | As telas de planos funcionando com o banco: cartões com alunos e faturamento de cada plano, criar e editar com valor em `1.234,56`, pausar e reativar. **Tem migration** (1 coluna em `planos`). | PR a abrir → `front-04-planos` | Enviada; falta abrir o PR |

O backend de hoje cobre cerca de 25 das 81 rotas que o front usa. Já existem, no formato antigo: alunos, planos, exercícios, fichas e um CRUD de pagamentos com situação de inadimplência. Não existem: cobrança no formato do front, frequência, relatórios, configurações, avaliações, mensagens, convite e a variante Personal.

## Fase A — Fundação

Nenhuma tela logada do front novo entra antes disto. São as tarefas das etapas 1 a 4 da lista do Diogo.

| | Branch | O que entrega | Tarefas | Pronto quando | Trava |
|---|---|---|---|---|---|
| [x] | `back-02-limpeza` | Redirect para rota inexistente nos exercícios, `/excuir/` nas fichas, `print()` com dados de formulário, contagem de ativos do painel, `.gitignore`. Pasta `tests/`. | 2.1, 2.2, 2.4, parte da 2.5 | Feito. | — |
| [x] | `back-03-isolamento` | Uma academia não enxerga nada da outra: as consultas passam por um filtro de conta único; login obrigatório em todas as rotas; nenhuma rota GET apaga ou altera dados. Sem migration. | 3.1 (parte), 3.3, 3.4 | Feito, com 15 testes "conta A × conta B". Ficou para a `back-06` o que pede migration: exercício com dono e unicidade de e-mail e CPF por academia. | — |
| [x] | `front-02-painel` | O layout das telas logadas (`base.html` novo, cabeçalho, menu, rodapé, páginas de erro) e os templates do painel, copiados fiéis do Drive. O `base.html` antigo foi renomeado para `base_antigo.html` e as 19 telas antigas passaram a herdar dele. | — | Feito. Sozinha não muda nada para quem usa. | — |
| [x] | `back-04-painel` | Depois do login abre o **painel novo**, com os números calculados do banco (alunos, planos e pagamentos) e só da conta logada. `usuario` e `academia` em todo template. As seções sem backend respondem "em construção"; alunos, planos, exercícios e fichas levam às telas antigas por pontes temporárias. Páginas de erro 403/404/500 do front. | 5.1 (parte), 4.2, parte da 3.7 | Feito, com os limites anotados em `docs/mudancas/back-04-painel.md`: `academia` e o papel do usuário são provisórios até a `back-06`. | — |
| [x] | `back-05-repo-e-config` | Tira do git os 102 `.pyc` e o `instance/database.db`. Tira o `mysql-connector` antigo do `requirements.txt` e cria o `requirements-dev.txt` com o `pytest`. `DATABASE_URL` vira o nome único da variável do banco (o nome antigo ainda é aceito, com aviso). `SECRET_KEY` sem valor padrão. | 2.5, 1.7, 2.3, 3.8 | Feito. `pip install` conferido num ambiente novo; o app recusa subir sem banco ou sem chave. | — |
| [x] | `back-06-contas-e-papeis` | Separa **conta** (a academia) de **usuário** (dono, recepção, instrutor). Coluna `papel` e bloqueio no servidor do que cada papel não pode. E-mail e CPF de aluno únicos por academia. Exercício com dono (os antigos viram catálogo padrão). `conta_id` obrigatório. Cadastro aberto fechado; conta nova por `flask criar-conta`. | 3.2, 3.5, 3.6 | Feito. Migration testada em Postgres (25 checagens, incluindo `flask db check`). O painel do instrutor fica para a branch do painel dele. | — |

## Fase B — Telas, na ordem de uso do cliente

Cada tela são duas branches: a `front-NN` (templates) e a `back-NN` que sai dela (rotas, regras e banco). As rotas antigas do Diogo são renomeadas para os nomes do front (tarefa 4.1) na branch da tela correspondente. Todas dependem da autorização A1 (migrations), menos o painel.

| | Branches | O que o cliente passa a fazer | Tarefas | Pronto quando | Trava |
|---|---|---|---|---|---|
| [x] | `front-03-alunos` + `back-07-alunos` | Cadastrar, buscar, editar e inativar aluno; ver a página do aluno; exportar a lista. Datas em `dd/mm/aaaa` (hoje todo cadastro falharia na validação). | 4.1, 4.3, 4.4 | Feito. Limites em `docs/mudancas/back-07-alunos.md`: reativar aluno ainda é pela tela antiga; o botão "Bloquear" só avisa; depois do cadastro vai para o perfil, e não para o recebimento. | A1 (dada); T3; foto do aluno fica para depois do lançamento |
| [x] | `front-04-planos` + `back-08-planos` | Criar, editar, pausar e reativar planos. Valor digitado como `R$ 1.234,56`. | 4.1, 4.3, 5.4 | Feito. Limites em `docs/mudancas/back-08-planos.md`: a variante Personal (pacotes) fica para a `back-17`; o faturamento do cartão conta para o plano em que o aluno está hoje. | A1 (dada) |
| [ ] | `front-05-cobranca` + `back-09-cobranca` | Receber a mensalidade: matrícula, renovação (recalcula vencimento e valor), confirmação em PIX, débito, crédito ou dinheiro, diária avulsa, histórico de pagamentos do aluno. No lançamento o PIX é **manual** (a recepção confere e confirma). | 5.2 | Matricular → cobrar → confirmar nas 4 formas → valor certo no painel. Cada pagamento guarda quem confirmou e como. | A1 (dada); reconciliar com a tabela `pagamentos` que o Diogo já criou; D3 |
| [ ] | `front-06-frequencia` + `back-10-frequencia` | Registrar a entrada do aluno em um toque; ver quem sumiu há mais de 15 dias; exportar. | 5.3 | Aluno sem nenhuma entrada aparece como "sem dado", não como "0 acessos". Ligar e desligar o check-in persiste. | A1 (dada) |
| [ ] | `front-07-relatorios` + `back-11-relatorios` | Fechamento do mês: recebido por forma de pagamento, inadimplência, custos e ponto de equilíbrio, exportação em CSV. Só dono e recepção. | 5.8 | Os totais batem com os cards do painel e com a soma dos pagamentos de teste. | A1 (dada) |
| [ ] | `front-08-config` + `back-12-config` | Dados da academia, horário, metas, modelos de mensagem, recebimento e funcionalidades ligadas. | 5.9 | Cada aba salva e o valor aparece nas outras telas (nome da academia no cabeçalho, meta no painel). | A1 (dada) |
| [ ] | `front-09-equipe` + `back-13-equipe` | O dono convida a recepção e os instrutores; a pessoa cria a senha pelo link; "esqueci a senha". | 5.10 | Convite vencido ou já usado dá 404; o convidado entra já na conta certa e com o papel certo. | A1 e A6 (dadas); D6 |

### Os outros módulos: todos entram no lançamento

Pelas decisões D1 e D8, os quatro entram: fichas, avaliação física e mensagens porque o Adauto quer no primeiro cliente, e a variante Personal porque o lançamento inclui personal trainers. Vêm depois das telas acima, nesta ordem.

| | Branches | O que é | Tarefas | Observação |
|---|---|---|---|---|
| [ ] | `front-10-treinos` + `back-14-treinos` | Exercícios e fichas de treino dentro da página do aluno. | 5.5 | O backend antigo já tem as tabelas; muda o fluxo. Sem esta branch, o instrutor perde as telas antigas de ficha quando o layout novo assumir. |
| [ ] | `front-11-avaliacoes` + `back-15-avaliacoes` | Avaliação física: agendar, registrar, comparar. | 5.6 | A1 (dada). IMC e RCQ calculados no servidor; é medição, não diagnóstico. |
| [ ] | `front-12-mensagens` + `back-16-mensagens` | Mensagens do dia pelo WhatsApp (link `wa.me`, custo zero). | 5.7 | A1 (dada). No lançamento o sistema **não envia sozinho**: ele monta o texto e abre o WhatsApp do aparelho, e a pessoa toca em enviar. Envio automático pede a API oficial do WhatsApp, que é paga por conversa e precisa de aprovação da Meta; fica para depois do lançamento. |
| [ ] | `front-13-personal` + `back-17-personal` | Variante Personal Trainer: agenda de sessões e pacotes. | 5.11 | A1 (dada). Obrigatória: o lançamento inclui personal trainers (D1). Falta decidir se renovar o pacote soma o saldo que sobrou (D12). |

## Fase C — Revisão de segurança

Com a skill `saas-flask-seguranca`, seção por seção, cada item marcado com evidência (arquivo e linha, ou teste). Falha P0 bloqueia o lançamento.

| | Branch | O que entrega | Tarefas | Trava |
|---|---|---|---|---|
| [ ] | `back-18-seguranca` | Limite de tentativas no login e nas rotas de senha e convite. Cabeçalhos de segurança, HTTPS forçado e CSP. Prazo de validade da sessão. Mesma mensagem para "conta desativada" e "senha errada" (hoje o login revela que a conta existe). Remoção do popup de perfil do login, já que o papel passa a vir do banco. Botão "Entrar com digital" escondido. | 1.6, 3.7 | A6 (dada) |
| [ ] | `back-19-lgpd` | Opt-in de WhatsApp por aluno, exportar e excluir os dados de um aluno (só o dono), logs sem CPF e telefone, páginas públicas de termos e política ligadas na criação de conta, guardando a versão aceita. | 3.9 | A1 (dada). Os textos estão em `docs/legal/` como rascunho; só são publicados depois da revisão do Adauto. |
| [ ] | (sem branch) Checklist final | Rodar a checklist completa da skill, o teste "conta A × conta B" em todas as rotas, `pip-audit`, e conferir que `.env` nunca entrou no histórico. Relatório com severidade e correção de cada achado. | — | — |

## Fase D — Deploy de produção

| | Item | O que é | Trava |
|---|---|---|---|
| [ ] | `back-20-producao` | Postgres no lugar do SQLite: todas as migrations rodadas do zero num Postgres de teste; configuração de produção conferida (`DEBUG` desligado, cookies seguros, segredos só em variável de ambiente). | 3.10; A4 (dada); D4 |
| [ ] | Ambiente | Contratar hospedagem e banco, apontar o domínio, HTTPS, variáveis de ambiente, backup automático do banco e teste de restauração. | D4, D5 |
| [ ] | Ensaio geral | Roteiro manual completo em produção com uma conta de teste: criar conta → cadastrar aluno → matricular → cobrar → registrar entrada → fechar o mês. No iPhone e no Android de verdade. | — |
| [ ] | Entrada dos clientes | Os clientes se cadastram sozinhos pela tela "Criar conta" (D9) e cadastram os alunos do zero (D10). Do nosso lado: publicar os termos, mandar o link e combinar o canal de suporte. | Termos revisados; `back-13` |

## O que está parado esperando o Adauto

Nenhuma autorização está pendente: o Diogo respondeu todas em 10/10/2026 (tabela abaixo). O que ainda falta decidir são contas externas e dois dados do Adauto, na segunda tabela.

### Autorizações (regra 4 do `CLAUDE.md`): todas dadas

O Diogo respondeu **sim** a todas em 10/10/2026, e o Adauto repassou. Ficam registradas aqui para a próxima sessão não perguntar de novo.

| # | Autorização | Situação |
|---|---|---|
| A1 | Criar migrations e mudar o `models.py` dentro das branches, para revisão no PR. Nenhuma roda em banco de verdade. | **Sim.** Vale para todas as branches daqui em diante. |
| A2 | Tirar do git os `.pyc` e o `instance/database.db`. | **Sim.** Feito na `back-05`. |
| A3 | Tirar o `mysql-connector==2.2.9` do `requirements.txt` e criar o `requirements-dev.txt` com o `pytest`. | **Sim.** Feito na `back-05`. |
| A4 | Um nome só para a variável do banco (`DATABASE_URL`) e `SECRET_KEY` sem valor padrão. | **Sim.** Feito na `back-05`. |
| A5 | Renomear o `base.html` antigo para `base_antigo.html`. | **Sim.** Feito na `front-02-painel`. |
| A6 | Dependências Flask-Limiter e Flask-Talisman. | **Sim.** Entram na `back-18-seguranca` (e o limite de tentativas, antes, na `back-13-equipe`). |
| A7 | Alinhar o banco local do Adauto. | Dada pelo Adauto e feita em 10/10/2026. |
| A8 | Instalar o Playwright no ambiente local. | Dada pelo Adauto e feita em 10/10/2026. |

A regra 4 continua valendo para o que **não** está nesta lista: outra dependência nova, apagar arquivo do Diogo, mexer em segredo ou em configuração de produção além do que a A4 descreve.

### Decisões do Adauto que ainda faltam

Decisões de negócio ou de conta externa. As quatro primeiras o Adauto quer decidir junto com o Diogo.

| # | Decisão | O que trava | Sugestão | Até quando |
|---|---|---|---|---|
| D4 | **Hospedagem e banco de produção:** onde o backend e o Postgres vão rodar e quanto dá para gastar por mês. Como o sistema será gratuito nos 2 primeiros meses, esse custo sai do bolso. | `back-20-producao`, o ambiente e o texto da política de privacidade | Levantar 2 ou 3 opções com preço antes de decidir | Antes da Fase D |
| D5 | **Domínio** do sistema (ex.: `app.valetec.com.br`). | Cookies seguros, link do convite, e-mails, e mais tarde o login com digital | Registrar já: demora a propagar e é barato | Antes da Fase D |
| D6 | **Provedor de e-mail** para convite, confirmação de cadastro e "esqueci a senha". Ficou mais urgente: com os clientes se cadastrando sozinhos (D9), sem e-mail ninguém recupera a senha. | `back-13-equipe` | Escolher junto com o domínio | Antes de `back-13` |
| D12 | **Personal:** renovar um pacote de sessões soma o saldo que sobrou do pacote anterior, ou o saldo antigo se perde? | `back-17-personal` | Perguntar aos personais que vão testar | Antes de `back-17` |
| D13 | **Dados de quem oferece o Vale Tec** para os termos: nome ou razão social, CNPJ, cidade, e-mail de contato e canal de suporte. | Publicar os termos | Lista completa em `docs/legal/LEIA-ME.md` | Antes do lançamento |

### Decisões já tomadas pelo Adauto (10/10/2026)

| # | Resposta | O que isso muda no plano |
|---|---|---|
| D1 | O lançamento é para **uma academia** (o dono e um instrutor) e para **alguns personal trainers** conhecidos. | A variante Personal (`back-17`) e os papéis (dono × instrutor, na `back-06`) são obrigatórios para o lançamento. Não dá para deixar nenhum dos dois para depois. |
| D2 | **Gratuito por cerca de 2 meses**, para teste. Depois começa a cobrar; o valor ainda será definido. | Não precisa de cobrança do Vale Tec dentro do sistema no lançamento. Os termos dizem que o preço será avisado com 30 dias de antecedência (prazo sugerido pelo Claude). |
| D7 | O Claude escreve os termos de uso e a política de privacidade; o Adauto revisa e completa. | Rascunhos em `docs/legal/`. Nada é publicado antes da revisão. |
| D8 | Fichas de treino, avaliação física e mensagens do dia **entram**. | As branches `11` a `13` são obrigatórias. Mensagens: no lançamento o sistema monta o texto e abre o WhatsApp; não envia sozinho. |
| D9 | Os clientes **se cadastram sozinhos**. | A tela "Criar conta" (`back-13`) é obrigatória para o lançamento, com limite de tentativas (A6) e e-mail funcionando (D6). Responde a T4: o cadastro fica aberto, mas pela tela nova. |
| D10 | Cada cliente **cadastra os alunos do zero**. | Não há importação de planilha no plano. |
| D11 | Suporte **nos fins de semana e depois das 20h** em dias úteis. Quer **backup** das contas para o caso de perda. | Backup automático do banco na Fase D. Os termos prometem backup diário guardado por 30 dias: a frequência e o prazo são sugestão do Claude, a confirmar. |
| D3 | PIX no lançamento com **confirmação manual** pela recepção (resposta do Diogo, item 17). | A `back-09-cobranca` não integra com nenhum PSP. PIX automático fica para depois do lançamento. |

### Decisões técnicas: respondidas pelo Diogo (10/10/2026)

| # | Resposta | O que isso muda no plano |
|---|---|---|
| T1 | **Tabela `contas` separada**, com `conta_id` em `instrutores`. | A `back-06` cria a tabela e leva `conta_id` também para alunos, planos, pagamentos e exercícios, que é o que faz a equipe de uma academia ver os mesmos dados. |
| T2 | Revisão dos PRs **um por um, na ordem**. Não indicou dia fixo. | A fila anda no ritmo dele. Hoje há 9 branches esperando. |
| T3 | Aluno continua com **`ativo` sim/não**. | Não há status "pausado" ou "cancelado", nem relatório de motivo de cancelamento. As telas do front que mostram esses estados usam só ativo e inativo. |
| T4 | **Fechar já** o `/instrutores/cadastro/` aberto. | A `back-06` fecha a rota. Até a tela nova "Criar conta" existir (`back-13`), conta nova só por comando no servidor. O Adauto quer auto-cadastro no lançamento (D9): as duas coisas combinam, o que muda é a ordem. |
| T5 | Cobrança: **tabelas novas** `cobrancas` e `pagamentos` do Esquema-Backend, migrando os dados da tabela atual. **Mostrar o esquema no PR antes.** | A `back-09-cobranca` abre primeiro só com o esquema proposto (modelo e migration), para o Diogo aprovar antes de o resto ser escrito. |
| T6 | O Diogo usa **Postgres local**. **Não existe banco de produção** nem dado real. | Toda migration é testada em Postgres, além do SQLite. Não há dado antigo para preservar, o que simplifica as migrations. |

## Depois do primeiro cliente

Nada aqui trava o lançamento: login com digital (depende do domínio), PIX automático com webhook, upload de fotos, PDF e Excel, WhatsApp pela API oficial, melhorias de ficha e tema por usuário.

## Achados em aberto

Coisas vistas durante o trabalho que ainda não têm dono. Cada uma já está encaixada numa branch acima.

| Achado | Onde | Vai em |
|---|---|---|
| `/instrutores/painel/` dá erro 500 para quem está logado: o formulário chama `alunos.excluirAlunos`, uma exclusão em massa que nunca foi criada | `main` | Continua: a tela antiga ainda existe em `/instrutores/painel/`. Some quando as telas antigas saírem |
| O painel antigo mostra `237` fixo em "Pagamentos pendentes" e "Planos a vencer" | `notificacao.html` | Resolvido na `back-04-painel`: a tela inicial antiga não é mais mostrada |
| O login diz "Usuário desativado" antes de conferir a senha, o que revela que a conta existe | `auth_service.py` | `back-18` |
| O logout antigo (`/instrutores/sair/`) é por GET: qualquer site consegue deslogar o usuário | `main` | Continua enquanto houver tela antiga, que é quem mostra esse link. O sair do layout novo já é por POST |
| O popup de perfil do login fechou com Esc, antes do primeiro toque, no navegador embutido do Claude. No Chromium do Playwright isso **não** se repete (4 cenários). Fica como observação; o backend já aceita o perfil vazio | front | Some com a remoção do popup (`back-18`) |
| Erro "Transition was skipped" no console ao sair da tela de login para uma tela do layout antigo | front (transição entre páginas) | Esperado enquanto houver tela antiga: ao ir de uma tela nova para uma antiga, o navegador cancela a animação e avisa no console. Some quando todas forem novas |
| **As migrations antigas não rodam do zero num Postgres vazio**: `flask db upgrade` num banco novo falha numa migration anterior, ao mudar o tipo de `treino.repeticoes`. Sem resolver isso não há como criar o banco de produção | `migrations/versions/` | `back-20-producao`. Vale avisar o Diogo desde já |
| O instrutor ainda não tem painel: vê "em construção" em vez dos números da academia. O template `painel/instrutor.html` do front não foi ligado | `painel/routes.py` | Junto com a `back-13-equipe`, que é quando instrutor passa a existir |
| Os exercícios que já existiam viraram catálogo padrão e ninguém consegue editá-los pela tela. A tela antiga ainda mostra os botões (o clique dá 404) | `exercicios/` | `back-14-treinos`: a tela nova distingue catálogo de exercício próprio |
| Ainda não há tela para trocar o nome da academia: fica o que a migration gravou ("Academia de *Nome*") | `contas.nome` | `back-12-config` |
| Na migration da `back-06`, dois usuários antigos que eram da mesma academia viram duas contas | bancos locais | Juntar com um `UPDATE` no `conta_id`, se for o caso |
| O front tem botões de **demonstração**, que só mostram um aviso e não fazem nada: "WhatsApp aberto para…", "Mensagens de parabéns enviadas", "Lembretes de renovação enviados" | `painel/index.html`, `_notificacao.html` | Cada um vira ação de verdade na branch do módulo (mensagens, cobrança) |
| O card "Avaliações de hoje" do painel tem número e nomes fixos de exemplo no template. Está escondido | `painel/index.html` | Volta com dado de verdade na branch de avaliações |
| O gráfico "Alunos ativos por mês" é uma aproximação: o banco não guarda quando um aluno foi inativado, então quem saiu não aparece nos meses passados | `painel_service.py` | Precisa de uma coluna com a data da inativação. Não entrou na `back-07-alunos` para não misturar assuntos; vai na `back-11`, de relatórios, que é quem mais depende desse histórico |
| O template do painel no repositório tem 6 ajustes que o do Drive não tem (lista em `docs/mudancas/back-04-painel.md`). O Adauto precisa levar para o Drive, senão a próxima cópia desfaz | `painel/index.html` | Adauto |
| `/fichas/editar/<id>` dá erro 500: o template `treino_form.html` usa um campo que o formulário de ficha não tem. Já era assim antes; apareceu agora porque a varredura de rotas passou a rodar com dados | tela antiga de fichas | `back-14-treinos`, que troca a tela. Se o Diogo quiser corrigir antes, é pequeno |
| No front novo não há botão para **reativar** um aluno desativado. Hoje só pela tela antiga (`/alunos/listar/`) | `alunos/detalhe.html` | Decisão do Adauto: se quiser o botão, entra no front e numa branch pequena de backend |
| O campo "Observações" do aluno sugere "restrição médica": é dado de saúde, sensível pela LGPD | `alunos/_campos.html` | `back-19-lgpd` e a política de privacidade |
| O servidor não limita o tamanho do que é enviado num formulário (`MAX_CONTENT_LENGTH`). O cadastro de aluno no celular tem campo de foto, que o servidor ignora | `config.py` | `back-18-seguranca` |
| O cartão de plano mostra "1 alunos": o template não tem singular | `planos/lista.html` (front) | Ajuste do Adauto no front (Drive); depois é só copiar de novo |
| O faturamento por plano (painel e tela de planos) conta o pagamento para o plano em que o aluno está **hoje**. Se ele trocou de plano no mês, o valor aparece no plano novo | `painel_service.py` | `back-09-cobranca`: o pagamento passa a guardar o plano |
| Nas telas novas, nome de plano não pode repetir na academia. Regra nossa, que o front de exemplo não tinha | `plano_tela_service.py` | Decisão do Adauto: manter ou tirar |

## Registro de atualizações

| Data | O que mudou |
|---|---|
| 10/10/2026 | Criado na Etapa 0. `front-01` (PR #8) e `back-01-auth-login` enviadas. |
| 10/10/2026 | OK do Adauto para seguir com o que não depende de decisão. `back-02-limpeza` enviada. A limpeza que depende de autorização virou a `back-05-repo-e-config`, e as branches seguintes foram renumeradas. Entrou a seção "O que está parado esperando o Adauto". |
| 10/10/2026 | `back-03-isolamento` enviada. Entraram os achados sobre exercício sem dono e registros antigos sem dono. |
| 10/10/2026 | PRs abertos: #9 (`back-01`), #10 (`back-02`) e #11 (`back-03`). |
| 10/10/2026 | O Adauto respondeu D1, D2, D7, D8, D9, D10 e D11 e autorizou A7 e A8. Consequências: Personal, fichas, avaliação, mensagens e a tela "Criar conta" são obrigatórios para o lançamento. Banco local alinhado e Playwright instalado. Entraram os rascunhos em `docs/legal/` e as decisões D12 e D13. |
| 10/10/2026 | PR #12 aberto (`docs-01`). |
| 10/10/2026 | O Adauto pediu o front novo numa branch para testar no código real. Entraram `front-02-painel` e `back-04-painel` (layout e painel juntos), na frente das branches que esperam autorização. As branches futuras foram renumeradas de novo: repo-e-config virou `back-05`, contas-e-papeis `back-06`, alunos `front-03` + `back-07`, e assim por diante. |
| 10/10/2026 | Respostas do Diogo: sim para todas as autorizações (A1 a A6); tabela `contas` separada; aluno continua com `ativo`; fechar o cadastro aberto; cobrança com tabelas novas e esquema mostrado antes; revisão um por um; Postgres local e nenhum dado de produção; PIX manual. Hospedagem, domínio e e-mail seguem em aberto. `back-05-repo-e-config` enviada. |
| 10/10/2026 | `back-06-contas-e-papeis` enviada: tabela `contas`, papéis, exercício com dono, cadastro aberto fechado. Achado novo: as migrations antigas não rodam do zero no Postgres. |
| 10/10/2026 | PRs abertos: #13 (`front-02`), #14 (`back-04`), #15 (`back-05`) e #16 (`back-06`). O banco local do Adauto recebeu a migration da `back-06`. |
| 10/10/2026 | `front-03-alunos` e `back-07-alunos` enviadas: as telas de alunos do front novo funcionando com o banco. Primeira tela da Fase B. Achados novos: `/fichas/editar/<id>` com erro 500 (antigo), falta botão de reativar aluno, observações como dado sensível, limite de tamanho de envio. |
| 10/10/2026 | `front-04-planos` e `back-08-planos` enviadas: as telas de planos do front novo funcionando com o banco, com a coluna `avaliacoes_incluidas`. Faltam abrir os PRs de `front-03`, `back-07`, `front-04` e `back-08`. |
