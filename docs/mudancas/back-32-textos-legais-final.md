# back-32-textos-legais-final — Termos de Uso e Política de Privacidade, versão 1.0

| | |
|---|---|
| **Branch** | `back-32-textos-legais-final` |
| **Sai de** | `back-31-pdf-ficha-avaliacao` |
| **Data** | 17/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo e o advogado** |
| **Pedido** | Adauto, 17/10/2026: "termina os textos e finaliza como se já fosse postar com as informações que te dei para mostrar para o advogado" |
| **Tem migration** | Não |
| **Dependência nova** | Não |

## O que mudou

### Textos (`app/legal/`)

Versão **1.0, de 17/10/2026**, escrita como se já fosse publicada: sem o aviso de "versão preliminar" e sem nenhum trecho "a definir".

| Onde | O que entrou |
|---|---|
| Termos §1, Política (abertura) | O site: https://valesolucoestec.com.br (domínio registrado pelo Adauto no Registro.br) |
| Termos §3 | "Meu perfil": mudar nome, e-mail e senha (`back-30`); trocar a senha desconecta os outros aparelhos |
| Termos §4 | Tabela de preços (academia R$ 59,99, personal R$ 29,99, confirmados pelo Diogo) e a **promoção de lançamento**: 50% para as 10 primeiras contas, enquanto a conta continuar ativa; se o preço mudar, quem tem a promoção paga 50% do preço novo; conta cancelada ou apagada perde o desconto (`back-28`) |
| Termos §8 e §14, Política §7 e §9 | E-mails do domínio: **suporte@valesolucoestec.com.br** (sistema e assinatura) e **ouvidoria@valesolucoestec.com.br** (dados pessoais). Antes: o Gmail |
| Termos §11 | "Enquanto o serviço for gratuito" virou "Durante o teste grátis" (o serviço agora é pago depois do teste) |
| Política (abertura) | Encarregado: agente de pequeno porte, dispensado pela Resolução CD/ANPD nº 2/2022, com o canal `ouvidoria@` |
| Política §2.1 | A promoção entra nos dados da assinatura |
| Política §2.2 | Ficha e avaliação em PDF: montadas na hora, **não ficam guardadas** (`back-31`) |
| Política §4 | **Hospedagem: Render** (EUA) e **e-mail: Brevo** (União Europeia; recebe só nome, e-mail e o texto da mensagem, nenhum dado de aluno) |
| Política §4 | **Transferência internacional**: arts. 33 a 36 da LGPD, com garantias contratuais dos fornecedores |

### Sistema

| Arquivo | Mudança |
|---|---|
| `app/services/legal_service.py` | `VERSAO = '1.0-2026-10-17'` (antes `0.4-2026-10-14`). Quem criar conta daqui em diante fica com o aceite da 1.0 |
| `config.py` | `VALE_TEC_SUPORTE_EMAIL` padrão: `suporte@valesolucoestec.com.br` (antes o Gmail). É o e-mail das telas de assinatura e de conta bloqueada |
| `.env.example` | O mesmo e-mail no exemplo |
| `docs/legal/LEIA-ME.md` | Reescrito para a 1.0: histórico de versões, os dados, a tabela de promessas, os **10 pontos para o advogado** |

### PDF para o advogado

`instance/Textos-legais-Vale-Tec-v1.0.pdf`, com 12 páginas e fora do git:
- capa;
- os dois textos exatamente como o sistema mostra;
- na última página, os pontos para a revisão jurídica.

## Por quê

O Adauto escolheu o domínio, a hospedagem (Render) e o serviço de e-mail (Brevo), e o Diogo confirmou os preços. Com isso, não sobrou nada "a definir" nos textos. O advogado precisa ler a versão que vai ao ar.

## Como foi testado

- `pytest` inteiro: **556 passaram**.
  - `tests/test_lgpd.py`: as páginas públicas mostram "Versão 1.0", sem "preliminar", sem "a definir", sem o Gmail e com o e-mail de ouvidoria.
  - `tests/test_assinatura.py`: a tela de conta bloqueada mostra o suporte do domínio.
- Navegador: `lgpd_navegador.py` **28/28** (o link de "Criar conta" abre os termos 1.0, sem rolagem lateral) e `assinatura_navegador.py` **42/42**.
- O PDF dos textos foi aberto e conferido página por página: tabelas de preço e de dados, listas e a página dos pontos jurídicos.

## Como revisar

```bash
git fetch origin
git diff origin/back-31-pdf-ficha-avaliacao..origin/back-32-textos-legais-final -- app/legal/ config.py app/services/legal_service.py
```

## Riscos

- **As caixas `suporte@` e `ouvidoria@` ainda não existem.** O domínio foi registrado, mas o e-mail no domínio não. Até as caixas (ou um encaminhamento para o Gmail) existirem, quem escrever para elas não recebe resposta. **Precisa estar pronto antes do lançamento.** Está na lista. Opção sem custo: encaminhamento de e-mail grátis (ImprovMX, ou o Cloudflare Email Routing se o DNS for para a Cloudflare) para o `vale.informatica02@gmail.com`.
- **Os textos prometem cópia de segurança diária por 30 dias.** Isso só vale depois do deploy com o backup ligado (`docs/DEPLOY.md`).
- **A revisão do advogado pode mudar o texto.** Se mudar, troca-se a `VERSAO` de novo, antes do primeiro cliente.
