# Log de branches

Uma entrada por branch, da mais antiga para a mais nova. É por aqui que a próxima sessão sabe onde parou.
O que fazer a seguir está em `docs/ROADMAP-LANCAMENTO.md`; os detalhes de cada mudança de backend estão em `docs/mudancas/<branch>.md`.

## front-01

- **Sai de:** `main` (`9b61934`) · **PR:** [#8](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/8) → `main` · **Data:** 10/10/2026
- **O que mudou:** tela de login nova (`auth/login.html`, `base_auth.html`, macros e todos os estáticos do front), correção de popups do iPhone (`ajustes-iphone.css` e `.js`), `CLAUDE.md` e as três skills em `.claude/skills`.
- **Testes:** smoke de rotas igual à `main` (nenhum `.py` muda); tela conferida no navegador em 375 px e 1440 px, claro e escuro, console sem erros.
- **Observações:** sozinha não muda nada para quem usa; a tela só aparece com a `back-01`. A linha da correção do iPhone no `base.html` novo entra na `front-02-painel`, porque o `base.html` do repositório ainda é o layout antigo.

## back-01-auth-login

- **Sai de:** `front-01` · **PR:** [#9](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/9) → `front-01` · **Data:** 06/10 e 10/10/2026
- **O que mudou:** blueprint `auth` (`/login`, `POST /sair`, e `/esqueci-senha` e `/criar-conta` respondendo 501); quem não está logado cai na tela nova; e-mail sem diferenciar maiúscula; cookies seguros no `ProductionConfig`; o destino pedido antes do login fica guardado na sessão.
- **Testes:** 51 de 52 checagens de servidor (a que falha é o limite de tentativas, tarefa 1.6, fora da branch); 7 de 7 dos cookies de produção; smoke com os mesmos status da `main`; fluxo completo no navegador.
- **Observações:** a branch tem um commit `teste` (com `.pyc` e `launch.json`) e, em seguida, um commit que desfaz essa parte. O resultado final não tem nenhum dos dois; não foi usado `--force`.
- **Doc:** `docs/mudancas/back-01-auth-login.md`

## back-02-limpeza

- **Sai de:** `back-01-auth-login` · **PR:** [#10](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/10) → `back-01-auth-login` · **Data:** 10/10/2026
- **O que mudou:** editar exercício não dá mais erro 500; `/fichas/excuir/` virou `/fichas/excluir/`; saíram os `print()` com dados de formulário; o painel conta os alunos ativos; `.gitignore` consertado. Primeira pasta de testes automáticos (`tests/`).
- **Testes:** `pytest` 15 de 15; smoke com os mesmos status da `main`.
- **Observações:** o que dependia de autorização (tirar `.pyc` e `database.db` do git, `requirements.txt`, variável do banco, `SECRET_KEY`) foi para a `back-05-repo-e-config`. O `pytest` não está no `requirements.txt`.
- **Doc:** `docs/mudancas/back-02-limpeza.md`

## back-03-isolamento

- **Sai de:** `back-02-limpeza` · **PR:** [#11](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/11) → `back-02-limpeza` · **Data:** 10/10/2026
- **O que mudou:** filtro de conta num lugar só (`app/helpers/conta.py`); usuários, fichas, treinos, painel e select de planos passam a enxergar só a própria conta; login obrigatório em todas as rotas não públicas; excluir treino só por POST.
- **Testes:** `pytest` 30 de 30. Contraprova: os 15 testes de isolamento rodados contra o código anterior dão 9 falhas. Smoke com os status esperados.
- **Observações:** exercício continua sendo catálogo único (precisa de coluna nova); e-mail e CPF de aluno continuam únicos no banco inteiro. Vão para a `back-06`. Antes do deploy, conferir se há aluno ou plano sem dono no banco.
- **Doc:** `docs/mudancas/back-03-isolamento.md`

## docs-01-decisoes-e-termos

- **Sai de:** `back-03-isolamento` · **PR:** [#12](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/12) → `back-03-isolamento` · **Data:** 10/10/2026
- **O que mudou:** nenhuma linha de backend ou de front. Entram as respostas do Adauto às decisões de negócio no roadmap; os rascunhos `docs/legal/Termos-de-Uso.md` e `Politica-de-Privacidade.md`, com o `LEIA-ME.md` do que ele precisa conferir; e `tests/navegador/login_navegador.py`, o teste da tela de login com Playwright.
- **Testes:** `pytest` 30 de 30; teste de navegador 60 de 60 (celular de 360 e 390 px com toque, desktop de 1440 px, claro e escuro, e uso só pelo teclado).
- **Observações:** os textos legais são rascunho e não estão publicados; a tabela do `LEIA-ME.md` mostra quais promessas o sistema ainda não cumpre. O Playwright foi instalado só no ambiente do Adauto (não está no `requirements.txt`). O banco local do Adauto foi alinhado e ganhou a tabela `pagamentos`; ele ainda tem colunas a mais, vindas de uma branch antiga (`exercicio.instrutor_id`, `ficha.instrutor_id`, `alunos.data_inicio_plano`), que podem conflitar com a migration da `back-06`.

## front-02-painel

- **Sai de:** `docs-01-decisoes-e-termos` · **PR:** [#13](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/13) → `docs-01-decisoes-e-termos` · **Data:** 10/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `base.html`, `_cabecalho.html`, `_gaveta.html`, `_rodape.html`, `_digital.html`, `errors/` e `painel/` (index e os dois arquivos de popups). O `base.html` antigo foi renomeado para `base_antigo.html` e as 19 telas antigas passaram a herdar dele (só a linha `extends` mudou).
- **Testes:** os 12 arquivos novos conferidos byte a byte com o Drive; smoke de rotas idêntico ao da `back-03`; `pytest` 30 de 30.
- **Observações:** sozinha não muda nada para quem usa. O Adauto pediu esta branch em 10/10 para testar o front no código real.

## back-04-painel

- **Sai de:** `front-02-painel` · **PR:** [#14](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/14) → `front-02-painel` · **Data:** 10/10/2026
- **O que mudou:** depois do login abre o painel novo, com números do banco (alunos, planos, pagamentos) e só da conta logada. `context_processor` com `usuario` e `academia`. Blueprint `painel`; seções sem backend respondem "em construção" (`app/blueprints/pendentes.py`); pontes temporárias dos nomes de rota do front para as telas antigas de alunos, planos, exercícios e fichas; páginas de erro 403/404/500 do front. A rota inicial antiga (`main.homepage`) virou atalho para o painel.
- **Testes:** `pytest` 49 de 49 (19 novos em `tests/test_painel.py`); navegador com Playwright: painel 66 de 66 e login 60 de 60 (celular de 390 px com toque e desktop de 1440 px, claro e escuro); smoke sem mudança de status nas rotas que já existiam.
- **Observações:** `academia` ("Minha academia") e o papel do usuário são provisórios até existir a tabela de contas. O template `painel/index.html` do repositório tem 6 ajustes que o do Drive não tem (lista no doc). O front tem botões de demonstração que não fazem nada de verdade.
- **Doc:** `docs/mudancas/back-04-painel.md`

## back-05-repo-e-config

- **Sai de:** `back-04-painel` · **PR:** [#15](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/15) → `back-04-painel` · **Data:** 10/10/2026
- **O que mudou:** 102 `.pyc` e o `instance/database.db` saíram do git (continuam no disco); `mysql-connector==2.2.9` saiu do `requirements.txt` e entrou o `requirements-dev.txt`; `DATABASE_URL` é o nome único da variável do banco (o antigo `DATABASE_URI` ainda funciona, com aviso no log); `SECRET_KEY` sem valor padrão no `config.py`.
- **Testes:** `pytest` 55 de 55 (6 novos em `tests/test_config.py`); `pip install -r requirements.txt` e `-r requirements-dev.txt` num ambiente virtual novo, em Python 3.13, sem erro.
- **Observações:** cada pessoa precisa renomear `DATABASE_URI` para `DATABASE_URL` no próprio `.env`. Quem trocar para uma branch antiga volta a ver os `.pyc` versionados.
- **Doc:** `docs/mudancas/back-05-repo-e-config.md`

## back-06-contas-e-papeis

- **Sai de:** `back-05-repo-e-config` · **PR:** [#16](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/16) → `back-05-repo-e-config` · **Data:** 10/10/2026
- **O que mudou:** modelo `Conta` (a academia) separado do usuário; `conta_id` e `papel` em `instrutores`; `conta_id` em alunos, planos, pagamentos e exercícios, e o filtro de conta passa a usar essa coluna; permissão por papel no servidor (`papel_requerido`); e-mail e CPF de aluno únicos por academia; exercício com dono (os antigos viram catálogo padrão); `/instrutores/cadastro/` fechado e comando `flask criar-conta`; nome da academia e papel vindos do banco.
- **Migration:** `b06c0a1e2f30_contas_e_papeis.py`, escrita à mão, move dados. **Depois do pull, o app só sobe depois de `flask db upgrade`.**
- **Testes:** `pytest` 111 de 111 (56 novos em `tests/test_contas.py`); migration testada num Postgres temporário, 25 checagens, incluindo `flask db check` sem diferença, downgrade e upgrade de novo; navegador: painel 66 de 66, login 60 de 60.
- **Observações:** não há como existir instrutor ou recepção até o convite de equipe (`back-13`); o instrutor ainda não tem painel; as migrations ANTIGAS não rodam do zero num Postgres vazio (problema anterior, a resolver antes do deploy). O banco local do Adauto recebeu esta migration em 10/10/2026, com a autorização dele.
- **Doc:** `docs/mudancas/back-06-contas-e-papeis.md`

## front-03-alunos

- **Sai de:** `back-06-contas-e-papeis` · **PR:** [#17](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/17) → `back-06-contas-e-papeis` · **Data:** 10/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `alunos/lista.html`, `detalhe.html`, `novo.html`, `editar.html`, `buscar.html`, `_form.html`, `_campos.html` e `_resultados.html`.
- **Testes:** os 8 arquivos conferidos byte a byte com o Drive; `pytest` sem mudança.
- **Observações:** sozinha não muda nada para quem usa: nenhuma rota aponta para esses templates antes da `back-07-alunos`.

## back-07-alunos

- **Sai de:** `front-03-alunos` · **PR:** [#18](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/18) → `front-03-alunos` · **Data:** 10/10/2026
- **O que mudou:** o menu "Alunos" abre as telas novas: lista com busca, filtros e paginação; cadastro e edição validados no servidor (datas em `dd/mm/aaaa`, CPF com dígitos conferidos, único por academia); perfil; busca ao vivo; exportar CSV; desativar (não apaga) e excluir (só o dono). A regra de "ativo, pendente ou inativo" saiu do painel para `situacao_service.py`, usada pelos dois. Quatro colunas novas em `alunos`.
- **Migration:** `b07a1f2e3d40_colunas_novas_do_aluno.py`: só acrescenta `data_inicio`, `dia_vencimento`, `forma_pagamento` e `observacoes`, vazias. **Depois do pull, rodar `flask db upgrade`.**
- **Testes:** `pytest` 155 de 155 (47 novos em `tests/test_alunos.py`); migration num Postgres temporário, 11 checagens; navegador: alunos 30 de 30, painel 70 de 70, login 60 de 60; varredura de todas as rotas GET como dono, recepção e instrutor, sem nenhuma rota pior que na branch anterior.
- **Observações:** as telas antigas de alunos continuam no ar (as outras telas antigas apontam para elas). Reativar aluno ainda é pela tela antiga. A foto do aluno não é gravada. O botão "Bloquear" só avisa. Depois de cadastrar, vai para o perfil e não para o recebimento (isso volta na cobrança).
- **Doc:** `docs/mudancas/back-07-alunos.md`

## front-04-planos

- **Sai de:** `back-07-alunos` · **PR:** [#19](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/19) → `back-07-alunos` · **Data:** 10/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `planos/lista.html`, `form.html` e `_form.html`.
- **Testes:** os 3 arquivos conferidos byte a byte com o Drive.
- **Observações:** sozinha não muda nada para quem usa: nenhuma rota aponta para esses templates antes da `back-08-planos`.

## back-08-planos

- **Sai de:** `front-04-planos` · **PR:** [#20](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/20) → `front-04-planos` · **Data:** 10/10/2026
- **O que mudou:** o menu "Planos" abre as telas novas: cartões com alunos, faturamento do mês e participação de cada plano (a mesma conta do gráfico do painel); criar e editar com valor em `1.234,56` conferido no servidor; pausar e reativar. Coluna nova `planos.avaliacoes_incluidas`.
- **Migration:** `b08c3d4e5f60_avaliacoes_incluidas_no_plano.py`: só acrescenta a coluna, com 0 nos planos que já existem. **Depois do pull, rodar `flask db upgrade`.**
- **Testes:** `pytest` 179 de 179 (26 novos em `tests/test_planos.py`); migration num Postgres temporário, 12 checagens; navegador: planos 31 de 31, alunos 30 de 30, painel 74 de 74, login 60 de 60; varredura de rotas por papel sem nenhuma rota pior.
- **Observações:** o front novo não tem botão de excluir plano, só de pausar. As telas antigas de planos continuam no ar. O instrutor vê nome e preço, sem os valores de faturamento. Nome de plano não repete na academia (regra nossa). A variante Personal (pacotes) fica para a `back-17`.
- **Doc:** `docs/mudancas/back-08-planos.md`

## front-05-cobranca

- **Sai de:** `back-08-planos` · **PR:** a abrir → `back-08-planos` · **Data:** 10/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `cobranca/receber.html`, `alunos/renovar.html` e `alunos/pagamentos.html`.
- **Testes:** os 3 arquivos conferidos byte a byte com o Drive.
- **Observações:** sozinha não muda nada para quem usa. O `receber.html` não tem caminho para PIX manual (está no roadmap, em achados).

## back-09-cobranca (em andamento: só a proposta)

- **Sai de:** `front-05-cobranca` · **PR:** a abrir → `front-05-cobranca` · **Data:** 10/10/2026
- **O que tem:** `docs/mudancas/back-09-cobranca.md` com a proposta das tabelas `cobrancas` (nova) e `pagamentos` (a atual, em outro formato), as regras que saem delas, os passos da migration e 6 perguntas para o Diogo, cada uma com recomendação.
- **O que NÃO tem:** código, modelo ou migration. O Diogo pediu para ver o esquema antes.
- **Para retomar:** com as respostas do Diogo, escrever modelo + migration `b09…` (testar num Postgres temporário com pagamentos antigos dentro), o serviço de cobrança, as rotas `cobrancas.*`, `alunos.renovar` e `alunos.pagamentos`, trocar a leitura de vencimento do `situacao_service.py` e do `painel_service.py` para as cobranças pagas, e voltar o fim do cadastro de aluno para a tela de receber.

## Onde parou (10/10/2026)

Alunos e planos prontos (PRs #17 a #20). A **cobrança está esperando o Diogo**: a `back-09-cobranca` tem só a proposta de esquema, com 6 perguntas. Não escrever modelo nem migration antes da resposta. Enquanto isso, o que não depende da cobrança pode andar: a próxima da fila que não usa pagamentos é `front-08-config` + `back-12-config` (dados da academia, horário, metas); frequência e relatórios dependem de decisões ou da cobrança. Faltam abrir os PRs de `front-05-cobranca` e `back-09-cobranca`. Do Adauto: ajustar o front para PIX manual, D12, D13, botão de reativar aluno, regra de nome de plano; dele e do Diogo: hospedagem, domínio e e-mail (D4, D5, D6).
