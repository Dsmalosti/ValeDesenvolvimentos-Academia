# back-22-ajustes-de-produto — três decisões do Adauto de 14/10/2026

| | |
|---|---|
| **Branch** | `back-22-ajustes-de-produto` |
| **Sai de** | `back-21-textos-legais` |
| **Data** | 14/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Decisões** | Respostas do Adauto à lista de pendências (14/10/2026): "inatividade automática ligada por padrão? **Não**"; "recepção pode ver as medidas da avaliação? **Pode**"; "aceita WhatsApp começa ligado ou desligado? **Desligado, mas aparece notificação**" |
| **Autorização usada** | A1 (Diogo, 10/10/2026): mudar o modelo e criar migration dentro da branch, para revisão no PR |
| **Tem migration** | **Sim:** `b22b5c6d7e80_inatividade_desligada_por_padrao.py` (só o valor padrão de uma coluna; nenhum dado muda) |
| **Dependência nova** | Não |

## Resumo

1. **Inatividade automática nasce desligada.** Conta nova não desativa aluno sozinha; o dono liga em Configurações se quiser.
2. **A recepção vê o resultado da avaliação física** (histórico, resultado e o resumo no perfil). Registrar continua só com dono e instrutor.
3. **WhatsApp só com autorização.** A caixa "Aceita receber avisos pelo WhatsApp" vem desmarcada; só entra na fila de Mensagens quem autorizou. Quem tem mensagem no dia e não autorizou aparece num aviso na tela de Mensagens, e o perfil do aluno também avisa.

## Arquivos

| Arquivo | O que mudou |
|---|---|
| `app/models.py` | `Conta.inatividade_ligada`: padrão `False` (era `True`) |
| `migrations/versions/b22b5c6d7e80_...py` | **Nova.** Troca o padrão da coluna no banco |
| `app/services/avaliacao_service.py` | Novo `PAPEIS_QUE_VEEM_O_RESULTADO` (a equipe toda) e `pode_ver_o_resultado()`; o resumo do perfil usa a regra nova |
| `app/blueprints/avaliacoes/routes.py` | Histórico e resultado sem a trava `so_quem_avalia`; a trava fica só em registrar, com aviso novo |
| `app/services/mensagem_service.py` | Só entra na fila quem tem `aceita_whatsapp` igual a sim; devolve também a lista de quem ficou de fora |
| `app/services/aluno_tela_service.py` | O perfil ganha `whatsapp_autorizado` |
| `app/templates/mensagens/index.html` | **Ajuste marcado:** aviso amarelo com os nomes de quem não autorizou (cada nome leva a Editar) |
| `app/templates/alunos/detalhe.html` | **Ajuste marcado:** aviso amarelo no perfil de quem não autorizou |
| `app/templates/alunos/_campos.html` | **Ajuste marcado:** a caixa só vem marcada para quem já autorizou; o texto de ajuda diz "Marque só se o aluno autorizou" |
| `tests/conftest.py` | `criar_aluno` ganhou `whatsapp=True` (os alunos de teste nascem autorizados, senão nem entrariam na fila) |
| `tests/test_avaliacoes.py`, `test_lgpd.py`, `test_mensagens.py`, `test_configuracoes.py` | Testes antigos atualizados para as regras novas (cada mudança tem o comentário `[back-22-ajustes-de-produto]`) |

## Cada mudança: antes, depois e por quê

### 1. Inatividade automática

- **Antes:** toda conta nascia com a regra ligada: na primeira vez que o painel abria no dia, quem estava vencido havia mais de 60 dias virava Inativo.
- **Agora:** nasce desligada. Quem quiser liga em Configurações → Funcionalidades → Inatividade automática (e escolhe os dias).
- **Contas que já existem não mudam.** A migration só troca o valor padrão. Nos bancos de desenvolvimento, as contas criadas antes continuam com a regra ligada; quem quiser desliga pela tela.
- **Por quê:** decisão do Adauto. Desativar aluno sozinho, sem o dono saber, surpreende.

### 2. Recepção vê o resultado da avaliação

- **Antes:** a recepção agendava, mas não abria o resultado nem o histórico, e no perfil do aluno via só a data da última avaliação.
- **Agora:** abre o histórico, o resultado e vê peso e IMC no perfil. Registrar uma avaliação continua só com dono e instrutor; a recepção que tenta é levada à agenda com o aviso "Só o dono e os instrutores registram a avaliação. Você pode agendar e ver os resultados."
- **LGPD:** medidas são dado de saúde. Os textos legais dizem que cada pessoa vê o que o papel dela permite, e isso continua verdade. O `docs/legal/LEIA-ME.md` é atualizado na branch de LGPD.

### 3. WhatsApp só com autorização

- **Antes:** a caixa vinha marcada e quem nunca tinha sido perguntado (campo vazio) entrava na fila de Mensagens. Só ficava de fora quem tinha recusado.
- **Agora:** a caixa vem desmarcada e só entra na fila quem autorizou (campo "sim"). Quem foi perguntado e recusou, ou nunca foi perguntado, fica de fora.
- **A notificação** que o Adauto pediu aparece em dois lugares:
  - **Mensagens:** "2 alunos ainda não autorizaram avisos pelo WhatsApp. Por isso ficaram fora da fila de hoje: Ana Souza, Bruno Dias. Pergunte se aceitam e marque no cadastro." Cada nome abre o cadastro do aluno.
  - **Perfil do aluno:** "Avisos pelo WhatsApp ainda não autorizados. Enquanto não autorizar, Ana não entra na fila de Mensagens. Pergunte e marque em Editar."
- **O botão "WhatsApp" do perfil e da lista continua funcionando** para qualquer aluno: é a pessoa da equipe abrindo uma conversa, não o sistema mandando aviso.
- **Por quê:** decisão do Adauto; também é o que a LGPD prefere (consentimento por ação, não marcado de fábrica).

## Templates para levar ao Drive

Os três ajustes estão marcados com `{# [back-22-ajustes-de-produto] ... #}` e usam variável opcional: no front do Drive, sem a variável, nada muda.

- `mensagens/index.html`: aviso de quem não autorizou.
- `alunos/detalhe.html`: aviso no perfil.
- `alunos/_campos.html`: a caixa começa desmarcada e o texto de ajuda muda.

## Como foi testado

- `pytest`: bateria inteira. Testes antigos atualizados para as regras novas, e casos novos: conta nasce com a regra desligada e ninguém é desativado; recepção abre histórico e resultado, mas não registra; aluno não perguntado e aluno que recusou ficam fora da fila, aparecem no aviso e o perfil avisa; depois de autorizar, entram na fila e o aviso some.
- Migration num Postgres temporário (criado e apagado pelo teste; nunca o banco do `.env`): 12 checagens. As contas que existiam não mudam; conta nova nasce desligada; `flask db check` bate; downgrade e upgrade de novo.
- Navegador (celular 390 px claro e desktop 1440 px escuro): LGPD, Mensagens, Avaliações, Alunos, Configurações e Painel.

## Como revisar

```bash
git fetch origin
git diff origin/back-21-textos-legais..origin/back-22-ajustes-de-produto -- app/ migrations/
```

Ordem sugerida: `mensagem_service.py` (a regra da fila), `avaliacoes/routes.py`, `models.py` e a migration.

## Riscos

- **A fila de Mensagens vai começar vazia** nas contas que já têm alunos: ninguém foi marcado como autorizado ainda. O aviso diz quem são. Para o piloto é o comportamento certo (nenhum dado real ainda).
- **Contas de desenvolvimento** continuam com a inatividade ligada (a migration não mexe nelas).
