# back-27-telas-antigas — remoção das telas do layout antigo

| | |
|---|---|
| **Branch** | `back-27-telas-antigas` |
| **Sai de** | `back-26-lgpd-final` |
| **Data** | 14/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Autorização** | Regra 4 do `CLAUDE.md` ("apagar arquivo do Diogo"): o Adauto respondeu **"Podem"** em 14/10/2026 à pergunta "as telas antigas podem sair? Duas dão erro 500" |
| **Tem migration** | Não. Nenhuma tabela muda: os dados das telas antigas são os mesmos das novas |
| **Dependência nova** | Não |

## Resumo

As telas do layout antigo (o primeiro front do Diogo, com Bootstrap) já tinham sido todas substituídas pelas telas novas, mas continuavam no código, abertas por endereço direto. Duas davam **erro 500** (`/instrutores/painel/` e `/fichas/editar/<id>`). Esta branch tira tudo isso: **50 arquivos, cerca de 2.300 linhas a menos**, sem tirar nenhuma função de quem usa o sistema.

## O que saiu

| O quê | Endereços que deixam de existir | Substituído por |
|---|---|---|
| Blueprint `main` (`app/routes.py`) | `/inicio-antigo/` | Painel (`/`) |
| Blueprint `instrutores` (rotas, formulários e 4 templates) | `/instrutores/login/`, `/sair/`, `/cadastro/`, `/painel/` (dava 500), `/lista/`, `/editar/<id>`, `/excluir/<id>` | Login novo (`/login`), Criar conta, Configurações → Equipe (convite, papel, remover) |
| Blueprint `fichas` (rotas, formulários e 5 templates) | `/fichas/...` (lista, novo, detalhes, editar (dava 500), excluir, treinos) | Fichas novas (`/treinos`, `/alunos/<id>/ficha`) |
| Blueprint `pagamentos` (rotas, formulário e 3 templates) | `/pagamentos/registrar/<id>`, `/listar/<id>`, `/situacao/` (já só redirecionavam desde a `back-09`) | Cobrança e extrato novos |
| Rotas antigas de alunos, com formulário e 2 templates | `/alunos/cadastro/`, `/listar/`, `/editar/<id>`, `/excluir/<id>`, `/status/<id>` | `/alunos`, `/alunos/novo`, `/alunos/<id>/editar` etc. |
| Rotas antigas de exercícios, com formulário e 2 templates | `/exercicios/criar/`, `/listar/`, `/editar/<id>`, `/excluir/<id>` | `/exercicios`, `/exercicios/novo`, `/exercicios/<id>/editar` |
| Rotas antigas de planos, com formulário e 2 templates | `/planos/criar/`, `/listar/`, `/editar/<id>/`, `/excluir/<id>` | `/planos`, `/planos/novo`, `/planos/<id>/editar` |
| Templates gerais antigos | `base_antigo.html`, `index.html`, `aluno.html`, `administracao.html`, `cabecalho.html`, `rodape.html`, `notificacao.html` | `base.html` e as telas novas |
| CSS antigo | `administracao.css`, `cabecalho.css`, `notificacao.css`, `painel-adm.css`, `reset.css`, `rodape.css`, `style.css` | `tokens.css` e `app.css` |
| Serviços que só as telas antigas usavam | `dashboard_service.py`, `exercicio_service.py`, `instrutor_service.py`, `pagamento_service.py`, `plano_service.py` | Os serviços das telas novas |

**Ficaram** (as telas novas ainda usam): `aluno_service.py` (excluir aluno), `auth_service.py` (login), os modelos e todas as tabelas.

## Mudanças em arquivos que ficaram

- `app/__init__.py`: não registra mais os quatro blueprints antigos (comentado com `[back-27-telas-antigas]`).
- `app/blueprints/alunos/routes.py`, `exercicios/routes.py`, `planos/routes.py`: as funções antigas saíram; os imports que só elas usavam também; os comentários que diziam "as rotas antigas continuam funcionando" foram trocados.
- `app/extensions/protecao.py`: **a regra de conteúdo (CSP) não libera mais o `cdn.jsdelivr.net`**. Só as telas antigas carregavam o Bootstrap de lá. Agora o sistema não carrega nada de fora: um site a menos em que é preciso confiar.

## Testes que mudaram

Testes que usavam as telas antigas passaram para as telas novas quando a regra continua valendo; os que testavam código que sumiu saíram:

| Arquivo | O que mudou |
|---|---|
| `tests/test_contas.py` | Papéis (instrutor não cadastra, recepção pode, só o dono exclui) e isolamento passaram para as rotas novas. Saíram os testes da gestão da equipe antiga e do exercício antigo, que já têm equivalentes em `test_equipe.py`, `test_treinos.py` e `test_alunos.py` |
| `tests/test_isolamento.py` | As tentativas com id de outra conta passaram para as rotas novas (perfil, editar, extrato, renovar, dados, ficha, planos); listas, cadastro e "envio forjado com o plano de outra conta" também |
| `tests/test_cobrancas.py` | As telas antigas de pagamento agora respondem 404 |
| `tests/test_seguranca.py` | O limite de tentativas da tela antiga de login saiu junto com ela (o endereço responde 404) |
| `tests/test_limpeza.py` | Saíram 3 testes de defeitos das telas antigas |
| `tests/test_login.py`, `tests/test_painel.py`, `tests/navegador/login_navegador.py` | Endereços antigos trocados pelos novos |

## Como foi testado

- `pytest`: bateria inteira.
- Navegador (celular e desktop): login, alunos, planos, treinos, painel e equipe.
- Varredura de rotas por papel: as rotas antigas somem da lista; nenhuma rota nova muda; os dois erros 500 que existiam desde a `main` acabam.

## Como revisar

```bash
git fetch origin
git diff origin/back-26-lgpd-final..origin/back-27-telas-antigas --stat
git diff origin/back-26-lgpd-final..origin/back-27-telas-antigas -- app/__init__.py app/extensions app/blueprints/alunos/routes.py app/blueprints/exercicios/routes.py app/blueprints/planos/routes.py
```

## Riscos

- **Link guardado de uma tela antiga** (favorito no navegador de alguém) passa a dar "página não encontrada". Ninguém usa o sistema em produção ainda.
- **Editar o próprio nome e e-mail**: a tela antiga `/instrutores/editar/<id>` deixava cada pessoa da equipe editar o próprio cadastro. As telas novas não têm "meu perfil" (a senha se troca por "esqueci a senha"). Fica anotado como pendência do front.
