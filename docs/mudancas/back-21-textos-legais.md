# back-21-textos-legais — dados da empresa nos termos de uso e na política de privacidade

| | |
|---|---|
| **Branch** | `back-21-textos-legais` |
| **Sai de** | `back-20-producao` |
| **Data** | 13/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Decisão que fecha** | **D13** (dados de quem oferece o Vale Tec), respondida pelo Adauto em 13/10/2026 |
| **Tem migration** | **Não.** |
| **Dependência nova** | **Não.** |

## Resumo

Os dois textos publicados em `/termos` e `/privacidade` tinham trechos "a definir" no lugar dos dados de quem oferece o sistema. O Adauto passou os dados e eles entraram nos textos:

| Dado | Valor |
|---|---|
| Razão social | 60.499.733 ADAUTO RODRIGUES DOS SANTOS NETTO |
| CNPJ | 60.499.733/0001-44 |
| Sede e foro | Tremembé/SP |
| E-mail de contato, de suporte e de assuntos de dados | vale.informatica02@gmail.com |
| Data da última atualização | 13/10/2026 |

Os textos continuam com o aviso de **versão preliminar** (agora 0.3): ainda falta a revisão do advogado.

## Arquivos

| Arquivo | O que mudou |
|---|---|
| `app/legal/termos-de-uso.md` | 8 trechos preenchidos. **Não sobra nenhum "a definir".** O aviso do topo deixou de falar em trechos a definir |
| `app/legal/politica-de-privacidade.md` | 5 trechos preenchidos. Ficam 3 "a definir", todos da hospedagem e do serviço de e-mail (D4 e D6) |
| `app/services/legal_service.py` | `VERSAO` de `0.2-2026-10-13` para `0.3-2026-10-13` (com o comentário `[back-21-textos-legais]`) |
| `docs/legal/LEIA-ME.md` | A seção 1 passou a listar o que foi preenchido, o que falta e três pontos de atenção |
| `tests/test_lgpd.py`, `tests/navegador/lgpd_navegador.py` | Conferem a versão 0.3, o CNPJ, a razão social e o e-mail nas páginas; e que só a política ainda tem "a definir" |

## Antes e depois

**Antes:** as duas páginas mostravam "a definir" (em destaque amarelo) onde deveria estar o nome de quem oferece o sistema, o CNPJ, a cidade, o foro e os e-mails. Quem criava conta aceitava a versão `0.2-2026-10-13`.

**Agora:** os termos estão completos; a política só não diz ainda onde os dados ficam hospedados e qual serviço envia os e-mails. Quem criar conta daqui em diante aceita a versão `0.3-2026-10-13`.

**Por que a versão mudou:** a regra do projeto é "mudou o texto, mudou a versão". É a versão que fica gravada no cadastro de quem cria a conta, como prova do que a pessoa aceitou.

## Como foi testado

- `pytest`: os 512 testes (os 15 de `tests/test_lgpd.py` com as checagens novas).
- Navegador (celular 390 px claro e desktop 1440 px escuro): `lgpd_navegador.py` e `login_navegador.py`.
- Conferido no servidor de demonstração (`http://127.0.0.1:5002/termos`): a página mostra a razão social, o CNPJ e Tremembé/SP.

## Como revisar

```bash
git fetch origin
git diff origin/back-20-producao..origin/back-21-textos-legais -- app/legal app/services/legal_service.py
```

É leitura de texto: conferir se a razão social, o CNPJ, a cidade e o e-mail estão certos em todos os lugares.

## Para decidir (Adauto e Diogo)

1. **Conferir o "/SP".** O Adauto informou só "Tremembé"; o estado foi acrescentado pelo Claude, porque o texto pede cidade e UF e o foro precisa dos dois.
2. **O e-mail é um Gmail.** Serve para começar. Quando o domínio existir (D5), trocar por um e-mail nele e mudar a versão.
3. **Suporte só por e-mail.** Se for atender também pelo WhatsApp, acrescentar o número no §8 dos Termos.
4. **A razão social é a do MEI.** Continua valendo a pergunta ao contador e ao advogado: o MEI pode licenciar software? Se o CNPJ mudar, os dois textos mudam junto.
5. **Admins veem os dados das academias?** O texto de hoje diz que os dados são usados só para prestar o serviço e que cada conta é separada das outras. Se vocês forem ter acesso de administrador aos dados das academias (suporte, por exemplo), isso precisa estar escrito na Política (§4 e §5). Não foi acrescentado aqui porque é decisão de vocês e do advogado.
6. **Preço e período de teste** (Termos §4): o texto ainda fala em "cerca de 2 meses" de graça e preço a definir. Atualizar quando a decisão sair.
7. **Hospedagem e serviço de e-mail** (D4 e D6): são os 3 "a definir" que restam na Política.

## Riscos

- **Dado errado em documento público.** Um erro na razão social ou no CNPJ fica à vista de todo cliente. Por isso o item 1 acima.
- **Contas criadas com a versão 0.2.** Não há nenhuma em produção (o sistema não está no ar). No banco local de quem testou, os cadastros antigos continuam marcados com 0.2, o que é o comportamento certo.
