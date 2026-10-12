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

- **Sai de:** `back-08-planos` · **PR:** [#21](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/21) → `back-08-planos` · **Data:** 10/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `cobranca/receber.html`, `alunos/renovar.html` e `alunos/pagamentos.html`.
- **Testes:** os 3 arquivos conferidos byte a byte com o Drive.
- **Observações:** sozinha não muda nada para quem usa. O `receber.html` não tem caminho para PIX manual (está no roadmap, em achados).

## back-09-cobranca

- **Sai de:** `front-05-cobranca` · **PR:** [#22](https://github.com/Dsmalosti/ValeDesenvolvimentos-Academia/pull/22) → `front-05-cobranca` · **Data:** 12/10/2026 (proposta de esquema em 10/10)
- **O que mudou:** tabela nova `cobrancas` (o que se deve) e `pagamentos` em outro formato (o que entrou, com quem confirmou e como), no esquema que o Diogo aprovou. Depois de cadastrar o aluno a recepção vai direto receber; recebe em PIX, débito, crédito ou dinheiro, sempre com confirmação manual; renovar com ou sem troca de plano; diária avulsa; extrato na tela e em CSV. A regra de "em dia / pendente" passou a ler as cobranças, e quem tem cobrança em aberto conta como pendente. As 3 telas antigas de pagamento viraram redirecionamentos.
- **Migration:** `b09d5e6f7a80_cobrancas_e_pagamentos.py`, escrita à mão, **converte a tabela de pagamentos**. Backup antes; depois do pull, `flask db upgrade`.
- **Testes:** `pytest` 214 de 214 (38 novos em `tests/test_cobrancas.py`); migration num Postgres temporário, 21 checagens, com ida e volta e pagamentos antigos dentro; navegador: cobrança 33 de 33, alunos 32 de 32, planos 31 de 31, painel 74 de 74, login 60 de 60; varredura de rotas por papel sem nenhuma rota pior.
- **Observações:** o template `cobranca/receber.html` do repositório tem 7 ajustes marcados para o PIX manual que o do Drive não tem. Excluir aluno com cobrança passou a ser recusado pela aplicação (antes era o banco). PIX automático, estorno e cobrança em lote pelo WhatsApp não existem ainda. Em produção o servidor precisa estar no fuso de Brasília.
- **Doc:** `docs/mudancas/back-09-cobranca.md`

## front-06-frequencia

- **Sai de:** `back-09-cobranca` · **PR:** a abrir → `back-09-cobranca` · **Data:** 12/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `frequencia/index.html`, `frequencia/_sugestoes.html` e `alunos/_linhas_acesso.html`.
- **Testes:** os 3 arquivos conferidos byte a byte com o Drive.

## back-10-frequencia

- **Sai de:** `front-06-frequencia` · **PR:** a abrir → `front-06-frequencia` · **Data:** 12/10/2026
- **O que mudou:** check-in em um toque (busca ao vivo por nome ou CPF), quem está na academia agora, entradas por hora, planilha do dia; card "Ausentes há mais de 15 dias" e alunos em risco por frequência no painel; assiduidade no perfil; bloquear e liberar acesso (coluna `alunos.acesso_liberado`). Quem não tem entrada registrada é "sem dado", nunca "0".
- **Migration:** `b10e6f7a8b90_frequencias_e_acesso.py`: cria `frequencias`, acrescenta `alunos.acesso_liberado` e liga o check-in nas contas do modelo academia. **Depois do pull, `flask db upgrade`.**
- **Testes:** `pytest` 236 de 236 (22 novos em `tests/test_frequencia.py`); migration num Postgres temporário, 14 checagens; navegador: frequência 31 de 31, cobrança 33 de 33, alunos 32 de 32, planos 31 de 31, painel 74 de 74, login 60 de 60; varredura de rotas por papel sem nenhuma rota pior.
- **Observações:** `alunos/detalhe.html` tem 1 ajuste marcado ("Sem dado"). Não há registro de saída: "na academia agora" é quem entrou há menos de 90 minutos. Mensalidade atrasada não barra a entrada; o botão Bloquear, sim. Decisão pendente do Adauto: como medir assiduidade.
- **Doc:** `docs/mudancas/back-10-frequencia.md`

## front-07-relatorios

- **Sai de:** `back-10-frequencia` · **PR:** a abrir → `back-10-frequencia` · **Data:** 12/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `relatorios/admin.html` e `relatorios/index.html`.
- **Testes:** os 2 arquivos conferidos byte a byte com o Drive.

## back-11-relatorios

- **Sai de:** `front-07-relatorios` · **PR:** a abrir → `front-07-relatorios` · **Data:** 12/10/2026
- **O que mudou:** o menu "Administrativo" mostra faturamento por forma, receita de 12 meses, ponto de equilíbrio contra os custos fixos (cadastrados na própria tela), fechamento, lançamentos com filtro e CSV, mapa de movimento, retenção, churn e alunos em risco. O banco passou a guardar quando cada aluno é desativado (`alunos.data_inativacao`, preenchida sozinha). O gráfico de ativos do painel passou a contar quem saiu depois.
- **Migration:** `b11f7a8b9c00_custos_e_data_de_inativacao.py`: cria `custos` e acrescenta `alunos.data_inativacao`. **Depois do pull, `flask db upgrade`.**
- **Testes:** `pytest` 257 de 257 (21 novos em `tests/test_relatorios.py`); migration num Postgres temporário, 12 checagens; navegador: relatórios 28 de 28, frequência 31 de 31, cobrança 33 de 33, alunos 32 de 32, planos 31 de 31, painel 74 de 74, login 60 de 60; varredura de rotas por papel sem nenhuma rota pior.
- **Observações:** `relatorios/admin.html` tem 13 ajustes marcados que o Drive não tem. Excel e PDF não existem (só CSV). Retenção e churn começam como "sem dado": só contam quem for desativado daqui em diante. `/relatorios` leva ao painel administrativo.
- **Doc:** `docs/mudancas/back-11-relatorios.md`

## Onde parou (12/10/2026)

Alunos, planos, cobrança, frequência e relatórios prontos e enviados. PRs #17 a #22 abertos; **faltam os PRs de `front-06`, `back-10`, `front-07` e `back-11`**. O banco local do Adauto está em `b08c3d4e5f60`: **falta rodar `b09`, `b10` e `b11`** (pedir o OK dele; backup antes). A próxima é `front-08-config` + `back-12-config` (dados da academia, horário, metas, modelos de mensagem, recebimento, ligar e desligar o check-in), depois equipe, treinos, avaliações, mensagens, personal, segurança, LGPD e produção. Pendências do Adauto: levar para o Drive os ajustes de `cobranca/receber.html` (7), `alunos/detalhe.html` (1) e `relatorios/admin.html` (13); D12, D13, assiduidade, pesos da nota de risco, botão de reativar aluno, regra de nome de plano; dele e do Diogo: hospedagem, domínio e e-mail (D4, D5, D6).
