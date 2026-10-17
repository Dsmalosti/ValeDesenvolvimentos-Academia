# back-31-pdf-ficha-avaliacao — ficha de treino e avaliação física em PDF

| | |
|---|---|
| **Branch** | `back-31-pdf-ficha-avaliacao` |
| **Sai de** | `back-30-meu-perfil` |
| **Data** | 17/10/2026 |
| **Feito por** | Adauto (com o Claude) — **revisão: Diogo** |
| **Pedido** | Adauto, 17/10/2026: "Quero que você faça em formato de PDF as fichas e as avaliações para mandar para o aluno. Verificar formatação bonita antes de confirmar tarefa." |
| **Tem migration** | Não |
| **Dependência nova** | **Não.** O PDF é montado por um gerador pequeno, escrito no projeto (`app/helpers/pdf.py`), só com a biblioteca padrão do Python |

## O que mudou

### 1. Dois PDFs novos

| PDF | Endereço | Onde está o botão | Nome do arquivo |
|---|---|---|---|
| Ficha de treino | `GET /alunos/<id>/ficha/pdf` (`treinos.pdf`) | Tela **Enviar ficha**: a opção **PDF** agora vem escolhida, com os botões "Enviar o PDF" e "Baixar o PDF" | `ficha-ana-souza.pdf` |
| Resultado da avaliação física | `GET /avaliacoes/<id>/pdf` (`avaliacoes.pdf`) | Tela **Resultado**: o botão "Exportar PDF", que antes só mostrava um aviso, agora baixa o arquivo | `avaliacao-ana-souza.pdf` |

**Como ficam** (as cores e o jeito do front: faixa azul-marinho no topo, amarelo de destaque, cartões e linhas alternadas; página A4 em pé):

- **Ficha:**
  - topo com o nome da academia, o aluno e "Válida até";
  - etiquetas com a ficha, o objetivo e quando foi atualizada;
  - **um bloco por treino** (letra, nome e quantidade de exercícios) com a tabela: nº, exercício (com o grupo muscular embaixo), séries, repetições, carga e descanso;
  - no fim, o lembrete "Dúvida em algum exercício? Fale com a equipe" com o telefone da academia;
  - ficha comprida **continua na página seguinte**, repetindo o título do treino com "(continuação)".
- **Avaliação:**
  - topo igual, com a data;
  - etiquetas com o avaliador e a avaliação comparada;
  - **quatro números grandes** (peso, altura, IMC, cintura);
  - **tabela de medidas** com o anterior, o atual e a variação:
    - verde quando a mudança foi na direção do objetivo e vermelho quando foi na contrária, com a mesma regra da tela;
    - cinza para as medidas sem objetivo;
    - "sem mudança" quando o número é o mesmo;
  - a anotação do avaliador;
  - a frase "Estes números são medidas, não um diagnóstico".
- **Rodapé** em todas as páginas: data em que foi gerado e "Página X de Y".
- **Tamanho:** de 3 a 6 KB por arquivo.

### 2. "Enviar o PDF" direto pelo celular

`static/js/compartilhar-pdf.js`:

- **No celular:** o botão abre o **Compartilhar** do aparelho já com o arquivo; a academia escolhe o WhatsApp do aluno e manda.
- **No computador, ou num celular sem essa função:** o botão baixa o PDF.

Por que o arquivo é buscado assim que a tela abre: o iPhone só deixa compartilhar logo depois do toque, sem esperar a internet no meio. Como o arquivo é pequeno, buscar antes não pesa.

### 3. Segurança e privacidade

- Mesmo acesso das telas:
  - a ficha: toda a equipe da academia;
  - o resultado da avaliação: dono, recepção e instrutor (regra da `back-22`);
  - aluno ou avaliação de outra conta: **404**.
- O PDF sai com `Cache-Control: private, no-store`. Tem dado pessoal do aluno (medidas, treino), e nenhum cache no caminho guarda uma cópia.

## Por que um gerador próprio, e não uma biblioteca

As bibliotecas conhecidas trariam pacotes novos ao servidor, e a regra 4 pede autorização para cada dependência:
- `fpdf2` traz Pillow, fontTools e defusedxml;
- `reportlab` traz Pillow;
- `weasyprint` exige programas instalados no sistema.

A ficha e a avaliação só precisam de texto, retângulos e linhas. O formato PDF faz isso com poucas instruções, e o `helpers/pdf.py` (cerca de 200 linhas, comentado) escreve essas instruções:

- **Fontes:** as padrão do PDF (Helvetica e Helvetica negrito). Todo leitor de PDF já tem essas fontes, então nada é embutido e o arquivo fica pequeno.
- **Acentos:** a tabela de letras do Windows (cp1252) cobre o português inteiro. Letra fora dela (emoji) vira "?".
- **Medidas de cada letra:** servem para alinhar à direita e quebrar linhas. São as da Helvetica, lidas do Arial do Windows, que tem as mesmas medidas.

Se um dia o PDF precisar de imagem (logo da academia, foto), aí vale trocar por uma biblioteca, com autorização.

## Como era antes

- Ficha: só em texto (mensagem do WhatsApp e arquivo `.txt`). Na tela de envio, Imagem e PDF ficavam desligados.
- Avaliação: o botão "Exportar PDF" mostrava o aviso "O PDF da avaliação é gerado pelo backend".

## Arquivos

| Arquivo | Mudança |
|---|---|
| `app/helpers/pdf.py` | **Novo.** O gerador (`PDF`: `nova_pagina`, `texto`, `retangulo`, `linha`, `largura`, `quebrar`, `cortar`, `gerar`) |
| `app/helpers/arquivos.py` | **Novo.** `resposta_em_pdf()`: a resposta de download, com o nome e o `no-store` |
| `app/services/pdf_service.py` | **Novo.** O desenho dos dois PDFs (`ficha_em_pdf`, `avaliacao_em_pdf`, `nome_do_arquivo`) |
| `app/services/treino_service.py` | `dados_para_o_pdf()`; a tela de envio passa `sem_imagem` e `arquivo_pdf` (antes: `so_texto=True`) |
| `app/services/avaliacao_service.py` | `MEDIDAS_DO_PDF`, `dados_para_o_pdf()`; o resultado passa `arquivo_pdf` |
| `app/blueprints/treinos/routes.py`, `app/blueprints/avaliacoes/routes.py` | Rotas `treinos.pdf` e `avaliacoes.pdf` |
| `app/templates/treinos/enviar.html` | Opção PDF ligada e escolhida; botões "Enviar o PDF" e "Baixar o PDF"; aviso de como mandar (**levar para o Drive**) |
| `app/templates/avaliacoes/resultado.html` | "Exportar PDF" vira link para o PDF quando `arquivo_pdf` vem; sem ele, fica como no Drive (**levar para o Drive**) |
| `app/static/js/compartilhar-pdf.js` | **Novo.** O "Compartilhar" do celular |
| `tests/test_pdf.py` | **Novo.** 12 testes |
| `tests/test_producao.py` | A varredura de isolamento entre contas também lê o texto de dentro dos PDFs |
| `tests/test_treinos.py`, `tests/navegador/treinos_navegador.py`, `tests/navegador/avaliacoes_navegador.py` | Conferem o PDF em vez de "só texto" |

## Como foi testado

- **Formatação conferida a olho:** os três PDFs de exemplo (ficha de 3 treinos em 2 páginas, avaliação com comparação e primeira avaliação) foram gerados e abertos página por página antes de fechar a branch. A partir disso foram feitos três ajustes: nome comprido do aluno diminui a letra antes de cortar, "sem mudança" no lugar de "0,0 cm", e telefone sem parênteses duplos.
- `pytest` inteiro: **556 passaram**. `tests/test_pdf.py` (12 testes) confere:
  - arquivo bem formado: a tabela de posições aponta para cada objeto;
  - acentos e parênteses escapados;
  - letra fora da tabela vira "?";
  - medidas, quebra e corte de texto;
  - o PDF da ficha com os treinos, o nome do arquivo e o `no-store`;
  - ficha comprida em várias páginas, com "(continuação)" e "Página N de N";
  - recepção e instrutor baixam;
  - outra conta e aluno sem ficha dão 404, e sem login pede login;
  - avaliação com e sem comparação ("sem mudança", variações, anotação, aviso de não diagnóstico);
  - os botões nas duas telas.
- **Navegador** (celular 390 px com toque, desktop 1440 px escuro):
  - `treinos_navegador.py` **83/83**: PDF escolhido, "Enviar o PDF" visível, o link devolve um PDF de verdade, e ao escolher Texto volta o botão do WhatsApp;
  - `avaliacoes_navegador.py` **70/70**: "Exportar PDF" baixa `avaliacao-<aluna>.pdf`, que começa com `%PDF-1.4`.
- Varredura de rotas por papel: igual à branch anterior, mais as duas rotas novas (`/alunos/1/ficha/pdf` e `/avaliacoes/1/pdf`), que respondem 200 aos três papéis. 0 problemas.
- `tests/test_producao.py`: a varredura "a conta B não vê nada da conta A" passou a abrir também as respostas em PDF e procurar a marca da conta A dentro delas (antes ela só lia texto e quebrava com o arquivo binário).

## Como revisar

```bash
git fetch origin
git diff origin/back-30-meu-perfil..origin/back-31-pdf-ficha-avaliacao --stat
git diff origin/back-30-meu-perfil..origin/back-31-pdf-ficha-avaliacao -- app/helpers/pdf.py app/services/pdf_service.py
```

## Riscos

- **Compartilhar no celular:** depende do navegador.
  - Chrome do Android e Safari do iPhone têm a função.
  - Navegador sem ela baixa o arquivo, e a pessoa anexa no WhatsApp à mão.
  - O teste automático usa o Chromium sem "Compartilhar"; o ensaio no aparelho de verdade fica com o Adauto (lista de lançamento).
- **Nome de exercício muito comprido** é cortado com "…" na tabela, para não invadir a coluna ao lado.
- **Imagem da ficha** (a opção "Imagem" da tela) continua desligada. Gerar imagem pede uma biblioteca (Pillow): decisão para depois.
