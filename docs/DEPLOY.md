# Vale Tec — como colocar no ar (deploy)

Guia para subir o sistema num servidor de verdade e para atualizar depois. Escrito na `back-20-producao`.

**O que este guia não decide:** onde hospedar (D4), o domínio (D5) e o e-mail (D6). Ele diz o que o sistema precisa, seja qual for a hospedagem escolhida. Os comandos de exemplo são de Linux, que é o que as hospedagens usam.

> **[back-33-deploy-render] Decidido em 17/10/2026:** hospedagem **Render**, domínio **valesolucoestec.com.br** (Registro.br) e e-mail **Brevo**. O passo a passo no Render está em `docs/DEPLOY-RENDER.md`; este arquivo continua valendo para o que não depende da hospedagem.

## 1. O que o servidor precisa ter

| Item | Detalhe |
|---|---|
| Python | 3.13 (a versão usada no desenvolvimento e nos testes) |
| Banco | PostgreSQL. Testado no 18. Um banco **vazio**, só do Vale Tec |
| HTTPS | Obrigatório. Em produção o sistema redireciona tudo para HTTPS e os cookies de login só andam por HTTPS |
| Servidor de aplicação | Um servidor WSGI (ver seção 5). **Não** usar `flask run` em produção |
| Disco | Nenhum arquivo é gravado em disco pelo sistema hoje (não há upload). Tudo fica no banco |

## 2. Variáveis de ambiente

Em produção as variáveis são definidas **no painel da hospedagem**, não num arquivo `.env` dentro do servidor. Nenhum valor de verdade vai para o git.

| Variável | Obrigatória | O que é |
|---|---|---|
| `FLASK_CONFIG` | **Sim** | Tem de ser `production`. Liga o HTTPS obrigatório, os cookies seguros e desliga o modo de depuração. Sem ela o sistema sobe em modo de desenvolvimento |
| `SECRET_KEY` | **Sim** | Chave que assina os cookies de login. Texto longo e aleatório, **diferente** da chave usada no computador de quem desenvolve. Para gerar uma: `python -c "import secrets; print(secrets.token_hex(32))"`. Trocar essa chave derruba todas as sessões |
| `DATABASE_URL` | **Sim** | Endereço do Postgres. Formato: `postgresql://usuario:senha@servidor:5432/banco`. O formato `postgres://...`, que algumas hospedagens entregam, também é aceito. Em produção o nome antigo (`DATABASE_URI`) **não** vale |
| `PROXIES_NA_FRENTE` | **Sim, quase sempre** | Quantos proxies ficam entre a internet e o app. Na maioria das hospedagens é `1`. Ver seção 6 |
| `RATELIMIT_STORAGE_URI` | Só com mais de um processo | Onde ficam os contadores do limite de tentativas. Vazia = memória do processo. Ver seção 7 |
| `SMTP_HOST`, `SMTP_PORTA`, `SMTP_USUARIO`, `SMTP_SENHA`, `EMAIL_REMETENTE` | Não | Envio de e-mail (convite da equipe e troca de senha). Sem elas o sistema funciona: o convite tem o botão de copiar o link e o suporte gera o link de senha com `flask link-de-senha` |
| `TZ` | Não | Fuso horário. Sem ela o servidor usa o horário de Brasília. Ver seção 8 |

Se `SECRET_KEY` ou `DATABASE_URL` faltarem, o sistema **se recusa a subir** e diz qual faltou. É de propósito.

## 3. Primeira vez: criar o banco

Com as variáveis definidas e as dependências instaladas (`pip install -r requirements.txt`):

```bash
flask --app main banco-novo
```

O comando cria todas as tabelas, marca o banco na versão mais nova e grava o catálogo padrão de exercícios (64). Ele **só roda em banco vazio**: se encontrar qualquer tabela, para e não mexe em nada.

**Por que não `flask db upgrade` na primeira vez:** num Postgres vazio ele para na segunda migration antiga (`f456ba924031`), que muda o tipo da coluna `treino.repeticoes` de um jeito que o Postgres recusa. Conferido num Postgres de teste em 13/10/2026. Num banco novo não há o que migrar: o caminho certo é criar tudo de uma vez e marcar a versão, que é o que o `banco-novo` faz.

Depois, criar a primeira conta pela tela `/criar-conta`, ou pelo terminal:

```bash
flask --app main criar-conta
```

## 4. Atualizações (toda versão nova)

1. **Backup do banco antes.** Sempre. Exemplo: `pg_dump "$DATABASE_URL" > backup-AAAAMMDD-HHMM.sql`.
2. Baixar o código novo e instalar as dependências: `pip install -r requirements.txt`.
3. Aplicar as mudanças de banco:
   ```bash
   flask --app main db upgrade
   ```
4. Reiniciar o servidor de aplicação.
5. Conferir `https://<domínio>/saude` (tem de responder `ok`) e entrar no sistema.

Para saber em que versão o banco está: `flask --app main db current`.

## 5. Servidor de aplicação

O ponto de entrada é o objeto `app` do arquivo `main.py` (`main:app`).

O `requirements.txt` **ainda não tem** um servidor WSGI de produção (Gunicorn, Waitress ou outro): incluir um é dependência nova, que pede o OK do Adauto e do Diogo, e a escolha depende da hospedagem (D4). Algumas hospedagens já trazem o delas.

Exemplo com Gunicorn, depois de autorizado e incluído no `requirements.txt`:

```bash
gunicorn --workers 1 --threads 8 --bind 0.0.0.0:$PORT main:app
```

**Por que um processo só (`--workers 1`) no começo:** os contadores do limite de tentativas ficam na memória de cada processo (seção 7). Um processo com várias threads atende com folga as primeiras academias.

## 6. Proxy e HTTPS

Na hospedagem, quem recebe o HTTPS é um proxy, que repassa o pedido ao app. Sem avisar o sistema, todos os visitantes parecem vir do endereço do proxy, e **uma pessoa errando a senha bloquearia o login de todo mundo**.

- Definir `PROXIES_NA_FRENTE=1` (ou o número certo de proxies da hospedagem).
- **Não** definir no computador de quem desenvolve nem num servidor sem proxy: aí qualquer visitante poderia inventar o próprio endereço e escapar do limite.
- **Como conferir no ensaio geral:** de dois aparelhos em redes diferentes (um no Wi-Fi, outro no 4G), errar a senha 11 vezes num deles. Só esse tem de ser barrado ("Muitas tentativas"); o outro continua entrando.

## 7. Limite de tentativas com mais de um processo

Com `RATELIMIT_STORAGE_URI` vazia, cada processo conta as tentativas sozinho. Com um processo, o limite é exato. Com N processos, o limite real fica até N vezes maior, e os contadores zeram quando o servidor reinicia. Para ter mais de um processo com o limite exato, apontar a variável para um Redis (`redis://servidor:6379`) e instalar o pacote `redis`, que também é dependência nova.

## 8. Fuso horário

O sistema decide "hoje" pelo relógio do servidor: vencimento, aniversariantes, agenda, fila de mensagens do dia, hora do pagamento. Servidor de hospedagem costuma estar em UTC, 3 horas à frente de Brasília.

- **No servidor (Linux):** o sistema já assume o horário de Brasília ao subir. Só definir `TZ` para escolher outro fuso.
- **No Windows (computador de quem desenvolve):** **não** definir `TZ`. O Windows não entende `America/Sao_Paulo` e o Python passa a marcar 3 horas a mais. Ali vale o relógio do próprio computador; se o sistema encontrar a variável, avisa no log.
- **Conferir no ensaio geral:** confirmar um pagamento e ver se a hora mostrada é a do relógio da parede.

## 9. Monitor: `/saude`

`GET /saude` responde `ok` (código 200) quando o app está de pé e o banco aceita uma consulta, e `banco fora do ar` (código 503) quando o banco não responde. É pública, não mostra nenhum dado e é a única rota que aceita HTTP sem redirecionar, porque o monitor da hospedagem costuma chamar o app por dentro da rede dela. Apontar o "health check" da hospedagem para ela.

## 10. Backup

Os termos de uso (versão 1.0) prometem backup **diário, guardado por 30 dias**. O sistema não faz backup sozinho: no Render, ver `docs/DEPLOY-RENDER.md`, seção 8 (recuperação do Render + cópia diária guardada por 30 dias).

- Ligar o backup automático diário do Postgres e conferir o prazo de guarda.
- **Testar a restauração uma vez antes de entrar o primeiro cliente**: restaurar o backup num banco separado e abrir o sistema apontando para ele. Backup que nunca foi restaurado não conta.

## 11. Registros (logs)

Em produção os avisos e erros saem na saída do processo, com data e origem, que é onde a hospedagem recolhe. O sistema não escreve CPF, telefone, senha nem link de troca de senha no log.

## 12. Antes de cada deploy

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

Procura falhas de segurança conhecidas nas dependências. É uma ferramenta de conferência, não entra no `requirements.txt`.

Também vale lembrar:

- Quem estava logado antes da `back-18-seguranca` entra de novo uma vez.
- Depois da primeira subida, fazer o **ensaio geral** do roadmap: criar conta → cadastrar aluno → matricular → cobrar → registrar entrada → fechar o mês, no iPhone e no Android de verdade.

## 13. Lista rápida do primeiro deploy

- [ ] Banco Postgres vazio criado, com backup diário ligado
- [ ] `FLASK_CONFIG=production`, `SECRET_KEY` nova, `DATABASE_URL`, `PROXIES_NA_FRENTE` definidas no painel da hospedagem
- [ ] `pip install -r requirements.txt` e `pip-audit` sem achado grave
- [ ] `flask --app main banco-novo`
- [ ] Servidor WSGI apontando para `main:app`, um processo
- [ ] Domínio com HTTPS; `http://` redireciona para `https://`
- [ ] `/saude` responde `ok`; monitor da hospedagem apontado para ela
- [ ] Primeira conta criada; hora do sistema conferida
- [ ] Limite de tentativas conferido de duas redes (seção 6)
- [ ] Restauração do backup testada
- [ ] Ensaio geral feito no celular
