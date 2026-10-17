# Textos legais do Vale Tec — o que o Adauto precisa conferir

Os dois textos que a tela "Criar conta" cita estão **publicados no sistema**, como páginas públicas:

| Texto | Página | Arquivo (é nele que se edita) |
|---|---|---|
| Termos de Uso | `/termos` | `app/legal/termos-de-uso.md` |
| Política de Privacidade | `/privacidade` | `app/legal/politica-de-privacidade.md` |

**Histórico:**

| Versão | Data | Branch | O que mudou |
|---|---|---|---|
| 0.2 | 10/10/2026 | — | Escritos pelo Claude, a pedido do Adauto (D7) |
| 0.2 | 13/10/2026 | `back-19-lgpd` | LGPD funcionando no sistema |
| 0.3 | 13/10/2026 | `back-21-textos-legais` | Dados da empresa |
| 0.4 | 14/10/2026 | `back-26-lgpd-final` | Teste grátis, administradores, registro de acessos |
| **1.0** | **17/10/2026** | `back-32-textos-legais-final` | Domínio, e-mails do domínio, hospedagem (Render), envio de e-mail (Brevo), preços e promoção de lançamento, Meu perfil e PDFs |

**A versão 1.0 está escrita como se já fosse publicada:** sem aviso de "preliminar" e sem nada "a definir". **Ela ainda precisa da revisão do advogado** (o Adauto já encontrou um) **antes de o sistema ir ao ar.** O PDF para o advogado é gerado com os textos exatamente como o sistema mostra; o último é o `Textos-legais-Vale-Tec-v1.0.pdf`.

## Como editar

1. Abra o arquivo `.md` e mude o texto. É Markdown comum: `#` título, `##` seção, `-` lista, `**negrito**`, tabela com `|`.
2. **Troque a versão** em `app/services/legal_service.py` (a linha `VERSAO = '...'`). É essa versão que fica gravada no cadastro de quem cria a conta. Mudou o texto, mudou a versão.
3. Abra `/termos` e `/privacidade` e confira.

## Importante

O Claude não é advogado. Os textos seguem a LGPD e a prática comum de sistemas parecidos, mas não substituem a revisão de um profissional. **O advogado revisa antes de o primeiro cliente pagar.**

## 1. Os dados da versão 1.0

| O quê | Valor | Onde aparece |
|---|---|---|
| Razão social | 60.499.733 ADAUTO RODRIGUES DOS SANTOS NETTO | Termos §1, Política (abertura) |
| CNPJ | 60.499.733/0001-44 | Termos §1, Política (abertura) |
| Cidade da sede e foro | Tremembé/SP (confirmado pelo Adauto) | Termos §1 e §13, Política (abertura) |
| Site | https://valesolucoestec.com.br (registrado no Registro.br) | Termos §1 e §14, Política (abertura) |
| Suporte | suporte@valesolucoestec.com.br | Termos §3, §8 e §14, Política §9, telas de assinatura e de conta bloqueada |
| Dados pessoais (ouvidoria) | ouvidoria@valesolucoestec.com.br | Termos §14, Política (abertura), §7 e §9 |
| Hospedagem e banco | Render (Render Services, Inc.), Estados Unidos | Política §4 |
| E-mails do sistema | Brevo (Sendinblue SAS), União Europeia | Política §4 |
| Preços | Academia R$ 59,99 e personal R$ 29,99 por mês (confirmados pelo Diogo) | Termos §4 |
| Promoção | 50% para as 10 primeiras contas, enquanto a conta continuar ativa | Termos §4 |
| Data de publicação | 17/10/2026 | topo dos dois |

**Antes de publicar:** as caixas `suporte@` e `ouvidoria@` precisam existir (ou encaminhar para o Gmail). Sem isso, quem escrever para elas não é atendido. Está na lista de lançamento.

**Para trocar um destes dados no futuro:** procure o valor antigo nos dois arquivos de `app/legal/`, troque em todos os lugares e mude a `VERSAO`. O e-mail de suporte das telas vem da configuração `VALE_TEC_SUPORTE_EMAIL` (padrão: o do domínio).

## 2. O que o texto promete e se o sistema já cumpre

Cada linha é uma promessa feita ao cliente. Atualizado em 17/10/2026 (branch `back-32-textos-legais-final`).

| Promessa no texto | Já é verdade no sistema? |
|---|---|
| Teste grátis de 2 meses; aviso 7 dias antes do fim; 7 dias de tolerância depois do vencimento; dados guardados 30 dias depois do bloqueio | **Sim** (`back-24`). Avisar mudança de preço com 30 dias é compromisso de vocês |
| Preços R$ 59,99 / R$ 29,99 e 50% para as 10 primeiras contas, enquanto a conta continuar ativa | **Sim** (`back-28`). O admin pode tirar a promoção de conta de teste ou repetida |
| Mudar nome, e-mail e senha em Meu perfil; trocar a senha desconecta os outros aparelhos | **Sim** (`back-30`) |
| PDF da ficha e da avaliação não fica guardado no Vale Tec | **Sim** (`back-31`): o arquivo é montado na hora e sai com `no-store` |
| Nenhum dado de aluno vai para o Brevo | **Sim**: o sistema só manda e-mail de convite, de troca de senha e de avisos da conta, para quem usa o sistema |
| Suporte por e-mail, sem horário fixo | Não depende do sistema |
| Uma conta não enxerga nada de outra | **Sim**, desde a `back-06`; há uma varredura automática que confere todas as rotas, PDFs incluídos (`tests/test_producao.py`) |
| Cada pessoa da equipe vê só o que o papel dela permite | **Sim**, desde a `back-06`. Avaliação física: dono, recepção e instrutor veem; só dono e instrutor registram (`back-22`) |
| Os administradores do Vale Tec veem os dados das contas, podem entrar como o dono, e cada acesso fica registrado | **Sim** (`back-25`). O admin dentro da conta não muda o login nem a senha do dono (`back-30`) |
| A academia consegue exportar os dados de um aluno | **Sim** (`back-19`) |
| A academia consegue excluir os dados de um aluno | **Sim** (`back-19`): apaga os dados pessoais e de saúde; os pagamentos ficam, sem identificação |
| Marcação de "aceita receber mensagens" por aluno | **Sim** (`back-19`; desde a `back-22` começa desligada) |
| O sistema não envia mensagem sozinho | **Sim** (`back-16`). Se o envio automático pelo WhatsApp entrar (pedido do Adauto, ainda em decisão), este ponto e a Política precisam mudar |
| Senha guardada só como hash | **Sim** (bcrypt) |
| Não coletamos dados de cartão | **Sim**: o sistema não processa pagamento |
| Só cookies necessários, sem rastreamento | **Sim.** Nenhuma ferramenta de análise ou propaganda; desde a `back-27` o sistema não carrega nada de fora |
| Sessão de 12 horas sem uso; "lembrar de mim" por 30 dias | **Sim** (`back-18`) |
| Logs sem CPF, telefone nem senha | **Sim**, com teste (`tests/test_lgpd.py`) |
| Conexão por HTTPS | **Na produção, sim:** a `back-18` obriga. O Render dá o certificado de graça para o domínio |
| Cópia de segurança diária, guardada por 30 dias | **Ainda não: depende do deploy.** Plano em `docs/DEPLOY.md` (backup do Render + cópia diária guardada fora dele por 30 dias). Antes de abrir para clientes, o backup precisa estar ligado e com a restauração testada |
| Depois do cancelamento, 30 dias para exportar e depois os dados são apagados | **Em parte.** O cancelamento é pelo e-mail de suporte; o apagamento é pelo painel de administração (`back-25`), depois dos 30 dias |
| Registros de acesso (data, hora, IP) guardados por 6 meses | **Sim** (`back-26`) |
| Aviso de incidente à academia em até 48 horas | É compromisso de vocês, não do sistema |

## 3. Pontos para o advogado olhar

1. **Quem assina.** O Vale Tec é oferecido pelo MEI do Adauto: confirmar se a atividade do MEI cobre licenciamento de software (SaaS) ou se precisa de outro CNAE.
2. **Transferência internacional** (Política §4). Os dados ficam nos EUA (Render) e o e-mail passa pela União Europeia (Brevo). O texto diz que a transferência segue os arts. 33 a 36 da LGPD com garantias contratuais dos fornecedores. Confirmar qual mecanismo usar: cláusulas-padrão da ANPD (Resolução CD/ANPD nº 19/2024) ou o contrato de tratamento (DPA) dos próprios fornecedores.
3. **Encarregado (DPO).** O texto diz que o MEI é agente de pequeno porte, dispensado de encarregado pela Resolução CD/ANPD nº 2/2022, e mantém o canal `ouvidoria@`. Confirmar o enquadramento.
4. **Limite de responsabilidade** (Termos §11). Escrito de forma conservadora e só "durante o teste grátis". Cláusula que tira responsabilidade pode ser abusiva se o cliente for tratado como consumidor.
5. **Promoção de lançamento** (Termos §4). "Enquanto a conta continuar ativa" e "50% do preço novo, se o preço mudar". Confirmar se a redação protege vocês se um dia a promoção precisar acabar.
6. **Contrato de tratamento de dados com a academia.** Hoje está embutido nos Termos (§7). Para clientes maiores, costuma virar documento separado.
7. **Consentimento do aluno para a avaliação física.** O texto põe essa obrigação na academia. Vale oferecer a ela um modelo de termo de consentimento.
8. **O que fica depois de apagar um aluno.** Os pagamentos continuam, sem nome. Confirmar o prazo de guarda desses registros.
9. **Foro.** Tremembé/SP, com a ressalva do consumidor.
10. **Aceite de quem entrou antes.** Contas criadas com a versão 0.4 (só testes, até agora) não aceitaram a 1.0. Como ainda não há cliente, não há o que fazer; daqui em diante, mudança importante pede aviso com 15 dias (Termos §12).

## 4. O que o sistema guarda como prova do aceite

Quem cria a conta em `/criar-conta` fica com a **versão dos textos** e a **data e hora** gravadas no cadastro (`instrutores.termos_versao` e `termos_aceitos_em`). Quem entra por convite não aceita termos: o contrato é com o dono da conta.
