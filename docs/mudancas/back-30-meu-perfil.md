# back-30-meu-perfil — cada pessoa edita o próprio nome, e-mail e senha

| | |
|---|---|
| **Branch** | `back-30-meu-perfil` |
| **Sai de** | `back-29-dependencias` |
| **Data** | 17/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Decisão** | Adauto, 17/10/2026: "Meu perfil (cada pessoa editar o próprio nome e e-mail) não existe nas telas novas. Precisa para o lançamento? — sim" |
| **Tem migration** | Não (usa as colunas que já existem: `nome`, `sobrenome`, `email`, `senha`) |
| **Dependência nova** | Não |

## O que mudou

Tela nova **Meu perfil** (`/perfil`), para todos os papéis (dono, recepção, instrutor) e para o personal trainer.

| Bloco | O que faz | Pede a senha atual? |
|---|---|---|
| Seus dados | Nome, sobrenome e e-mail de login | Só se o **e-mail** mudar |
| Trocar a senha | Senha atual e nova senha, com o botão de mostrar a senha e o medidor de força que o front já tinha | Sim |

**Regras** (em `app/services/perfil_service.py`):

- **Trocar o e-mail pede a senha atual.** O e-mail é o login: assim, quem pega um celular desbloqueado não troca o login de outra pessoa.
- **E-mail já usado** por outra pessoa, **e-mail inválido** e **nome vazio**: recusados, com a mensagem no campo.
- **Senha nova**: mesma regra do cadastro (pelo menos 8 caracteres) e diferente da atual.
- **Depois de trocar a senha:**
  - **este aparelho continua logado**: a rota faz o login de novo, com a "marca" da senha nova;
  - **os outros aparelhos saem**: a sessão deles tem a marca da senha antiga (regra da `back-18`).
- **Admin dentro da conta de um cliente** (`/admin` → "Entrar na conta como o dono"): vê a tela com os campos desligados e um aviso; o servidor recusa as mudanças. O admin não troca o login nem a senha do dono.
- **Limite de tentativas**: 10 envios por hora em cada formulário, contra quem tenta adivinhar a senha atual.
- O formulário só mexe em quem está logado (`current_user`). Um `id` forjado no envio não tem efeito, e há teste para isso.

**Menu:**

- Item novo **Meu perfil** (ícone de pessoa) na barra lateral do desktop, logo acima de Configurações.
- Item novo na gaveta do celular, nas duas variantes (academia e personal).

## Como era antes

- As telas novas não tinham onde editar o próprio cadastro. A tela antiga `/instrutores/editar/<id>` fazia isso e saiu na `back-27`.
- A senha só se trocava pelo "esqueci a senha", por e-mail.

## Arquivos

| Arquivo | Mudança |
|---|---|
| `app/services/perfil_service.py` | **Novo.** `salvar_dados()`, `trocar_senha()` e `valores_da_tela()` |
| `app/blueprints/perfil/routes.py` | **Novo.** `perfil.index`, `perfil.dados` e `perfil.senha` |
| `app/__init__.py` | Registra o blueprint (comentado com `[back-30-meu-perfil]`) |
| `app/templates/perfil/index.html` | **Novo, NÃO veio do Drive.** Montado com as peças do front (card, campo, `field-icon` com o olho, `data-forca`, note). Adauto: revise o visual e leve para o front |
| `app/templates/_cabecalho.html`, `app/templates/_gaveta.html` | Item "Meu perfil" no menu (**levar para o Drive**) |
| `tests/test_perfil.py` | **Novo.** 12 testes |
| `tests/navegador/perfil_navegador.py` | **Novo.** Celular e desktop |

## Como foi testado

- `pytest` inteiro: **544 passaram** (ambiente com as dependências da `back-29`).
- `tests/test_perfil.py` (12 testes):
  - os três papéis e o personal abrem o próprio perfil;
  - sem login, a tela pede login;
  - troca de nome sem senha;
  - troca de e-mail: sem senha, com senha errada e com senha certa (e o login novo funciona);
  - e-mail de outra pessoa, e-mail inválido e nome vazio são recusados;
  - um `id` forjado no formulário não mexe em outra pessoa;
  - trocar a senha mantém este aparelho e derruba o outro;
  - senha atual errada, senha nova curta e senha nova igual à atual são recusadas;
  - o admin dentro da conta não muda nada.
- Navegador (`perfil_navegador.py`): **26/26**, no celular (390 px, toque, claro) e no desktop (1440 px, escuro):
  - o link do menu abre a tela;
  - os campos vêm preenchidos e os botões têm tamanho de toque;
  - trocar o nome funciona;
  - com a senha errada, o erro aparece no campo certo;
  - o olho e o medidor de força funcionam;
  - depois de trocar a senha, continua logado e entra de novo com a senha nova;
  - sem rolagem lateral e com o console limpo.
- Os testes de navegador de login, painel, equipe, personal e configurações também rodaram, porque o menu mudou.
- Varredura de rotas por papel: a única diferença para a branch anterior é a rota nova `/perfil` (200 nos três papéis).

## Como revisar

```bash
git fetch origin
git diff origin/back-29-dependencias..origin/back-30-meu-perfil --stat
git diff origin/back-29-dependencias..origin/back-30-meu-perfil -- app/services/perfil_service.py app/blueprints/perfil/
```

## Riscos

- **Trocar o e-mail errado** (ex.: erro de digitação) faz a pessoa perder o login. Para recuperar, o dono ou o suporte ajudam; o "esqueci a senha" vai para o e-mail novo, já digitado errado. A tela avisa que o e-mail é o login, e a troca exige a senha.
- **O e-mail novo não é confirmado por link.** Fazer a confirmação depende do envio de e-mail funcionar em produção (Brevo). Fica como melhoria depois do deploy.
