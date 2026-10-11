# Textos legais do Vale Tec — o que o Adauto precisa conferir

Nesta pasta estão os rascunhos dos dois textos que a tela "Criar conta" promete ao cliente:

- `Termos-de-Uso.md`
- `Politica-de-Privacidade.md`

Foram escritos pelo Claude em 10/10/2026, a pedido do Adauto (decisão D7 do roadmap), para ele revisar e completar. **Nenhum dos dois vale ainda** e nenhum está publicado no sistema.

## Importante

O Claude não é advogado. Os textos seguem a LGPD e a prática comum de sistemas parecidos, mas não substituem a revisão de um profissional. A recomendação é passar por um advogado **antes de começar a cobrar**: enquanto o sistema é gratuito e de teste o risco é menor, e é quando entra dinheiro e mais clientes que um contrato mal escrito custa caro.

## 1. O que só você sabe (está marcado como `[PREENCHER]`)

| O quê | Onde aparece |
|---|---|
| Nome completo ou razão social de quem oferece o Vale Tec, e o CNPJ | Termos §1, Política (abertura) |
| Cidade e estado da sede, que também define o foro | Termos §1 e §13 |
| E-mail de contato e e-mail para assuntos de dados (pode ser o mesmo) | Termos §3 e §14, Política §7 e §9 |
| Canal de suporte (e-mail, WhatsApp) | Termos §8 |
| Data de publicação | topo dos dois |
| Provedor de hospedagem e país onde os dados ficam (decisão D4) | Política §4 |
| Provedor de e-mail (decisão D6) | Política §4 |
| Prazo do "lembrar de mim" | Política §3 |

## 2. O que eu assumi e você precisa confirmar

Cada linha é uma promessa feita ao cliente. Se não for verdade, troque o texto ou me avise para ajustar o sistema.

| Promessa no texto | De onde veio | Já é verdade no sistema? |
|---|---|---|
| Teste gratuito de cerca de 2 meses; preço avisado com 30 dias de antecedência | Sua resposta à D2. Os **30 dias** são sugestão minha | Não depende do sistema |
| Suporte nos fins de semana e depois das 20h em dias úteis | Sua resposta à D11 | Não depende do sistema |
| Cópia de segurança diária, guardada por 30 dias | Você pediu backup; os números são sugestão minha | **Ainda não.** Entra na Fase D (ambiente de produção) |
| Depois do cancelamento, 30 dias para exportar e depois os dados são apagados | Sugestão minha | **Ainda não.** Precisa da branch de LGPD |
| Aviso de incidente à academia em até 48 horas | Sugestão minha | É compromisso seu, não do sistema |
| A academia consegue exportar e excluir os dados de um aluno | Tarefa 3.9 da lista do backend | **Ainda não.** Branch de LGPD |
| Marcação de "aceita receber mensagens" por aluno | Tarefa 3.9 | **Ainda não.** Branch de LGPD |
| Uma conta não enxerga nada de outra | Branch `back-03-isolamento` | Sim para alunos, planos, pagamentos, fichas e usuários. **Exercícios ainda são compartilhados** entre todas as contas |
| Cada pessoa da equipe vê só o que o papel dela permite | Tarefa 3.6 | **Ainda não.** Branch de contas e papéis |
| Conexão por HTTPS | — | **Ainda não.** Fase D |
| Logs sem CPF, telefone nem senha | Branch `back-02-limpeza` | Sim |
| Senha guardada só como hash | Já era assim (bcrypt) | Sim |
| Não coletamos dados de cartão | O sistema não processa pagamento | Sim |
| Só cookies necessários, sem rastreamento | O front não carrega nenhuma ferramenta de análise ou propaganda | Sim |
| Registros de acesso (data, hora, IP) guardados por 6 meses | Exigência do Marco Civil da Internet para quem oferece aplicação na internet | **Ainda não.** Hoje o sistema não guarda esses registros de forma organizada; vai para a Fase D |

**Regra prática:** não publique os textos enquanto houver "Ainda não" nesta tabela para algo que o texto promete. Ou o sistema passa a cumprir, ou a promessa sai do texto.

## 3. Pontos para decidir com um advogado

1. **Quem assina.** Se o Vale Tec for oferecido pelo seu MEI, o contrato é com o MEI. Vale confirmar se a atividade do MEI cobre licenciamento de software.
2. **Limite de responsabilidade** (Termos §11). Está escrito de forma conservadora. Cláusula que tira responsabilidade pode ser considerada abusiva se o cliente for tratado como consumidor.
3. **Encarregado de dados (DPO).** Empresas pequenas têm regras mais leves na ANPD e, em geral, não precisam nomear um encarregado, mas precisam manter um canal de contato. Confirmar se o seu caso se enquadra.
4. **Contrato de tratamento de dados com a academia.** Hoje está embutido nos Termos (§7). Para clientes maiores, costuma virar um documento separado.
5. **Consentimento do aluno para a avaliação física.** O texto põe essa obrigação na academia. Vale oferecer a ela um modelo de termo de consentimento, para facilitar.
6. **Foro.** Está como a sua cidade, com a ressalva do consumidor.

## 4. O que falta no sistema para publicar

- Duas páginas públicas, `/termos` e `/privacidade`, ligadas nos links da tela "Criar conta" (hoje os links apontam para `#termos` e `#privacidade`, que não levam a lugar nenhum).
- Guardar, no cadastro, a data e a versão dos termos que a pessoa aceitou.

As duas coisas estão previstas na branch de LGPD do roadmap.
