# back-26-lgpd-final — textos legais 0.4 e registro de acessos

| | |
|---|---|
| **Branch** | `back-26-lgpd-final` |
| **Sai de** | `back-25-admin` |
| **Data** | 14/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Pedido** | Adauto, 14/10/2026: "Termine tudo de LGPD e me manda em forma de PDF para verificar"; "escreva [que os admins veem os dados] e termine essa parte do sistema"; suporte "sem horário", "não falar sobre os horários disponíveis"; o advogado já foi escolhido e vai revisar |
| **Autorização usada** | A1 (Diogo, 10/10/2026): mudar o modelo e criar migration dentro da branch |
| **Tem migration** | **Sim:** `b26e8f9a0b10_registros_de_acesso.py` (tabela nova, nasce vazia) |
| **Dependência nova** | Não |

## Resumo

1. **Os textos legais (versão 0.4)** passaram a descrever o que o sistema faz hoje:
   - **Termos §4** (novo título "Teste grátis, preço e pagamento"): 2 meses grátis da criação da conta, sem cartão; depois, mensal por PIX, com o preço na tela Assinatura e aviso 7 dias antes; 7 dias de tolerância, bloqueio, dados guardados 30 dias, e depois podem ser apagados; mudança de preço com 30 dias de aviso.
   - **Termos §5**: "fase de teste" virou "fase de lançamento" (o teste agora é o teste grátis da §4).
   - **Termos §7** e **Política §4 e §5**: **os administradores do Vale Tec (hoje, os sócios) veem os dados das contas e podem entrar como o dono**, só para suporte, pagamentos, problemas e manutenção, e **cada acesso fica registrado**.
   - **Termos §8**: suporte por e-mail, **sem horário**.
   - **Termos §9**: cancelar é pelo canal de contato (o "pelo sistema" saiu: não existe botão de cancelar); conta bloqueada guarda os dados 30 dias.
   - **Política §2**: novos dados: data do último uso e os pagamentos da mensalidade; a opção de WhatsApp do aluno começa desligada.
   - **Política §6**: prazo da conta bloqueada e dos registros de acesso.
2. **Registro de acessos** (data, hora e IP de cada entrada no sistema), que o Marco Civil da Internet (art. 15) manda guardar por 6 meses. A Política já prometia; o sistema não guardava. Agora:
   - grava a cada login e quando um admin entra na conta de um cliente;
   - apaga sozinho os de mais de 6 meses (a cada gravação; não precisa de agendador);
   - fica guardado mesmo se a conta for apagada antes (sem chave estrangeira);
   - não aparece em tela nenhuma: só sai a pedido de autoridade.
3. **O PDF** dos dois textos, para o Adauto e o advogado: `instance/Textos-legais-Vale-Tec-v0.4.pdf` (fora do git), gerado do mesmo texto que o sistema publica.

## Arquivos

| Arquivo | O que mudou |
|---|---|
| `app/legal/termos-de-uso.md`, `app/legal/politica-de-privacidade.md` | Versão 0.4, data 14/10/2026 e as mudanças acima |
| `app/services/legal_service.py` | `VERSAO = '0.4-2026-10-14'` (era `0.3-2026-10-13`) |
| `docs/legal/LEIA-ME.md` | A tabela "o que o texto promete e se o sistema já cumpre" atualizada; a opção de WhatsApp decidida |
| `app/models.py` | Modelo novo `RegistroDeAcesso` |
| `migrations/versions/b26e8f9a0b10_registros_de_acesso.py` | **Nova.** A tabela `registros_de_acesso` |
| `app/services/registro_de_acesso_service.py` | **Novo.** Grava e apaga os vencidos |
| `app/blueprints/auth/routes.py` | Grava o acesso depois do login (linha marcada `[back-26-lgpd-final]`) |
| `app/services/admin_service.py` | Grava quando o admin entra na conta de um cliente |
| `tests/test_lgpd.py`, `tests/test_admin.py`, `tests/navegador/lgpd_navegador.py` | Versão 0.4 e testes novos |

## O que ainda falta na LGPD (e não é do código)

- **O advogado revisar** os textos (o PDF é para isso) e, depois, tirar o aviso de "versão preliminar".
- **Hospedagem e serviço de e-mail** (os 3 "a definir" que restam na Política §4).
- **Backup diário guardado por 30 dias**: é do servidor de produção.
- **Quando a versão final sair**: decidir se quem já tem conta precisa aceitar de novo (o sistema guarda a versão aceita por cada um).

## Como foi testado

- `pytest`: bateria inteira, com testes novos: o login grava data, hora, IP e evento; o registro de mais de 6 meses some e o de 5 meses fica; senha errada não grava; o admin entrando na conta de um cliente grava "admin_entrou"; os textos publicados trazem o teste grátis, o bloqueio, o acesso dos admins e nada de horário de suporte.
- Migration num Postgres temporário: 12 checagens (inclusive endereço IPv6 e registro de conta que não existe mais).
- Navegador: LGPD 28 de 28.
- PDF conferido na tela antes de enviar.

## Como revisar

```bash
git fetch origin
git diff origin/back-25-admin..origin/back-26-lgpd-final -- app/legal
git diff origin/back-25-admin..origin/back-26-lgpd-final -- app/ migrations/ ':!app/legal'
```

## Riscos

- **IP atrás do proxy:** o IP gravado é o que o app recebe. Em produção, com `PROXIES_NA_FRENTE` certo (ver `docs/DEPLOY.md`), é o do visitante; errado, seria o do proxy.
- **Texto ainda não revisado pelo advogado.** Continua com o aviso de versão preliminar.
