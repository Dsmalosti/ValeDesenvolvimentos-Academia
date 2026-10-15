# back-19-lgpd — termos publicados, aceite registrado e os direitos do aluno

| | |
|---|---|
| **Branch** | `back-19-lgpd` |
| **Sai de** | `back-18-seguranca` |
| **Data** | 13/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Tarefa** | 3.9 da lista "Tarefas do backend — Diogo": LGPD |
| **Decisões usadas** | **D15** (Adauto, 12/10/2026): "criar e finalizar a LGPD e deixar no sistema funcionando; depois vejo com o advogado". D7 (os textos são rascunho do Claude). A1 (migration na branch) |
| **Tem migration** | **Sim:** `migrations/versions/b19a4b5c6d70_lgpd_aceites_e_anonimizacao.py`. Quatro colunas novas, todas aceitando vazio. |
| **Dependência nova** | **Nenhuma.** |

## Resumo

A LGPD passa a funcionar dentro do sistema:

1. **Termos de Uso e Política de Privacidade publicados**, em `/termos` e `/privacidade`, abertos a qualquer pessoa. Os links da tela "Criar conta", que não levavam a lugar nenhum, agora abrem os textos.
2. **O aceite fica gravado:** quem cria a conta fica com a versão dos textos e a data no cadastro.
3. **A vontade do aluno sobre o WhatsApp** entra no cadastro. Quem recusou não aparece na fila de mensagens.
4. **Exportar os dados de um aluno:** o dono baixa um arquivo com tudo o que o sistema guarda sobre ele.
5. **Apagar os dados de um aluno:** "Excluir aluno" agora funciona para quem tem histórico. Apaga os dados pessoais e de saúde; os pagamentos ficam, sem nada que identifique a pessoa.

**Os textos continuam sendo rascunho** e aparecem com o aviso "Versão preliminar, ainda em revisão". O que falta para a versão final está em `docs/legal/LEIA-ME.md`, reescrito nesta branch.

## Arquivos

| Arquivo | O que é |
|---|---|
| `app/legal/termos-de-uso.md`, `app/legal/politica-de-privacidade.md` | Os dois textos. **Vieram de `docs/legal/`** (movidos com `git mv`) porque o sistema passou a lê-los. Ajustados ao que o sistema faz hoje (seção 1). |
| `app/services/legal_service.py` | **Novo.** Lê o texto e transforma em página. A `VERSAO` dos textos fica aqui. |
| `app/blueprints/legal/` | **Novo.** As rotas `/termos` e `/privacidade`. |
| `app/templates/legal/pagina.html` | **Novo, e não veio do Drive** (seção 6). |
| `app/services/lgpd_service.py` | **Novo.** Exportar e apagar os dados de um aluno. |
| `app/models.py` | `User.termos_versao`, `termos_aceitos_em`; `Aluno.aceita_whatsapp`, `anonimizado_em`. |
| `migrations/versions/b19a4b5c6d70_lgpd_aceites_e_anonimizacao.py` | **Novo.** A migration. |
| `app/helpers/conta.py` | `da_conta(Aluno)` deixa de fora quem teve os dados apagados. |
| `app/services/acesso_service.py` | Criar conta grava o aceite. |
| `app/services/aluno_tela_service.py` | O cadastro lê e grava `aceita_whatsapp`; o perfil sabe se quem está logado é o dono. |
| `app/services/mensagem_service.py` | Quem recusou o WhatsApp não entra na fila. |
| `app/blueprints/alunos/routes.py` | Rota nova `alunos.dados`; `alunos.excluir` apaga os dados de quem tem histórico. |
| `app/__init__.py` | Registra o blueprint `legal`. |
| `app/templates/auth/criar_conta.html`, `alunos/_campos.html`, `alunos/detalhe.html` | **Ajustes marcados** (seção 6). |
| `docs/legal/LEIA-ME.md` | Reescrito: onde editar os textos, o que falta preencher, o que o texto promete e o sistema já cumpre. |
| `tests/test_lgpd.py` | **Novo.** 15 testes. |
| `tests/test_alunos.py`, `test_cobrancas.py`, `test_frequencia.py`, `test_avaliacoes.py`, `test_personal.py` | Um teste de cada mudou de regra (seção 5). |
| `tests/navegador/lgpd_navegador.py` | **Novo.** Teste no navegador, celular e computador. |

## Cada mudança: antes, depois e por quê

### 1. Termos e política publicados

- `/termos` e `/privacidade` são **públicos** (sem login): quem ainda vai criar a conta precisa conseguir ler.
- Os textos ficam em **Markdown**, em `app/legal/`, para o Adauto e o advogado editarem sem mexer em código. Não foi usada biblioteca de Markdown (seria dependência nova): o `legal_service` entende só o que os dois textos usam (títulos, parágrafos, listas, tabelas, negrito, link).
- **Todo o texto é escapado antes de virar HTML.** Um `<script>` escrito no arquivo aparece como texto, e link que não seja `https://` ou para o outro documento vira só o texto. Tem teste.
- Os trechos `` `[PREENCHER: ...]` `` (o que só o Adauto sabe: razão social, CNPJ, e-mails) aparecem na página como **"a definir"**.
- **O que mudou no conteúdo dos textos**, para bater com o sistema de hoje:
  - o aviso do topo deixou de dizer "rascunho, ainda não vale" e passou a "versão preliminar 0.2, ainda em revisão";
  - cookie de sessão: "até 12 horas sem uso" (era "até fechar o navegador"); "lembrar de mim": 30 dias (estava por preencher);
  - a lista de dados do aluno ganhou as sessões do personal, a vontade sobre o WhatsApp e o registro de mensagem preparada;
  - "aluno excluído pela academia" agora descreve o que acontece de fato (seção 5).

### 2. Aceite ao criar a conta

Antes: a tela dizia "ao criar a conta você aceita os termos" e nada ficava gravado.

Agora `acesso_service.criar_conta` grava `termos_versao` (a `VERSAO` do `legal_service`, hoje `0.2-2026-10-13`) e `termos_aceitos_em`. **Sempre que um dos textos mudar, a `VERSAO` precisa mudar junto.**

- Contas criadas antes desta branch ficam com os dois campos vazios.
- Quem entra por **convite** não tem aceite: o contrato é com o dono da conta.

### 3. O aluno aceita receber avisos pelo WhatsApp?

`alunos.aceita_whatsapp`: sim, não, ou vazio (ainda não foi perguntado).

- O cadastro do aluno ganhou um interruptor, logo abaixo de "Observações". **Vem ligado**; a academia desliga se o aluno pedir para não receber.
- **Quem recusou não entra na fila de Mensagens** (nem aniversário, nem lembrete, nem cobrança), e a linha dele também não pode ser marcada como enviada.
- Aluno que já existia fica "ainda não perguntado" e continua na fila, como antes.

### 4. Exportar os dados de um aluno

`GET /alunos/<id>/dados` (`alunos.dados`), **só o dono**. Devolve um arquivo JSON com: cadastro, cobranças e pagamentos, entradas, fichas de treino com os exercícios, avaliações físicas (com a anamnese), avaliações marcadas, sessões e os registros de mensagem.

- O arquivo é para a academia entregar ao aluno que pedir (direito de acesso e de portabilidade).
- Vai com `Cache-Control: no-store`, para o navegador não guardar cópia.
- Recepção e instrutor recebem 403; outra academia, 404.

### 5. Apagar os dados de um aluno ("Excluir aluno")

**Antes:** aluno com pagamento, entrada, avaliação ou sessão **não podia ser excluído** ("desative em vez de excluir"). Ou seja: a academia não tinha como atender um pedido de exclusão de dados.

**Agora**, no mesmo botão "Excluir aluno" (só o dono, só por POST, com o popup de confirmação):

| O aluno… | O que acontece |
|---|---|
| não tem histórico | A linha é apagada inteira, como sempre foi. |
| tem histórico | **Apagados de vez:** avaliações físicas (feitas e marcadas), fichas de treino, entradas, sessões e registros de mensagem. **Anonimizado:** o cadastro perde nome, e-mail, telefone, CPF, nascimento e observações. **Mantidos:** cobranças e pagamentos, sem nada que identifique a pessoa (a observação do pagamento, que é texto livre, também é apagada). |

Por que os pagamentos ficam: o faturamento do mês e os extratos da academia não podem mudar por causa de um pedido de exclusão, e registro financeiro tem prazo legal de guarda. É por isso que a linha do aluno continua existindo: os pagamentos apontam para ela.

**O aluno apagado some de todas as telas.** A mudança está num lugar só: `da_conta(Aluno)`, por onde toda tela busca aluno, passou a deixar de fora quem tem `anonimizado_em`. Lista, busca, painel, mensagens e relatórios de alunos deixam de vê-lo, e o endereço do perfil responde 404. CPF e e-mail ficam livres para um cadastro novo.

**Não dá para desfazer.** O popup de confirmação passou a dizer o que é apagado e o que fica.

Cinco testes antigos conferiam a regra anterior ("não pode ser excluído") e foram trocados pela nova, cada um com o comentário `[back-19-lgpd]`.

### 6. Templates

**Novo, sem origem no Drive:** `legal/pagina.html`. Usa a base das telas públicas e alarga a coluna, porque o texto é longo. **Adauto: revise o visual e leve para o front.**

**Ajustes marcados com `{# [back-19-lgpd] ... #}`:**

| Arquivo | Ajuste |
|---|---|
| `auth/criar_conta.html` | Os links de termos e de política apontam para as páginas de verdade (abrem em outra aba). |
| `alunos/_campos.html` | **Campo novo**, que o front não tinha: o interruptor "Aceita receber avisos pelo WhatsApp", com as mesmas peças dos outros formulários. |
| `alunos/detalhe.html` | **Botão novo** na "Zona de risco": "Baixar os dados deste aluno (LGPD)", só para o dono. |
| `alunos/detalhe.html` | O texto do popup "Excluir cadastro?" diz o que é apagado e que os pagamentos ficam sem o nome. |

## A migration

`b19a4b5c6d70_lgpd_aceites_e_anonimizacao.py`, depois da `b17f3a4b5c60` (a `back-18` não teve migration). Acrescenta `instrutores.termos_versao`, `instrutores.termos_aceitos_em`, `alunos.aceita_whatsapp` e `alunos.anonimizado_em`. Não toca em dado existente. O downgrade remove as quatro colunas; dados já apagados não voltam.

## Como foi testado

- **`pytest`: 502 de 502** (15 novos em `tests/test_lgpd.py`): páginas públicas sem login, com o aviso, sem Markdown cru e com "a definir"; um texto aponta para o outro e a política traz os prazos reais; o leitor de Markdown não deixa passar código; criar conta mostra os links e grava a versão; conta antiga e convite sem aceite; cadastro grava o WhatsApp (sim, não, formulário antigo); quem recusou sai da fila; exportar traz tudo e nada da equipe; só o dono exporta; excluir com histórico apaga, anonimiza e mantém o financeiro (com o faturamento do mês igual antes e depois); sem histórico apaga a linha; só o dono apaga; CPF e e-mail ficam livres; o código não imprime nem registra dado pessoal.
- **Migration num Postgres temporário** (criado e apagado pelo teste): **14 checagens**.
- **Navegador (Playwright):** LGPD **28 de 28**, celular (390 px, toque, claro) e computador (1440 px, escuro): termos e política a partir de "Criar conta", sem login, com as tabelas dentro da tela; o interruptor do WhatsApp gravando; o botão de baixar os dados; excluir com o popup novo, a aluna sumindo da lista e o perfil virando 404. As outras 13 telas foram rodadas de novo, sem falha.
- **Varredura de rotas por papel**, comparada com a `back-18-seguranca`: só entraram as rotas desta branch.

## Revisão de segurança (skill `saas-flask-seguranca`, seção 9 e as que a branch toca)

| Item | Como está | Evidência |
|---|---|---|
| Exportar e excluir dados do aluno a pedido | Feito; excluir é anonimização com o financeiro preservado | `test_dono_baixa_tudo...`, `test_excluir_aluno_com_historico_apaga_os_dados_e_mantem_o_financeiro` |
| Só o dono, só na própria conta | 403 para recepção e instrutor; 404 para outra academia; excluir só por POST | `test_so_o_dono_exporta_e_so_da_propria_academia`, `test_so_o_dono_apaga_e_outra_academia_nao_alcanca` |
| Logs sem CPF, senha ou token | Um teste varre o código: sem `print()` e sem linha de log com esses campos | `test_o_codigo_nao_imprime_nem_registra_dado_pessoal` |
| Coletar só o necessário | Nenhum dado novo do aluno além da vontade sobre o WhatsApp | — |
| Texto de arquivo virando HTML | Tudo escapado; só `https://` e link interno viram link | `test_o_leitor_de_markdown_nao_deixa_passar_codigo` |
| Página pública nova | Sem formulário e sem dado de conta; leva os mesmos cabeçalhos de segurança | `test_termos_e_politica_sao_paginas_publicas` |
| Arquivo com dado sensível | `no-store`; nome do arquivo só com o id | `test_dono_baixa_tudo...` |

## Como revisar

```bash
git fetch origin
git diff origin/back-18-seguranca..origin/back-19-lgpd --stat
git diff origin/back-18-seguranca..origin/back-19-lgpd -- app/ migrations/ ':!app/legal'
git diff -M origin/back-18-seguranca..origin/back-19-lgpd -- app/legal docs/legal
```

Ordem sugerida: `lgpd_service.py` (o texto do começo explica o que é apagado e o que fica); `helpers/conta.py` (`da_conta`); `alunos/routes.py` (`excluir` e `dados`); `legal_service.py`.

## Para decidir (Adauto, Diogo e o advogado)

1. **Os textos.** Preencher o que está "a definir" (D13: razão social, CNPJ, cidade, e-mails, suporte; D4 e D6: hospedagem e e-mail) e passar pelo advogado. Lista completa em `docs/legal/LEIA-ME.md`.
2. **A opção de WhatsApp vem ligada.** Para mensagem com oferta, o advogado pode pedir que comece desligada.
3. **Contas antigas e a versão final dos termos.** Quando a versão final sair, decidir se quem já tem conta precisa aceitar de novo. O sistema ainda não pede.
4. **Excluir a conta inteira** (a academia sair do Vale Tec) e **exportar tudo de uma vez** não existem como tela. Hoje seria feito à mão, a pedido. O texto promete 30 dias para exportar depois do cancelamento.
5. **Registros de acesso (IP, data e hora) por 6 meses** e **cópia de segurança diária**: são do ambiente de produção (Fase D), não do código.
6. **O arquivo de exportação é JSON**, que é o formato de portabilidade. Se a academia quiser algo para imprimir e entregar ao aluno, seria um PDF (biblioteca nova).

## Riscos

- **Apagar é definitivo.** Depois do "Excluir aluno" não há como recuperar avaliações, fichas e frequência. O popup avisa.
- **O aluno apagado continua como uma linha no banco** ("Aluno removido"), ligada aos pagamentos. Não é "apagar tudo": é o que a política de privacidade descreve.
- **Cópias de segurança antigas** ainda terão os dados até saírem do ciclo (o texto fala em 30 dias; depende de como o backup for montado na Fase D).
- **A mudança em `da_conta(Aluno)` vale para o sistema inteiro.** É o que garante que o aluno apagado some de tudo, e por isso passou pela suíte completa.
