# Vale Tec — integração do front com o backend

Este arquivo fica na raiz do repositório e é lido sozinho pelo Claude Code em toda sessão.
Ele diz COMO trabalhar. O QUE fazer está em `docs/ROADMAP-LANCAMENTO.md`, que é a fonte de verdade do progresso.

## Quem é quem

- **Adauto** (dono do projeto, júnior): implementa front e backend com o Claude e faz a manutenção depois. Explique o que está fazendo e por quê: ele está aprendendo.
- **Diogo** (dono do backend): revisa cada branch e aprova o merge. Nada vai pra `main` sem o OK dele.

## Onde estão as coisas

| O quê | Caminho |
|---|---|
| Repositório (backend + front integrado) | `C:\Users\Adauto Netto\Documents\GitHub\ValeDesenvolvimentos-Academia` (este) |
| Front pronto (mock, fonte do design) | `G:\Meu Drive\Adauto Netto\MEI\vale informatica\Saas Academia\vale-tec-front` (SÓ LEITURA: copiar daqui, nunca editar lá) |
| Branches já prontas (login) | `branches-front-01-back-01.bundle` na pasta `Saas Academia` do Drive |
| Docs de referência | `docs/` no repo; os docs do projeto no claude.ai (PRD, TRD, Esquema-Backend, Integracao-Front-Back, Tarefas do backend — Diogo) |

O front do Drive roda com `_dev/app.py` (mock). Os templates e o `static/` dele são a referência de design: copiar fiel, sem "melhorar" o visual.

## Regras de trabalho (obrigatórias)

1. **Uma tela ou um assunto por branch.** Nomes: `front-NN-<tela>` (só front) e `back-NN-<assunto>` (mexe no backend). Cada branch sai da anterior e vira um PR para o Diogo, na ordem.
2. **Só passa pra próxima quando a atual está 100%**: testes passando, smoke de rotas igual ou melhor que a `main`, doc escrito, commit feito, push feito.
3. **Toda branch que mexe no backend** leva `docs/mudancas/<branch>.md` com: o que mudou, por quê, como era antes, como foi testado, como revisar (`git diff`), e riscos. Toda linha alterada no backend leva o comentário `# [<branch>] ...` explicando o que era antes.
4. **Pare e pergunte ao Adauto antes de**: adicionar ou remover dependência (`requirements.txt`), criar ou rodar migration, mudar modelo do banco, apagar arquivo do Diogo, mexer em config de produção ou segredo. Explique em português simples o que muda e o risco.
5. **Nunca**: dar push na `main`, usar `--force` em branch que já está no GitHub, commitar `.env`, senha ou token, commitar `.pyc` ou `__pycache__`.
6. **Código limpo e comentado** em português: o Adauto mantém depois.
7. **Contrato front ↔ back** (Integracao-Front-Back.md): endpoints com os nomes que o template chama em `url_for`; `name` dos campos = colunas do banco; categorias de flash `success|error|warning|info`; `context_processor` com `usuario`, `academia`, `csrf_token`.
8. **Ao terminar cada branch**, atualize `docs/ROADMAP-LANCAMENTO.md` (marque o item, anote o PR) e `docs/Log-Branches.md`. É assim que a próxima sessão sabe onde parou.

## Skills (usar sempre)

- `saas-qa-release`: antes de dar push em qualquer branch com tela. Varredura de rotas por perfil, Playwright no celular (390px, toque) e no PC (1440px), tema claro e escuro, console limpo. A seção 6 dela (entrega pelo Drive) NÃO vale aqui: aqui a entrega é branch + PR.
- `saas-flask-seguranca`: em toda branch `back-*` e na revisão final antes do lançamento (isolamento entre academias, papéis, CSRF, rate limit, headers, segredos, LGPD).
- `saas-interacoes-mobile`: quando a tela tiver popup, gaveta, arrastar, linha clicável ou transição.
Se uma skill não estiver disponível, avise o Adauto em vez de seguir sem ela.

## Testes

- Rodar Python com `PYTHONDONTWRITEBYTECODE=1` (o repo versiona `.pyc`; sem isso aparecem alterações falsas).
- Banco de teste: SQLite descartável. Nunca o banco real.
- Cada branch: teste do fluxo da tela (servidor + Playwright) e smoke de todas as rotas GET logado, comparado com a `main`.
- iPhone: os popups dependem de `static/css/ajustes-iphone.css` e `static/js/ajustes-iphone.js` (ver `Correcao-iPhone-08-10.md`). Não remover.

## Formato do resumo ao fim de cada branch

Mande ao Adauto: nome da branch, link do PR, o que mudou (3 a 5 linhas), resultado dos testes, o que precisa de decisão dele ou do Diogo. Sem jargão desnecessário.
