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

## front-08-config

- **Sai de:** `back-11-relatorios` · **PR:** a abrir → `back-11-relatorios` · **Data:** 12/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `config/index.html`, `config/_metas.html`, `config/recebimento.html` e `_digital_linha.html` (este num segundo commit: a tela o inclui).
- **Testes:** os 4 arquivos conferidos byte a byte com o Drive.

## back-12-config

- **Sai de:** `front-08-config` · **PR:** a abrir → `front-08-config` · **Data:** 12/10/2026
- **O que mudou:** o dono troca os dados da academia e o horário, liga e desliga o check-in, define o prazo da inatividade automática e as três metas (que viram a linha dos gráficos do painel e do administrativo); dono e recepção personalizam os modelos de mensagem; a tela de recebimento mostra de onde veio cada confirmação do mês. A regra "o aluno vira inativo sozinho depois de X dias sem renovar" roda ao abrir o painel, uma vez por dia.
- **Migration:** `b12a8b9c0d10_configuracoes_da_conta.py`: 10 colunas em `contas` e a tabela `modelos_mensagem`. **Depois do pull, `flask db upgrade`.** Atenção: a inatividade nasce ligada, com 60 dias.
- **Testes:** `pytest` 287 de 287 (30 novos em `tests/test_configuracoes.py`); migration num Postgres temporário, 15 checagens; navegador: configurações 29 de 29, relatórios 28 de 28, frequência 31 de 31, cobrança 33 de 33, alunos 32 de 32, planos 31 de 31, painel 74 de 74, login 60 de 60; varredura de rotas por papel sem nenhuma rota pior.
- **Observações:** a equipe aparece na tela, mas convidar, trocar papel e remover só avisam (é a `back-13`). "Ligar PIX" só avisa. A logo não é gravada. Dois templates têm 1 ajuste marcado cada.
- **Doc:** `docs/mudancas/back-12-config.md`

## front-09-equipe

- **Sai de:** `back-12-config` · **PR:** a abrir → `back-12-config` · **Data:** 12/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `auth/criar_conta.html`, `auth/convite.html` e `auth/esqueci_senha.html`.
- **Testes:** os 3 arquivos conferidos byte a byte com o Drive.

## back-13-equipe

- **Sai de:** `front-09-equipe` · **PR:** a abrir → `front-09-equipe` · **Data:** 12/10/2026
- **O que mudou:** o dono cria a própria conta em `/criar-conta` (academia ou personal) e já entra; convida recepção e instrutores por link (7 dias, uso único, só o hash no banco), troca o papel e remove (desativa, sem apagar); troca de senha por link (1 hora, uso único). Envio de e-mail por SMTP com a biblioteca padrão; sem configurar, o convite é copiado e o suporte gera o link de senha com `flask link-de-senha`.
- **Migration:** `b13b9c0d1e20_convites_e_troca_de_senha.py`: cria `convites` e `redefinicoes_senha`. **Depois do pull, `flask db upgrade`.**
- **Testes:** `pytest` 317 de 317 (31 novos em `tests/test_equipe.py`); migration num Postgres temporário, 13 checagens; navegador: equipe 34 de 34 (dono, convidado e visitante em navegadores separados) e as outras telas sem mudança; varredura de rotas por papel sem nenhuma rota pior.
- **Observações:** `auth/nova_senha.html` é novo e não veio do Drive. As telas públicas ainda não têm limite de tentativas (P0, `back-18`). O instrutor convidado vê "em construção" no painel. Arquivo novo `.env.example`, só com os nomes das variáveis.
- **Doc:** `docs/mudancas/back-13-equipe.md`

## front-10-treinos

- **Sai de:** `back-13-equipe` · **PR:** a abrir → `back-13-equipe` · **Data:** 12/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `exercicios/` (lista, detalhe, form) e `treinos/` (biblioteca, modelo, atribuir, ficha, _catalogo, enviar).
- **Testes:** os 9 arquivos conferidos byte a byte com o Drive.

## back-14-treinos

- **Sai de:** `front-10-treinos` · **PR:** a abrir → `front-10-treinos` · **Data:** 12/10/2026
- **O que mudou:** catálogo de exercícios (64 padrão, que ninguém edita, mais os da academia), com busca, filtro, detalhe, novo e editar; 5 modelos prontos de ficha; usar o modelo com um ou vários alunos; editor da ficha por treino (A a E): ajustar, adicionar pelo catálogo, tirar, criar treino, salvar, excluir; enviar pelo WhatsApp com o texto da ficha pronto (link `wa.me`, custo zero) e baixar em texto. As telas antigas de exercício e ficha continuam no ar, sem alteração.
- **Migration:** `b14c0d1e2f30_treinos_e_catalogo_padrao.py`: acrescenta colunas em `exercicio`, `ficha`, `treino` e `treino_exercicio`, dá letra aos treinos que já existem e grava o catálogo padrão. **Depois do pull, `flask db upgrade`.**
- **Testes:** `pytest` 352 de 352 (36 novos em `tests/test_treinos.py`); migration num Postgres temporário, 25 checagens; navegador: treinos 79 de 79 e as outras nove telas sem mudança; varredura de rotas por papel sem nenhuma rota pior.
- **Observações:** arquivo novo `app/dados_padrao.py` (só dados: exercícios e modelos). `treinos/enviar.html` tem 3 ajustes marcados (imagem e PDF desabilitados). "Editar o modelo" e "Duplicar ficha" seguem como aviso do front. Comando novo `flask semear-catalogo`.
- **Doc:** `docs/mudancas/back-14-treinos.md`

## front-11-avaliacoes

- **Sai de:** `back-14-treinos` · **PR:** a abrir → `back-14-treinos` · **Data:** 12/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `avaliacoes/` (agenda, agendar, aluno, registrar, resultado).
- **Testes:** os 5 arquivos conferidos byte a byte com o Drive.

## back-15-avaliacoes

- **Sai de:** `front-11-avaliacoes` · **PR:** a abrir → `front-11-avaliacoes` · **Data:** 12/10/2026
- **O que mudou:** agenda de avaliações (hoje, amanhã, semana, não realizadas); agendar e remarcar, sem dois alunos no mesmo horário do mesmo avaliador; assistente de quatro etapas com IMC e cintura/quadril calculados só no servidor; resultado com a comparação e botão do WhatsApp com o texto pronto; histórico com gráfico; cartão no perfil do aluno; aviso e card "Avaliações de hoje" no painel. Medidas só para dono e instrutor: a recepção agenda e é barrada no resto.
- **Migration:** `b15d1e2f3a40_avaliacoes_fisicas.py`: cria `avaliacoes_agendadas` e `avaliacoes_fisicas`. **Depois do pull, `flask db upgrade`.**
- **Testes:** `pytest` 397 de 397 (45 novos em `tests/test_avaliacoes.py`); migration num Postgres temporário, 16 checagens; navegador: avaliações 68 de 68 e as outras dez telas sem mudança; varredura de rotas por papel sem nenhuma rota pior.
- **Observações:** arquivo novo `app/helpers/whatsapp.py` (o endereço `wa.me`, que a ficha de treino também passou a usar). 10 ajustes marcados em templates (lista no doc). Ficaram de fora: fotos, PDF, cobrança da avulsa e percentual de gordura.
- **Doc:** `docs/mudancas/back-15-avaliacoes.md`

## front-12-mensagens

- **Sai de:** `back-15-avaliacoes` · **PR:** a abrir → `back-15-avaliacoes` · **Data:** 12/10/2026
- **O que mudou:** só template. Cópia fiel do Drive de `mensagens/index.html`.
- **Testes:** o arquivo conferido byte a byte com o Drive.

## back-16-mensagens

- **Sai de:** `front-12-mensagens` · **PR:** a abrir → `front-12-mensagens` · **Data:** 12/10/2026
- **O que mudou:** a fila de mensagens do dia: aniversariantes de hoje, avaliações de amanhã e mensalidades vencidas, cada uma com o texto dos modelos de Configurações já preenchido e o botão que abre o WhatsApp de quem usa (custo zero, sem API; decisão D14). O toque fica gravado ("Enviada hoje" para toda a equipe); cobrança no máximo a cada 3 dias; instrutor não vê cobrança. Botões de WhatsApp que eram demonstração (perfil, lista, painel, avisos) viraram links; a cobrança em lote do painel leva à fila.
- **Migration:** `b16e2f3a4b50_mensagens_enviadas.py`: cria `mensagens_enviadas`. **Depois do pull, `flask db upgrade`.**
- **Testes:** `pytest` 422 de 422 (25 novos em `tests/test_mensagens.py`); migration num Postgres temporário, 18 checagens; navegador: mensagens 34 de 34 (sem sair para a internet) e as outras onze telas; varredura de rotas por papel sem mudança.
- **Observações:** a tela nunca diz que a fila "sai sozinha" (o envio automático não existe). Ficaram de fora: envio automático pela API oficial, filas de "sumido" e "boas-vindas", e o "Comprovante" da tela de pagamento.
- **Doc:** `docs/mudancas/back-16-mensagens.md`

## front-13-personal

- **Sai de:** `back-16-mensagens` · **PR:** a abrir → `back-16-mensagens` · **Data:** 12/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `personal/` (painel, pacotes, pacote_form, renovar, config, _pacotes_acabando, _ticket) e `agenda/` (index, detalhe, nova).
- **Testes:** os 10 arquivos conferidos byte a byte com o Drive.

## back-17-personal

- **Sai de:** `front-13-personal` · **PR:** a abrir → `front-13-personal` · **Data:** 12/10/2026
- **O que mudou:** a conta de personal trainer ganha o sistema dela. Pacotes de sessões no lugar de planos; saldo calculado (sessões compradas menos as concluídas que abateram), sem coluna de saldo; renovar soma o que sobrou (D12, como no front); pendente é quem tem cobrança em aberto; agenda com marcar, presença, remarcar, cancelar e repetição semanal; painel, configurações (CPF, CREF, locais), cobrança e fila de mensagens com o texto de pacote e de sessão. Tudo atrás de `pacote_service.e_personal()`: a conta de academia não muda.
- **Migration:** `b17f3a4b5c60_personal_pacotes_e_sessoes.py`: `planos.quantidade_sessoes`, `cobrancas.quantidade_sessoes`, `contas.cpf/cref/locais_ativos` e a tabela `sessoes`. Não toca em dado existente. **Depois do pull, `flask db upgrade`.**
- **Testes:** `pytest` 465 de 465 (43 novos em `tests/test_personal.py`); migration num Postgres temporário, 17 checagens; navegador: personal 55 de 55 e as doze telas da academia sem mudança; varredura de rotas por papel (conta de academia): só a agenda mudou.
- **Observações:** é a maior branch do projeto; começar a revisão pelo `pacote_service.py`. 5 ajustes marcados em `personal/painel.html`. Dez pontos para decidir no doc (D12, validade, falta, confirmação, grade de horários...).
- **Doc:** `docs/mudancas/back-17-personal.md`

## back-18-seguranca

- **Sai de:** `back-17-personal` · **PR:** a abrir → `back-17-personal` · **Data:** 12/10/2026
- **O que mudou:** limite de tentativas no login (por IP e por e-mail), em criar conta, em "esqueci a senha", nos links de convite e de senha e na tela antiga de login; cabeçalhos de segurança com regra de conteúdo (CSP) e, em produção, HTTPS obrigatório; sessão com prazo de 12 horas e "manter conectado" por 30 dias; a sessão cai ao trocar a senha e ao ser removido da equipe; o login responde igual para e-mail inexistente, senha errada e conta desativada; saem o popup de perfil e o botão de digital do login; envio limitado a 5 MB.
- **Migration:** não tem.
- **Dependências:** `Flask-Limiter==4.1.1` e `flask-talisman==1.1.0` (autorizadas, A6), mais `limits`, `Deprecated`, `ordered-set` e `wrapt`. **Depois do pull: `pip install -r requirements.txt`.**
- **Testes:** `pytest` 487 de 487 (22 novos em `tests/test_seguranca.py`); navegador: as 13 telas com a regra de conteúdo ligada e o console limpo; varredura de rotas por papel sem mudança.
- **Observações:** ao subir, **todos precisam entrar de novo uma vez**. O teste de navegador achou um recurso do front que a regra de conteúdo bloqueava (speculation rules); foi liberado com a palavra própria do CSP. Templates novos `errors/429.html` e `errors/413.html` (não vieram do Drive) e 3 ajustes marcados em `auth/login.html`.
- **Doc:** `docs/mudancas/back-18-seguranca.md`

## back-19-lgpd

- **Sai de:** `back-18-seguranca` · **PR:** a abrir → `back-18-seguranca` · **Data:** 13/10/2026
- **O que mudou:** termos de uso e política de privacidade publicados em `/termos` e `/privacidade` (lidos de `app/legal/*.md`, com aviso de versão preliminar); o aceite fica gravado ao criar a conta (versão e data); o cadastro do aluno ganhou "Aceita receber avisos pelo WhatsApp" e quem recusou sai da fila de mensagens; o dono baixa um arquivo com tudo o que o sistema guarda sobre um aluno; "Excluir aluno" passa a funcionar para quem tem histórico: apaga dados pessoais, avaliações, fichas, frequência e sessões, e mantém os pagamentos sem identificação. O aluno apagado some de todas as telas (`da_conta(Aluno)`).
- **Migration:** `b19a4b5c6d70_lgpd_aceites_e_anonimizacao.py`: `instrutores.termos_versao/termos_aceitos_em` e `alunos.aceita_whatsapp/anonimizado_em`. **Depois do pull, `flask db upgrade`.**
- **Testes:** `pytest` 502 de 502 (15 novos em `tests/test_lgpd.py`); migration num Postgres temporário, 14 checagens; navegador: LGPD 28 de 28 e as outras 13 telas; varredura de rotas por papel: só as rotas novas.
- **Observações:** os dois textos saíram de `docs/legal/` e foram para `app/legal/` (o sistema lê de lá); `docs/legal/LEIA-ME.md` foi reescrito. Cinco testes antigos ("aluno com histórico não pode ser excluído") passaram para a regra nova. Template novo `legal/pagina.html` (não veio do Drive) e um campo e um botão novos no front.
- **Doc:** `docs/mudancas/back-19-lgpd.md`

## back-20-producao

- **Sai de:** `back-19-lgpd` · **PR:** a abrir → `back-19-lgpd` · **Data:** 13/10/2026
- **O que mudou:** comando `flask banco-novo` (cria um banco vazio pelo `models.py`, marca a última versão das migrations e grava o catálogo de exercícios; recusa banco que já tem tabela); rota pública `/saude` (responde `ok` ou `banco fora do ar`); com `PROXIES_NA_FRENTE` o limite de tentativas enxerga o endereço de cada visitante; no servidor (Linux) o app assume o horário de Brasília; em produção só vale `DATABASE_URL`, e o formato `postgres://` é aceito; logs com data em produção; guia `docs/DEPLOY.md`.
- **Migration:** nenhuma. **Dependência nova:** nenhuma.
- **Testes:** `pytest` 512 de 512 (10 novos em `tests/test_producao.py`, entre eles a varredura "conta A × conta B" em todas as rotas); num Postgres temporário: `flask db upgrade` do zero para em `f456ba924031`, `flask banco-novo` cria 20 tabelas e `flask db check` passa; navegador: as 14 telas; varredura de rotas por papel: só a rota nova.
- **Observações:** checklist final de segurança feita aqui. `pip-audit` achou falhas conhecidas em 5 dependências (Werkzeug, Flask, idna, Mako, python-dotenv); nenhuma versão foi alterada, pede OK. **Defeito achado e corrigido na própria branch:** definir `TZ` no Windows adianta o relógio do Python em 3 horas; o ajuste de fuso ficou só para Linux e o `.env.example` avisa. A parte do teste de fuso que vale para Linux não roda no Windows. A branch mexe em configuração de produção: o Diogo confere no PR.
- **Doc:** `docs/mudancas/back-20-producao.md` e `docs/DEPLOY.md`

## Onde parou (13/10/2026)

**O roadmap acabou no que não depende de decisão.** Tudo enviado até a `back-20-producao`: todas as telas do front ligadas (menos a central de notificações e o painel do instrutor, que não estão em nenhuma branch), segurança (`back-18`), LGPD (`back-19`) e preparação de produção com a checklist final (`back-20`). Em 11/10/2026 o Diogo juntou na `main` (PR #23, `integracao-main`) tudo até a `front-05-cobranca` e a proposta de esquema da `back-09`, com um ajuste dele em `auth/routes.py`; **faltam os PRs de `back-09-cobranca` (o código) a `back-20-producao`**: 20 branches, na ordem, a primeira apontando para a `main` e cada uma das outras para a anterior. A junção da `back-20` com a `main` atual foi simulada: sem conflito, testes passando. O banco local do Adauto está em `b08c3d4e5f60`: **falta rodar `b09` a `b19`** e instalar as dependências da `back-18` (`pip install -r requirements.txt`): pedir o OK dele, backup antes, avisar da inatividade automática da `b12`. Enquanto isso a pasta do projeto fica em `back-08-planos`, que é onde o banco dele está.

O que falta, e de quem depende:

- **Adauto e Diogo:** hospedagem, domínio e e-mail (D4, D5, D6); servidor de aplicação (dependência nova); atualizar as 5 dependências do `pip-audit`; conferir a configuração de produção da `back-20`; remoção das telas antigas e do Flask-JWT-Extended sem uso; a migration antiga `f456ba924031`.
- **Adauto:** dados da empresa para os textos legais (D13) e o advogado; levar para o Drive os ajustes marcados nos templates (a lista está em cada `docs/mudancas/back-*.md`) e os templates que nasceram no repositório (`auth/nova_senha.html`, `errors/429.html`, `errors/413.html`, `legal/pagina.html`); as decisões de produto anotadas em cada doc (treinos: "Editar o modelo", "Duplicar ficha", "Salvar ficha" no desktop; avaliação: recepção vê medidas?, preço da avulsa, fotos, percentual de gordura; mensagens: envio automático pago, chave de lembretes, filas de sumido e boas-vindas; personal: D12, validade do pacote, falta, confirmação do aluno; LGPD: opção de WhatsApp começa ligada?, aceitar de novo na versão final).
- **Depois da hospedagem:** ambiente, backup com teste de restauração e ensaio geral no celular (`docs/DEPLOY.md`, seção 13).
- **Sem branch no roadmap:** central de notificações, painel do instrutor, PIX automático, ficha e avaliação em PDF.
