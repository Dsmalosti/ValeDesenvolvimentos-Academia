# Roadmap de lançamento — Vale Tec

Fonte de verdade do progresso: o que falta para o **primeiro cliente** usar o sistema, na ordem em que será feito.
O `CLAUDE.md` diz *como* trabalhar; este arquivo diz *o que* fazer e *onde paramos*.

| | |
|---|---|
| **Atualizado em** | 10/10/2026 |
| **Estado** | Etapa 0 concluída. **Aguardando o OK do Adauto neste roadmap** para começar a Fase A. |
| **Base** | `main` em `9b61934` |
| **Referências** | `Tarefas do backend — Diogo.md` (os números 1.1, 3.2 etc. deste roadmap vêm de lá), `Integracao-Front-Back.md`, `Esquema-Backend.md`, `Acesso-e-Mensagens.md`, `Front-Personal.md` |

## Como ler

- Cada linha das tabelas é **uma branch e um PR** para o Diogo, na ordem. Cada branch sai da anterior.
- `front-NN-<tela>` traz só templates e estáticos, copiados fiéis do `vale-tec-front`. Sozinha ela não muda nada para quem usa.
- `back-NN-<assunto>` mexe no backend e é o que faz a tela funcionar. Toda `back-*` leva `docs/mudancas/<branch>.md`.
- **⏸ Pergunta antes** marca o que a regra 4 do `CLAUDE.md` manda perguntar ao Adauto: dependência nova, migration, mudança de modelo, apagar arquivo do Diogo, configuração de produção.
- **D1, D2…** apontam para a seção [Decisões do Adauto](#decisões-do-adauto). Uma branch com decisão em aberto não começa.
- Uma branch só é marcada `[x]` com testes passando, smoke de rotas igual ou melhor que a `main`, doc escrito e push feito.

## Onde estamos

| | Branch | O que entrega | PR | Estado |
|---|---|---|---|---|
| [x] | `front-01` | Tela de login nova, correção de popups do iPhone, `CLAUDE.md` e skills | [#8](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/8) → `main` | Aguardando revisão do Diogo |
| [x] | `back-01-auth-login` | Login e logout de verdade (tarefas 1.1 a 1.5) | a abrir → `front-01` | Push feito; falta abrir o PR |

O backend de hoje cobre cerca de 25 das 81 rotas que o front usa. Já existem, no formato antigo: alunos, planos, exercícios, fichas e um CRUD de pagamentos com situação de inadimplência. Não existem: cobrança no formato do front, frequência, relatórios, configurações, avaliações, mensagens, convite e a variante Personal.

## Fase A — Fundação

Nenhuma tela logada do front novo entra antes disto. São as tarefas das etapas 1 a 4 da lista do Diogo.

| | Branch | O que entrega | Tarefas | Pronto quando | Trava |
|---|---|---|---|---|---|
| [ ] | `back-02-limpeza` | Corrige o que quebra hoje: redirect para rota inexistente nos exercícios, `/excuir/` nas fichas, `print()` com dados de formulário, `SECRET_KEY` com valor padrão. Tira do git os `.pyc` e o `instance/database.db` e conserta o `.gitignore`. Um nome só para a variável do banco. Limpa o `requirements.txt`. | 2.1 a 2.5, 3.8, 1.7 | Nenhuma rota dá erro 500 no smoke; `git ls-files` sem `.pyc`; `pip install -r requirements.txt` roda limpo. | ⏸ tirar arquivos versionados do Diogo; ⏸ `requirements.txt`; ⏸ variável do banco é configuração de produção |
| [ ] | `back-03-isolamento` | Uma academia não enxerga nada da outra: todas as consultas passam por um filtro de conta único; login obrigatório em todas as rotas; nenhuma rota GET apaga ou altera dados. Sem migration. | 3.1, 3.3, 3.4 | Logado na conta A, abrir qualquer `/…/<id da conta B>` dá 404. Teste automático para cada rota com id. | — |
| [ ] | `back-04-contas-e-papeis` | Separa **conta** (a academia) de **usuário** (dono, recepção, instrutor). Coluna `papel` e bloqueio no servidor das telas de dono. E-mail e CPF de aluno únicos por academia. `instrutor_id` obrigatório. | 3.2, 3.5, 3.6 | Dois usuários da mesma conta veem os mesmos alunos; o instrutor recebe 403 em relatórios e configurações. | ⏸ migrations e mudança de modelo; T1, T2 |
| [ ] | `front-02-layout` | O layout das telas logadas: `base.html` novo, cabeçalho, menu, rodapé e páginas de erro. O `base.html` antigo é renomeado (não apagado) para as telas antigas continuarem abrindo até serem trocadas. | — | Os arquivos batem com os do Drive; as telas antigas continuam iguais. | ⏸ renomear arquivo do Diogo |
| [ ] | `back-05-layout` | O que todo template novo precisa: `usuario` e `academia` em toda página, páginas de erro 403/404/500, avisos nas categorias do front, e os endereços do menu respondendo "em construção" para o layout não quebrar. | 4.2, 4.4, parte da 3.7 | Uma página de teste com o layout novo abre sem erro no celular e no PC, claro e escuro. | — |

## Fase B — Telas, na ordem de uso do cliente

Cada tela são duas branches: a `front-NN` (templates) e a `back-NN` que sai dela (rotas, regras e banco). As rotas antigas do Diogo são renomeadas para os nomes do front (tarefa 4.1) na branch da tela correspondente.

| | Branches | O que o cliente passa a fazer | Tarefas | Pronto quando | Trava |
|---|---|---|---|---|---|
| [ ] | `front-03-painel` + `back-06-painel` | Abrir o sistema e ver o resumo do dia: alunos ativos e inativos, novas matrículas, vencimentos, notificações. O instrutor vê o painel sem os números de dinheiro. Os cards de faturamento e de ausentes mostram "sem dado" até a cobrança e a frequência existirem. | 5.1, 4.1 | Os números batem com o banco de teste; métrica sem dado aparece como "sem dado", nunca como zero. | — |
| [ ] | `front-04-alunos` + `back-07-alunos` | Cadastrar, buscar, editar e inativar aluno; ver a página do aluno; exportar a lista. Datas em `dd/mm/aaaa` (hoje todo cadastro falharia na validação). | 4.1, 4.3, 4.4 | Fluxo completo de cadastro → edição → inativação no celular; busca sem recarregar a página. | ⏸ migration (colunas novas do aluno); T3; foto do aluno fica para depois do lançamento |
| [ ] | `front-05-planos` + `back-08-planos` | Criar, editar, pausar e reativar planos. Valor digitado como `R$ 1.234,56`. | 4.1, 4.3, 5.4 | Plano pausado some do cadastro de aluno e continua nos alunos que já o têm. | ⏸ migration (`avaliacoes_incluidas`) |
| [ ] | `front-06-cobranca` + `back-09-cobranca` | Receber a mensalidade: matrícula, renovação (recalcula vencimento e valor), confirmação em PIX, débito, crédito ou dinheiro, diária avulsa, histórico de pagamentos do aluno. No lançamento o PIX é **manual** (a recepção confere e confirma). | 5.2 | Matricular → cobrar → confirmar nas 4 formas → valor certo no painel. Cada pagamento guarda quem confirmou e como. | ⏸ migrations; reconciliar com a tabela `pagamentos` que o Diogo já criou; D3 |
| [ ] | `front-07-frequencia` + `back-10-frequencia` | Registrar a entrada do aluno em um toque; ver quem sumiu há mais de 15 dias; exportar. | 5.3 | Aluno sem nenhuma entrada aparece como "sem dado", não como "0 acessos". Ligar e desligar o check-in persiste. | ⏸ migration (`frequencias`) |
| [ ] | `front-08-relatorios` + `back-11-relatorios` | Fechamento do mês: recebido por forma de pagamento, inadimplência, custos e ponto de equilíbrio, exportação em CSV. Só dono e recepção. | 5.8 | Os totais batem com os cards do painel e com a soma dos pagamentos de teste. | ⏸ migration (`custos`) |
| [ ] | `front-09-config` + `back-12-config` | Dados da academia, horário, metas, modelos de mensagem, recebimento e funcionalidades ligadas. | 5.9 | Cada aba salva e o valor aparece nas outras telas (nome da academia no cabeçalho, meta no painel). | ⏸ migrations |
| [ ] | `front-10-equipe` + `back-13-equipe` | O dono convida a recepção e os instrutores; a pessoa cria a senha pelo link; "esqueci a senha". | 5.10 | Convite vencido ou já usado dá 404; o convidado entra já na conta certa e com o papel certo. | ⏸ migration (`convites`); D6, D9 |

### Módulos que o front já tem e não estão na ordem acima

Entram no primeiro cliente só se a decisão D8 disser que sim. Se ficarem de fora, o item do menu mostra "em construção" ou é escondido.

| | Branches | O que é | Tarefas | Observação |
|---|---|---|---|---|
| [ ] | `front-11-treinos` + `back-14-treinos` | Exercícios e fichas de treino dentro da página do aluno. | 5.5 | O backend antigo já tem as tabelas; muda o fluxo. Sem esta branch, o instrutor perde as telas antigas de ficha quando o layout novo assumir. |
| [ ] | `front-12-avaliacoes` + `back-15-avaliacoes` | Avaliação física: agendar, registrar, comparar. | 5.6 | ⏸ migration. IMC e RCQ calculados no servidor; é medição, não diagnóstico. |
| [ ] | `front-13-mensagens` + `back-16-mensagens` | Mensagens do dia pelo WhatsApp (link `wa.me`, custo zero). | 5.7 | ⏸ migration. |
| [ ] | `front-14-personal` + `back-17-personal` | Variante Personal Trainer: agenda de sessões e pacotes. | 5.11 | ⏸ migrations. Só se o primeiro cliente for personal (D1). |

## Fase C — Revisão de segurança

Com a skill `saas-flask-seguranca`, seção por seção, cada item marcado com evidência (arquivo e linha, ou teste). Falha P0 bloqueia o lançamento.

| | Branch | O que entrega | Tarefas | Trava |
|---|---|---|---|---|
| [ ] | `back-18-seguranca` | Limite de tentativas no login e nas rotas de senha e convite. Cabeçalhos de segurança, HTTPS forçado e CSP. Prazo de validade da sessão. Mesma mensagem para "conta desativada" e "senha errada" (hoje o login revela que a conta existe). Remoção do popup de perfil do login, já que o papel passa a vir do banco. Botão "Entrar com digital" escondido. | 1.6, 3.7 | ⏸ dependências novas (Flask-Limiter, Flask-Talisman); T4 |
| [ ] | `back-19-lgpd` | Opt-in de WhatsApp por aluno, exportar e excluir os dados de um aluno (só o dono), logs sem CPF e telefone, links de termos e política na criação de conta. | 3.9 | ⏸ migration; D7 |
| [ ] | (sem branch) Checklist final | Rodar a checklist completa da skill, o teste "conta A × conta B" em todas as rotas, `pip-audit`, e conferir que `.env` nunca entrou no histórico. Relatório com severidade e correção de cada achado. | — | — |

## Fase D — Deploy de produção

| | Item | O que é | Trava |
|---|---|---|---|
| [ ] | `back-20-producao` | Postgres no lugar do SQLite: todas as migrations rodadas do zero num Postgres de teste; configuração de produção conferida (`DEBUG` desligado, cookies seguros, segredos só em variável de ambiente). | 3.10; ⏸ configuração de produção; D4 |
| [ ] | Ambiente | Contratar hospedagem e banco, apontar o domínio, HTTPS, variáveis de ambiente, backup automático do banco e teste de restauração. | D4, D5 |
| [ ] | Ensaio geral | Roteiro manual completo em produção com uma conta de teste: criar conta → cadastrar aluno → matricular → cobrar → registrar entrada → fechar o mês. No iPhone e no Android de verdade. | — |
| [ ] | Entrada do cliente | Criar a conta do primeiro cliente, importar os alunos dele se houver planilha, treinar quem vai usar. | D9, D10 |

## Decisões do Adauto

Decisões de negócio ou de conta externa. Nenhuma é técnica: só você pode responder. A coluna "Até quando" diz qual branch para se a resposta não existir.

| # | Decisão | O que trava | Sugestão | Até quando |
|---|---|---|---|---|
| D1 | **Quem é o primeiro cliente:** academia ou personal trainer? Quantas pessoas vão usar (só o dono, ou recepção e instrutores também)? | A ordem inteira da Fase B e se a equipe (`back-13`) é obrigatória | Academia, com a variante Personal depois | Antes de `back-04` |
| D2 | **Preço do Vale Tec** para a academia (mensalidade, teste grátis, cobrança por aluno ou fixa) e como você vai cobrar o cliente. | Não trava código do lançamento; trava a conversa de venda e o contrato | Preço fixo mensal no piloto, cobrado por fora do sistema | Antes da entrada do cliente |
| D3 | **PIX:** lançar com confirmação manual (a recepção confere o comprovante) ou só com PIX automático? Se automático, qual PSP (Asaas, Mercado Pago ou Efí) e ele aceita pessoa física sem CNPJ? | `back-09-cobranca` | Lançar com PIX manual; PIX automático depois do piloto | Antes de `back-09` |
| D4 | **Hospedagem e banco de produção:** onde o backend e o Postgres vão rodar e quanto você aceita pagar por mês. A Vercel de hoje só serve o mock do front. | `back-20-producao` e o ambiente | Levantar 2 ou 3 opções com preço antes de decidir | Antes da Fase D |
| D5 | **Domínio** do sistema (ex.: `app.valetec.com.br`). | Cookies seguros, link do convite, e-mails, e mais tarde o login com digital | Registrar já: demora a propagar e é barato | Antes da Fase D |
| D6 | **Provedor de e-mail** para convite e "esqueci a senha". | `back-13-equipe` | Escolher junto com o domínio | Antes de `back-13` |
| D7 | **Termos de uso e política de privacidade (LGPD):** quem escreve, e o contrato com a academia dizendo que ela é a dona dos dados dos alunos e o Vale Tec só os processa. | `back-19-lgpd` e a entrada do cliente | Texto revisado por advogado antes do primeiro cliente pagante | Antes da Fase C |
| D8 | **Quais módulos extras entram no primeiro cliente:** fichas de treino, avaliação física, mensagens do dia. | Tamanho da Fase B | Fichas entram (o instrutor usa todo dia e o backend antigo já tem); avaliação e mensagens depois | Antes de `front-11` |
| D9 | **Como o primeiro cliente recebe o acesso:** você cria a conta dele à mão, ou ele se cadastra sozinho pela tela "Criar conta"? | Se `back-13-equipe` precisa estar pronta no lançamento | Conta criada por você no piloto; auto-cadastro depois | Antes de `back-13` |
| D10 | **Dados que o cliente já tem:** importar a planilha de alunos dele ou ele cadastra do zero? | A entrada do cliente | Importar por você, uma vez, com conferência | Antes da entrada do cliente |
| D11 | **Suporte e backup:** quem atende o cliente e em que horário; quanto tempo de dado ele pode perder num desastre. | A rotina de backup do ambiente | Backup diário, guardado por 30 dias | Antes da Fase D |

### Decisões técnicas (Adauto com o Diogo)

| # | Decisão | O que trava | Sugestão |
|---|---|---|---|
| T1 | Tabela `contas` separada, ou `conta_id` apontando para o dono? | `back-04` e tudo depois | Tabela `contas`: é onde ficam os dados da academia |
| T2 | O Diogo revisa branch por branch, na ordem, ou em lotes? PR empilhado só anda se o anterior for aprovado. | O ritmo de todo o roadmap | Combinar um dia fixo de revisão |
| T3 | Aluno: `ativo` sim/não, ou `status` (ativo, pausado, cancelado)? | `back-07` e o relatório de cancelamento | `status`, se o motivo de cancelamento for entrar nos relatórios |
| T4 | Entram as dependências Flask-Limiter e Flask-Talisman? | `back-18` | Sim: são pequenas e padrão de mercado |

## Depois do primeiro cliente

Nada aqui trava o lançamento: login com digital (depende do domínio), PIX automático com webhook, upload de fotos, PDF e Excel, WhatsApp pela API oficial, melhorias de ficha e tema por usuário.

## Achados em aberto

Coisas vistas durante o trabalho que ainda não têm dono. Cada uma já está encaixada numa branch acima.

| Achado | Onde | Vai em |
|---|---|---|
| `/instrutores/painel/` dá erro 500 para quem está logado (`alunos.excluirAlunos` não existe) | `main` | Some com o painel novo (`back-06`) |
| `/fichas/novo/` abre sem login | `main` | `back-03` |
| O login diz "Usuário desativado" antes de conferir a senha, o que revela que a conta existe | `auth_service.py` | `back-18` |
| O popup de perfil do login fecha com Esc ou "voltar" antes do primeiro toque, deixando o formulário sem perfil | front | Some com a remoção do popup (`back-18`) |
| Erro "Transition was skipped" no console ao sair da tela de login para uma tela do layout antigo | front (`tema.js` / transição entre páginas) | Conferir de novo depois de `back-05` |
| Os testes de navegador de 06/10 usavam Playwright, que não está instalado nesta máquina | ambiente | ⏸ decidir se instala (não entra no `requirements.txt` do projeto) |

## Registro de atualizações

| Data | O que mudou |
|---|---|
| 10/10/2026 | Criado na Etapa 0. `front-01` (PR #8) e `back-01-auth-login` enviadas. |
