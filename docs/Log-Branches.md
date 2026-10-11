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

- **Sai de:** `docs-01-decisoes-e-termos` · **PR:** a abrir → `docs-01-decisoes-e-termos` · **Data:** 10/10/2026
- **O que mudou:** só templates. Cópia fiel do Drive de `base.html`, `_cabecalho.html`, `_gaveta.html`, `_rodape.html`, `_digital.html`, `errors/` e `painel/` (index e os dois arquivos de popups). O `base.html` antigo foi renomeado para `base_antigo.html` e as 19 telas antigas passaram a herdar dele (só a linha `extends` mudou).
- **Testes:** os 12 arquivos novos conferidos byte a byte com o Drive; smoke de rotas idêntico ao da `back-03`; `pytest` 30 de 30.
- **Observações:** sozinha não muda nada para quem usa. O Adauto pediu esta branch em 10/10 para testar o front no código real.

## back-04-painel

- **Sai de:** `front-02-painel` · **PR:** a abrir → `front-02-painel` · **Data:** 10/10/2026
- **O que mudou:** depois do login abre o painel novo, com números do banco (alunos, planos, pagamentos) e só da conta logada. `context_processor` com `usuario` e `academia`. Blueprint `painel`; seções sem backend respondem "em construção" (`app/blueprints/pendentes.py`); pontes temporárias dos nomes de rota do front para as telas antigas de alunos, planos, exercícios e fichas; páginas de erro 403/404/500 do front. A rota inicial antiga (`main.homepage`) virou atalho para o painel.
- **Testes:** `pytest` 49 de 49 (19 novos em `tests/test_painel.py`); navegador com Playwright: painel 66 de 66 e login 60 de 60 (celular de 390 px com toque e desktop de 1440 px, claro e escuro); smoke sem mudança de status nas rotas que já existiam.
- **Observações:** `academia` ("Minha academia") e o papel do usuário são provisórios até existir a tabela de contas. O template `painel/index.html` do repositório tem 6 ajustes que o do Drive não tem (lista no doc). O front tem botões de demonstração que não fazem nada de verdade.
- **Doc:** `docs/mudancas/back-04-painel.md`

## back-05-repo-e-config

- **Sai de:** `back-04-painel` · **PR:** a abrir → `back-04-painel` · **Data:** 10/10/2026
- **O que mudou:** 102 `.pyc` e o `instance/database.db` saíram do git (continuam no disco); `mysql-connector==2.2.9` saiu do `requirements.txt` e entrou o `requirements-dev.txt`; `DATABASE_URL` é o nome único da variável do banco (o antigo `DATABASE_URI` ainda funciona, com aviso no log); `SECRET_KEY` sem valor padrão no `config.py`.
- **Testes:** `pytest` 55 de 55 (6 novos em `tests/test_config.py`); `pip install -r requirements.txt` e `-r requirements-dev.txt` num ambiente virtual novo, em Python 3.13, sem erro.
- **Observações:** cada pessoa precisa renomear `DATABASE_URI` para `DATABASE_URL` no próprio `.env`. Quem trocar para uma branch antiga volta a ver os `.pyc` versionados.
- **Doc:** `docs/mudancas/back-05-repo-e-config.md`

## Onde parou (10/10/2026)

O Diogo respondeu tudo em 10/10: todas as autorizações foram dadas, e as respostas estão na seção "O que está parado esperando o Adauto" do `docs/ROADMAP-LANCAMENTO.md`. A próxima branch é a **`back-06-contas-e-papeis`** (tabela `contas`, `conta_id` nas tabelas de negócio, coluna `papel`, e-mail e CPF únicos por conta, exercício com dono, fechar o cadastro aberto). Não há nada travando ela. Depois vem alunos (`front-03-alunos` + `back-07-alunos`). Do Adauto e do Diogo faltam só hospedagem, domínio e provedor de e-mail (D4, D5, D6), e do Adauto D12 e D13.
