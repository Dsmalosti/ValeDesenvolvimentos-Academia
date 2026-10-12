# back-14-treinos — catálogo de exercícios e fichas de treino

| | |
|---|---|
| **Branch** | `back-14-treinos` |
| **Sai de** | `front-10-treinos` (que só traz os 9 templates, copiados do Drive) |
| **Data** | 12/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefa** | 5.5 da lista "Tarefas do backend — Diogo": exercícios e fichas de treino |
| **Decisões usadas** | A1 (migration na branch, só rodada em banco de teste); D14 (mensagem gratuita: o sistema monta o texto e abre o WhatsApp de quem está usando) |
| **Tem migration** | **Sim:** `migrations/versions/b14c0d1e2f30_treinos_e_catalogo_padrao.py`. Só **acrescenta colunas** em 4 tabelas que já existiam e grava o catálogo padrão de exercícios. |
| **Dependência nova** | **Nenhuma.** |

## Resumo

As telas de exercícios e de ficha de treino do front novo passam a funcionar de verdade:

- **Catálogo de exercícios** (`/exercicios`): 64 exercícios padrão que toda academia já encontra prontos, mais os que a própria academia criar. Busca, filtro por grupo muscular, "carregar mais", detalhe, novo e editar.
- **Modelos prontos** (`/treinos`): 5 fichas-modelo (hipertrofia, perda de peso, condicionamento, baixo impacto, iniciante), as mesmas do front.
- **Usar um modelo com um aluno**: marca um ou vários alunos e a ficha é copiada para cada um, em rascunho.
- **Editor da ficha** (`/alunos/<id>/ficha`): treinos por letra (A a E), ajustar séries, repetições, carga e descanso, adicionar exercício pelo catálogo, tirar, criar treino, salvar e excluir.
- **Enviar pelo WhatsApp** (`/alunos/<id>/ficha/enviar`): o sistema monta a mensagem com a ficha inteira e o botão abre o WhatsApp de quem está usando, já na conversa do aluno e com o texto pronto. **Não custa nada e o sistema não envia nada sozinho** (D14).

Dono, recepção e instrutor usam tudo isso: ficha de treino não é dinheiro.

As telas antigas (`/exercicios/listar/`, `/fichas/...`) **continuam no ar**, sem alteração. Só não são mais o destino dos menus do layout novo.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/dados_padrao.py` | **Novo.** Só dados: os 64 exercícios padrão, os 5 modelos de ficha, os músculos de cada grupo e o texto padrão de "como executar". Para mudar um modelo, é aqui. |
| `app/services/treino_service.py` | **Novo.** Todas as regras: catálogo, modelos, ficha, texto do envio. |
| `app/blueprints/treinos/` | **Novo.** As 10 rotas de fichas (lista abaixo). |
| `app/blueprints/exercicios/routes.py` | 4 rotas novas no fim do arquivo (`lista`, `detalhe`, `novo`, `editar`). As rotas antigas, em cima, não mudaram. |
| `app/models.py` | Colunas novas em `Exercicio`, `Ficha`, `Treino` e `TreinoExercicio` (seção 1). |
| `migrations/versions/b14c0d1e2f30_treinos_e_catalogo_padrao.py` | **Novo.** A migration. |
| `app/blueprints/pendentes.py` | Saíram as duas últimas pontes para tela antiga (`treinos.biblioteca` e `treinos.ficha_aluno`): `PONTES` ficou vazia. |
| `app/__init__.py` | Registra o blueprint `treinos`. |
| `app/cli.py` | Comando novo `flask semear-catalogo` (grava o catálogo padrão; pode rodar de novo, não duplica). |
| `app/services/aluno_tela_service.py` | O cartão "Ficha de treino" do perfil do aluno passa a ler a ficha em uso pelo `treino_service`. |
| `app/templates/treinos/enviar.html` | **3 ajustes marcados** (seção 6). |
| `tests/test_treinos.py` | **Novo.** 36 testes. |
| `tests/conftest.py`, `tests/test_painel.py`, `tests/test_alunos.py` | Ajudante `semear_catalogo()`; os testes das duas pontes viraram testes das telas de verdade. |
| `tests/navegador/treinos_navegador.py` | **Novo.** Teste no navegador, celular e computador. |
| `tests/navegador/painel_navegador.py` | 1 checagem trocada: `/exercicios` agora abre o catálogo novo (antes conferia a ponte). |

## Cada mudança: antes, depois e por quê

### 1. Banco

As quatro tabelas já existiam (são do Diogo). Nada foi renomeado nem apagado; só entraram colunas, todas aceitando vazio ou com valor padrão:

| Tabela | Coluna nova | Para quê |
|---|---|---|
| `exercicio` | `equipamento` | Campo do formulário do front ("Barra", "Halteres"...). |
| `ficha` | `objetivo` | Texto curto que aparece no topo da ficha. |
| `ficha` | `rascunho` (padrão: não) | A ficha nasce rascunho quando vem de um modelo; "Salvar ficha" tira. |
| `ficha` | `modelo` | De qual modelo ela nasceu (para o "Usado N×" da biblioteca). |
| `ficha` | `valida_ate` | Hoje + 90 dias ao criar. |
| `ficha` | `atualizada_em`, `atualizada_por_id` | "Atualizada em 12/10 por Marina". |
| `treino` | `letra`, `nome` | A tela nova organiza por letra (A a E) e nome ("Peito e costas"). Antes era só `dia_semana`, que continua lá. |
| `treino_exercicio` | `descanso`, `ordem` (padrão 0) | Descanso entre séries e a posição da linha no treino. |

**A ficha em uso de um aluno é a ativa mais recente.** Dar uma ficha nova a quem já tem **não apaga a antiga**: ela fica inativa, guardada.

### 2. Rotas

| Endereço | Endpoint | Antes |
|---|---|---|
| `GET /exercicios` | `exercicios.lista` | ponte para `/exercicios/listar/` |
| `GET /exercicios/<id>` | `exercicios.detalhe` | não existia |
| `GET, POST /exercicios/novo` | `exercicios.novo` | não existia |
| `GET, POST /exercicios/<id>/editar` | `exercicios.editar` | não existia |
| `GET /treinos` | `treinos.biblioteca` | ponte para a lista antiga de fichas |
| `GET /treinos/modelo/<id>` | `treinos.modelo` | não existia |
| `GET, POST /treinos/modelo/<id>/atribuir` | `treinos.atribuir` | não existia |
| `GET /alunos/<id>/ficha` | `treinos.ficha_aluno` | ponte para a tela antiga de fichas |
| `POST /alunos/<id>/ficha` | `treinos.ficha_salvar` | não existia |
| `POST /alunos/<id>/ficha/exercicio` | `treinos.ex_salvar` (`acao` = adicionar, editar ou remover) | não existia |
| `POST /alunos/<id>/ficha/treino` | `treinos.treino_novo` | não existia |
| `POST /alunos/<id>/ficha/excluir` | `treinos.ficha_excluir` | não existia |
| `GET /alunos/<id>/ficha/enviar` | `treinos.enviar` | não existia |
| `GET /alunos/<id>/ficha/baixar` | `treinos.baixar` | não existia |

Todas exigem login. Nenhuma tela aberta por GET grava nada no banco (tem teste).

### 3. Catálogo de exercícios

- **Catálogo padrão** = exercícios sem dono (`conta_id` vazio). Toda academia vê e usa; **ninguém edita**. Quem tenta editar um deles recebe o aviso "é do catálogo padrão, crie um exercício seu" e volta ao detalhe. Isso resolve o achado da `back-06` (os botões de editar da tela antiga davam 404 sem explicar).
- **Exercício da academia** = criado por ela. Só ela vê, usa e edita. Exercício de outra academia responde 404.
- Formulário: nome (obrigatório, até 100 letras), grupo muscular (um dos 7 da lista), equipamento e link do vídeo. **O link só é aceito se começar com `http://` ou `https://`.** Na hora de mostrar, a mesma regra vale para o que já estava gravado: link fora desse formato aparece como "sem vídeo".
- A tela antiga grava o grupo como código (`peito`, `ombro`). A tela nova **traduz para mostrar** ("Peito", "Ombros"), sem mexer no banco, para o exercício antigo entrar no filtro certo.
- O banco não guarda a duração do vídeo nem os músculos trabalhados. A duração aparece como "vídeo"; os músculos vêm de uma tabela fixa por grupo (`MUSCULOS_DO_GRUPO`); "como executar" usa a `descricao` do exercício e, se estiver vazia, um texto padrão.

### 4. Modelos e ficha do aluno

- Os 5 modelos ficam no código (`app/dados_padrao.py`), iguais para todas as academias. **Não são editáveis pela tela** (ver "Para decidir").
- **Usar com um aluno:** só alunos ativos da própria conta. Aluno de outra academia ou inativo, mesmo que o id seja enviado na mão, é ignorado. Um aluno marcado: vai para o editor (ou para "enviar", conforme o botão). Vários: volta à biblioteca com o aviso.
- **Editor:** cada ação é um envio de formulário e grava na hora (não há "rascunho de edição" no navegador).
  - Adicionar: entra no fim do treino aberto, com 3 × 12 e 60s de descanso.
  - Ajustar: séries de 1 a 20; repetições de 1 a 100; carga e descanso são texto livre curto.
  - Treinos: até 5 (A a E). O sexto é recusado com aviso.
  - Excluir: pede confirmação num popup, só por POST, e apaga a ficha com seus treinos. O catálogo e os modelos não são afetados.
- **Fichas criadas na tela antiga** funcionam na nova: os treinos ganham letra pela ordem em que foram criados. Ficha antiga sem nenhum treino abre com um "Treino A" vazio, que só é criado no banco quando o primeiro exercício entra.
- Aluno sem ficha: o botão "Visualizar ficha" do perfil leva à biblioteca, com o aviso para escolher um modelo.

### 5. Enviar a ficha (D14: gratuito)

O sistema **não manda mensagem**. Ele monta o texto (saudação, a ficha inteira, assinatura com o nome da academia) e um endereço `https://wa.me/55<telefone>?text=<texto>`. Quem está usando toca em "Abrir no WhatsApp", o aplicativo abre na conversa do aluno com tudo escrito, e a pessoa toca em enviar. Funciona no celular e no WhatsApp Web, sem API paga e sem cadastro em lugar nenhum.

- O código do país é colocado olhando o **tamanho** do número (DDD + número), e não "se começa com 55": 55 também é DDD (Santa Maria/RS).
- Treino criado e ainda vazio não entra no texto. Ficha sem nenhum exercício não abre a tela de envio (avisa e volta ao editor).
- Aluno sem telefone: o botão abre o WhatsApp para a pessoa escolher o contato.
- **Imagem e PDF não existem ainda** (seção 6 e "Para decidir"). "Baixar" devolve a ficha em arquivo de texto.
- O sistema não registra "enviada em": ele não tem como saber se a pessoa tocou em enviar no WhatsApp.

### 6. Templates

Os 9 templates vieram do Drive na `front-10-treinos`, sem alteração. Nesta branch, **só `treinos/enviar.html` mudou**, com 3 ajustes marcados com `{# [back-14-treinos] ... #}`, todos ligados à variável `so_texto`:

1. Os botões "Imagem" e "PDF" ficam desabilitados.
2. "Texto" já vem escolhido (e a prévia mostra o bloco de texto).
3. O botão de baixar diz "Baixar a ficha em texto" em vez de "Baixar as imagens".

Sem a variável, a tela se comporta como no Drive. **Adauto: leve os 3 para o front.**

## A migration

`b14c0d1e2f30_treinos_e_catalogo_padrao.py`, depois da `b13b9c0d1e20`.

- Acrescenta as colunas da seção 1 (com `batch_alter_table`, como as anteriores).
- **Treinos que já existem** ganham letra pela ordem de criação dentro de cada ficha (1º = A ... 5º = E). Do 6º em diante ficam sem letra: continuam no banco e na tela antiga, só não aparecem na nova.
- **Linhas de treino que já existem** ganham `ordem` pela ordem de criação.
- **Catálogo padrão:** insere os exercícios da lista que ainda não existirem **com o mesmo nome** (sem diferenciar maiúsculas). Os que já existem não são renomeados nem têm o grupo trocado; só recebem o equipamento se estava vazio. Exercício de academia com nome igual não é tocado.
- **Downgrade:** remove as colunas. Os exercícios acrescentados **ficam** (fichas já podem estar usando).

A lista de exercícios é importada de `app/dados_padrao.py`, o mesmo arquivo que o sistema usa. É dado, não código de regra; se a lista mudar no futuro, bancos migrados antes recebem o que faltar com `flask semear-catalogo`.

## Como foi testado

- **`pytest`: 352 de 352** (36 novos em `tests/test_treinos.py`): catálogo gravado uma vez só; lista, busca, filtro e "carregar mais"; detalhe; criar e editar; 5 formulários inválidos; catálogo padrão e exercício de outra academia não editáveis; exercício da tela antiga na tela nova; biblioteca e tela do modelo; atribuir a um, a vários, a ninguém, a inativo e a aluno de outra academia; ficha nova guarda a antiga; editor (adicionar, ajustar, tirar); 10 pedidos inválidos que não mudam nada; até 5 treinos; salvar e excluir; GET não grava; fichas antigas sem letra e sem treino; texto e link do envio; DDD 55; ficha vazia; os três papéis; 404 em todas as rotas para aluno de outra academia.
- **Migration num Postgres temporário** (criado e apagado pelo teste; nunca o banco do `.env`): **25 checagens**. Sobe, confere colunas, letras, ordem, catálogo sem repetição, `flask db check`, desce, confere que o banco volta a bater com a branch anterior, sobe de novo sem duplicar.
- **Navegador (Playwright):** treinos **79 de 79**, celular (390 px, toque, claro) e computador (1440 px, escuro): todo o fluxo acima pela tela, popups de ajustar, catálogo e excluir, sem "None", sem rolagem lateral, console limpo, nenhum 404. As outras telas foram rodadas de novo, sem mudança: login 60 de 60, painel 74 de 74, alunos 32 de 32, planos 31 de 31, cobrança 33 de 33, frequência 31 de 31, relatórios 28 de 28, configurações 29 de 29, equipe 34 de 34.
- **Varredura de rotas por papel**, comparada com a `front-10-treinos`: só mudou o que é desta branch.

## Revisão de segurança (skill `saas-flask-seguranca`)

| Item | Como está | Evidência |
|---|---|---|
| Isolamento entre academias | Toda rota de ficha busca o aluno com `da_conta(Aluno)`; exercício com `exercicios_visiveis()` / `exercicios_proprios()`. Outra conta: 404 | `test_ficha_de_aluno_de_outra_academia_da_404` (7 rotas), `test_catalogo_padrao_e_exercicio_de_outra_academia_nao_sao_editados`, `test_atribuir_a_varios_a_ninguem_e_a_quem_nao_pode` |
| Id enviado na mão | Exercício de outra academia não entra na ficha; aluno de fora não recebe ficha; posição que não existe não apaga nada | `test_pedido_invalido_na_ficha_nao_muda_nada` (10 casos) |
| Papéis | Os três papéis usam as fichas (decisão do documento de acesso: treino não é dinheiro) | `test_os_tres_papeis_usam_as_fichas` |
| CSRF | Todo formulário manda `csrf_token`; tudo que grava é POST; excluir é só POST | `test_salvar_tira_do_rascunho_e_excluir_apaga_so_a_ficha` (GET dá 405) |
| GET não grava | Abrir qualquer tela não muda o banco (nem cria o "Treino A" vazio) | `test_abrir_telas_nao_grava_nada` |
| Link clicável vindo do usuário | `video_url` só `http(s)`, ao gravar **e** ao mostrar | `test_exercicio_invalido_avisa_e_nao_grava`, `test_exercicio_criado_na_tela_antiga_aparece_certo_na_nova` |
| Texto do usuário na tela | Tudo passa pelo escape automático do Jinja; a mensagem do WhatsApp vai codificada no endereço (`quote`) | `test_enviar_monta_o_texto_e_abre_o_whatsapp_de_quem_usa` |
| Arquivo para baixar | Nome do arquivo usa só o id do aluno (nada digitado pelo usuário no cabeçalho) | `treinos.baixar` |
| Dados pessoais | A mensagem leva só o primeiro nome do aluno e a ficha. O telefone vai no endereço do WhatsApp, que abre no aparelho de quem usa; nada é enviado a terceiros pelo servidor | — |

## Como revisar

```bash
git fetch origin
git diff origin/front-10-treinos..origin/back-14-treinos --stat
git diff origin/front-10-treinos..origin/back-14-treinos -- app/ migrations/
```

Ordem sugerida: `models.py` e a migration; `dados_padrao.py` (só passar o olho: é dado); `treino_service.py` (o texto do começo explica as regras); `treinos/routes.py`; o fim de `exercicios/routes.py`.

## Para decidir (Adauto e Diogo)

1. **Ficha em imagem e em PDF.** O front promete os dois; o servidor só faz texto. Gerar imagem ou PDF pede biblioteca nova (regra 4). Sugestão: depois do lançamento.
2. **"Editar o modelo" e "Duplicar ficha".** No front os dois botões só mostram um aviso ("entra junto com o backend"). Não implementei: modelo editável por academia pede tabela nova. Hoje o caminho é usar o modelo com o aluno e ajustar a ficha dele. Decidir: implementar depois ou tirar os botões do front.
3. **No computador não existe o botão "Salvar ficha"** (só no celular). Como cada ajuste já grava na hora, nada se perde, mas a etiqueta "rascunho" só sai pelo celular. É do front: falta o botão no cabeçalho do desktop.
4. **Telas antigas de exercício e de ficha** (`/exercicios/listar/`, `/fichas/...`) continuam no ar e não foram tocadas. `/fichas/editar/<id>` segue com o erro 500 que já tinha. Diogo: quando aprovar as novas, dá para remover as antigas (apagar arquivo seu é decisão sua).
5. **Excluir exercício da academia:** a tela nova não tem esse botão (a antiga tem). Se fizer falta, é pequeno.
6. Detalhes de texto do front, para o Adauto ver: "Ela não precisa instalar nada" e "Prévia do que ela recebe" estão no feminino para qualquer aluno; a hora "14:32" na bolha é fixa; a prancha nos modelos está como "3 × 1" (igual ao front).

## Riscos

- **A migration grava dados** (64 exercícios no catálogo padrão). É segura para rodar de novo e não mexe no que existe, mas quem já tinha exercícios padrão com nomes parecidos e não iguais ("Supino" e "Supino reto") fica com os dois.
- **Treinos antigos do 6º em diante** de uma mesma ficha não aparecem na tela nova (ficam só na antiga).
- **O texto do WhatsApp fica longo** em ficha grande (vai inteiro no endereço). Testado com ficha de 4 treinos; fichas muito maiores podem passar do limite de endereço de algum navegador. Imagem/PDF resolveria.
- **Modelos e catálogo padrão são iguais para todas as academias** e só mudam com alteração no código.
