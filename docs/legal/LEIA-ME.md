# Textos legais do Vale Tec — o que o Adauto precisa conferir

Os dois textos que a tela "Criar conta" cita agora estão **publicados no sistema**, como páginas públicas:

| Texto | Página | Arquivo (é nele que se edita) |
|---|---|---|
| Termos de Uso | `/termos` | `app/legal/termos-de-uso.md` |
| Política de Privacidade | `/privacidade` | `app/legal/politica-de-privacidade.md` |

Foram escritos pelo Claude em 10/10/2026, a pedido do Adauto (decisão D7), e atualizados em 13/10/2026 na branch `back-19-lgpd` (decisão D15: deixar a LGPD funcionando no sistema; o advogado revisa depois). Os arquivos saíram desta pasta e foram para `app/legal/` porque o sistema passou a lê-los.

**Os dois aparecem com o aviso "Versão preliminar 0.2, ainda em revisão".** Tire o aviso (a linha que começa com `>` no topo de cada arquivo) quando o advogado aprovar.

## Como editar

1. Abra o arquivo `.md` e mude o texto. É Markdown comum: `#` título, `##` seção, `-` lista, `**negrito**`, tabela com `|`.
2. **Troque a versão** em `app/services/legal_service.py` (a linha `VERSAO = '...'`). É essa versão que fica gravada no cadastro de quem cria a conta. Mudou o texto, mudou a versão.
3. Abra `/termos` e `/privacidade` e confira.

## Importante

O Claude não é advogado. Os textos seguem a LGPD e a prática comum de sistemas parecidos, mas não substituem a revisão de um profissional. A recomendação é passar por um advogado **antes de começar a cobrar**: enquanto o sistema é gratuito e de teste o risco é menor, e é quando entra dinheiro e mais clientes que um contrato mal escrito custa caro.

## 1. O que só você sabe (aparece na página como "a definir")

No arquivo está marcado como `` `[PREENCHER: ...]` ``. Troque o trecho inteiro, com os acentos graves, pelo valor.

| O quê | Onde aparece |
|---|---|
| Nome completo ou razão social de quem oferece o Vale Tec, e o CNPJ | Termos §1, Política (abertura) |
| Cidade e estado da sede, que também define o foro | Termos §1 e §13 |
| E-mail de contato e e-mail para assuntos de dados (pode ser o mesmo) | Termos §3 e §14, Política §7 e §9 |
| Canal de suporte (e-mail, WhatsApp) | Termos §8 |
| Data de publicação | topo dos dois |
| Provedor de hospedagem e país onde os dados ficam (decisão D4) | Política §4 |
| Provedor de e-mail (decisão D6) | Política §4 |

O prazo do "lembrar de mim" saiu desta lista: o sistema usa 30 dias e o texto já diz isso.

## 2. O que o texto promete e se o sistema já cumpre

Cada linha é uma promessa feita ao cliente. Atualizado em 13/10/2026.

| Promessa no texto | Já é verdade no sistema? |
|---|---|
| Teste gratuito de cerca de 2 meses; preço avisado com 30 dias de antecedência | Não depende do sistema (os 30 dias são sugestão do Claude) |
| Suporte nos fins de semana e depois das 20h em dias úteis | Não depende do sistema |
| Uma conta não enxerga nada de outra | **Sim.** Vale também para exercícios, desde a `back-06` |
| Cada pessoa da equipe vê só o que o papel dela permite | **Sim**, desde a `back-06`. Medidas de avaliação física: só dono e instrutor (`back-15`) |
| A academia consegue exportar os dados de um aluno | **Sim** (`back-19`): botão no perfil do aluno, só para o dono |
| A academia consegue excluir os dados de um aluno | **Sim** (`back-19`): "Excluir aluno" apaga os dados pessoais e de saúde; os pagamentos ficam, sem identificação |
| Marcação de "aceita receber mensagens" por aluno | **Sim** (`back-19`): no cadastro do aluno; quem recusou não entra na fila de mensagens |
| O sistema não envia mensagem sozinho | **Sim** (`back-16`): prepara o texto e abre o WhatsApp de quem usa |
| Senha guardada só como hash | **Sim** (bcrypt) |
| Não coletamos dados de cartão | **Sim**: o sistema não processa pagamento |
| Só cookies necessários, sem rastreamento | **Sim.** O front não carrega nenhuma ferramenta de análise ou propaganda, e a regra de conteúdo da `back-18` só deixa rodar script do próprio sistema (mais o Bootstrap das telas antigas) |
| Sessão de 12 horas sem uso; "lembrar de mim" por 30 dias | **Sim** (`back-18`) |
| Logs sem CPF, telefone nem senha | **Sim**, e há um teste que vigia isso (`tests/test_lgpd.py`) |
| Conexão por HTTPS | **Na produção, sim:** a `back-18` obriga. Depende de a hospedagem estar no ar (Fase D) |
| Cópia de segurança diária, guardada por 30 dias | **Ainda não.** É do ambiente de produção (Fase D) |
| Depois do cancelamento da conta, 30 dias para exportar e depois os dados são apagados | **Ainda não.** Não existe "cancelar conta" no sistema; hoje seria feito à mão, a pedido |
| Registros de acesso (data, hora, IP) guardados por 6 meses | **Ainda não.** É do servidor de produção (Fase D) |
| Aviso de incidente à academia em até 48 horas | É compromisso seu, não do sistema |

**Regra prática:** antes de tirar o aviso de "versão preliminar", cada "Ainda não" precisa virar "Sim", ou a promessa sai do texto.

## 3. Pontos para decidir com um advogado

1. **Quem assina.** Se o Vale Tec for oferecido pelo seu MEI, o contrato é com o MEI. Vale confirmar se a atividade do MEI cobre licenciamento de software.
2. **Limite de responsabilidade** (Termos §11). Está escrito de forma conservadora. Cláusula que tira responsabilidade pode ser considerada abusiva se o cliente for tratado como consumidor.
3. **Encarregado de dados (DPO).** Empresas pequenas têm regras mais leves na ANPD e, em geral, não precisam nomear um encarregado, mas precisam manter um canal de contato. Confirmar se o seu caso se enquadra.
4. **Contrato de tratamento de dados com a academia.** Hoje está embutido nos Termos (§7). Para clientes maiores, costuma virar um documento separado.
5. **Consentimento do aluno para a avaliação física.** O texto põe essa obrigação na academia. Vale oferecer a ela um modelo de termo de consentimento, para facilitar.
6. **A opção de WhatsApp vem marcada.** No cadastro do aluno, "Aceita receber avisos pelo WhatsApp" começa ligada e a academia desmarca se o aluno não quiser. Para lembrete e cobrança isso costuma bastar; para mensagem com oferta (o parabéns com desconto, por exemplo), o advogado pode pedir que comece desligada.
7. **O que fica depois de apagar um aluno.** Os pagamentos continuam, sem nome. Confirmar o prazo de guarda desses registros.
8. **Foro.** Está como a sua cidade, com a ressalva do consumidor.

## 4. O que o sistema guarda como prova do aceite

Quem cria a conta em `/criar-conta` fica com a **versão dos textos** e a **data e hora** gravadas no cadastro (`instrutores.termos_versao` e `termos_aceitos_em`). Contas criadas antes de 13/10/2026 não têm esse registro. Quem entra por convite não aceita termos: o contrato é com o dono da conta.

Quando a versão final for publicada, vale decidir se as contas antigas precisam aceitar de novo (o sistema ainda não pede).
