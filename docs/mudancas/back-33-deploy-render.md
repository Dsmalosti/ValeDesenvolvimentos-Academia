# back-33-deploy-render — passo a passo do deploy no Render, com Brevo, domínio e backup

| | |
|---|---|
| **Branch** | `back-33-deploy-render` |
| **Sai de** | `back-32-textos-legais-final` |
| **Data** | 17/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Decisões** | Adauto e Diogo, 17/10/2026: hospedagem **Render** ("o Diogo vai ver para aprender a mexer"), domínio **valesolucoestec.com.br** (Registro.br), e-mail **Brevo** no plano grátis |
| **Tem migration** | Não |
| **Dependência nova** | Não. O guia depende do **Gunicorn**, que ainda espera o OK do Diogo |
| **Código do sistema** | Não muda. Só documentação, um modelo de automação (desligado) e comentários no `.env.example` |

## O que mudou

| Arquivo | O que é |
|---|---|
| `docs/DEPLOY-RENDER.md` | **Novo.** Passo a passo para o Diogo:<br>• custos;<br>• conta e região;<br>• criar o Postgres e o Web Service (com os campos preenchidos);<br>• variáveis de ambiente;<br>• `banco-novo` e os dois admins;<br>• DNS no Registro.br (registro A e CNAME, HTTPS grátis);<br>• Brevo (domínio autenticado, chave SMTP);<br>• caixas `suporte@` e `ouvidoria@` por encaminhamento grátis;<br>• backup e teste de restauração;<br>• o `render.yaml` que entra com o Gunicorn;<br>• opções de ambiente de teste × produção;<br>• lista do primeiro deploy. |
| `docs/exemplos/backup-diario.yml` | **Novo, desligado.** Modelo de GitHub Actions: `pg_dump` diário do banco, criptografado (AES-256) e guardado por 30 dias. **Só roda com o repositório privado.** |
| `docs/DEPLOY.md` | Aponta para o guia do Render; a seção de backup cita a versão 1.0 dos termos. |
| `.env.example` | Comentário com os valores do Brevo (só nomes e formato, nenhuma senha). |

## Por quê

O Adauto e o Diogo escolheram Render e Brevo, e o Diogo vai aprender a mexer no Render. O guia junta, na ordem, tudo o que precisa ser clicado e preenchido, para o primeiro deploy não depender de lembrar de cabeça.

## Achado importante: o repositório é público

Conferido em 17/10/2026 (`api.github.com/repos/Dsmalosti/ValeDesenvolvimentos-Academia` responde `"visibility": "public"`).

- **Backup:** num repositório público, os arquivos guardados pelo GitHub Actions podem ser baixados por qualquer pessoa com conta no GitHub. Por isso o modelo de backup só roda com o repositório privado.
- **Código:** o código do sistema, que é o produto, fica aberto para cópia. Os termos dizem que "o sistema, a marca, as telas e o código são nossos".
- **Histórico:** o banco SQLite antigo de desenvolvimento (`instance/database.db`), tirado do git na `back-05`, continua no histórico público. Ele tem:
  - 2 usuários com e-mail do Gmail e a senha guardada como hash bcrypt;
  - 3 alunos de teste, com telefone de DDD 12.
- O `.env` **nunca** foi para o git (conferido com `git log --all -- .env`).

**Recomendação (decisão do Diogo, dono do repositório):**
1. Tornar o repositório privado.
2. Quem usou nesse banco antigo uma senha que também use em outro lugar deve trocá-la nesses outros lugares.
3. Tornar privado não apaga cópias que alguém já tenha feito, mas fecha o acesso daqui em diante.

## Como foi testado

- Os dois blocos YAML (`docs/exemplos/backup-diario.yml` e o `render.yaml` dentro do guia) foram lidos por um leitor de YAML, num ambiente descartável: estão bem formados.
- O formato do remetente `Vale Tec <nao-responda@valesolucoestec.com.br>` é aceito pelo envio de e-mail do sistema (`email.utils.getaddresses`).
- `tests/test_producao.py` e `tests/test_config.py` passando (nenhum código mudou).
- **O deploy em si não foi feito:** depende da conta no Render, do Gunicorn e dos acessos ao Registro.br e ao Brevo, que são de vocês.

## Como revisar

```bash
git fetch origin
git diff origin/back-32-textos-legais-final..origin/back-33-deploy-render --stat
```

## Riscos

- **Preços do Render:** vêm de comparações de 2026, não da página oficial. Conferir antes de contratar.
- **Endereço do registro A** (`216.24.57.1`): é o da documentação do Render. Usar o que a tela do Render mostrar na hora.
- **PITR de 3 dias no workspace Hobby:** sozinho, não cumpre os 30 dias prometidos. Por isso o backup diário externo é necessário.
