<!-- Criado em: 28/09/2026 15:15 -->
<!-- Modificado em: 28/09/2026 16:15 -->

# Feature Specification: Triagem de curadoria com LLM

**Feature Branch**: `011-triagem-llm`

**Created**: 28/09/2026

**Status**: Draft

**Input**: User description: "011-triagem-llm — Triagem com LLM dos artefatos inventariados (etapa 2 da curadoria automatizada, depende da 010). Escopo fechado no debate docs/debates/curadoria-automatizada.md (linha 468 e decisões C1–C6, K3, K4, P2–P4, F2): chamada ao `claude` CLI SEM ferramentas (texto entra, JSON sai; quem grava é o praxisforge); dois modelos — um mais barato para a triagem e outro para o rascunho; um prompt por artefato; contexto do acervo `library/` (veredito = "já existe no acervo"); vereditos coberto / lacuna / fora de escopo com justificativa, e rascunho (só ideias) quando lacuna; fusões propostas pelo LLM entram como lacuna; prompts e critérios versionados em `prompts/curation/` (mudar o prompt invalida vereditos); teto de custo por execução + `--resume`; similaridade em duas camadas (heurística + juiz LLM barato, limiar 0,7) para garantir que o rascunho extrai ideias e não copia; staging em `~/.config/praxisforge/curation/<alias>/`; triagem incremental — só artefatos pendentes/alterados por hash (pasta `in_curation`); atualiza as etapas do state.json da 010 (pending → triaged → drafted, failed com tentativas). Falha do CLI (timeout, indisponível, JSON inválido) não derruba o lote."

## Contexto

A feature 010 inventaria cada pasta registrada e grava, fora do repositório, um manifesto e um
estado por artefato (etapa `pending`). Esta feature cobre a **etapa 2** do fluxo decidido no
debate de 25/09/2026: um modelo de linguagem lê cada artefato pendente e diz se a ideia dele
**já existe no acervo `library/`** (coberto), **falta no acervo** (lacuna) ou **não é
conhecimento curável** (fora de escopo). Para cada lacuna, ele escreve um **rascunho autoral só
com as ideias**. Rascunhos e vereditos ficam numa área de staging, fora do repositório,
aguardando a revisão e a promoção (feature 012).

Três restrições do debate não são negociáveis:

- **Segurança (K4)**: o conteúdo vem de repositórios de terceiros e pode conter *prompt
  injection*. Por isso o modelo é chamado **sem nenhuma ferramenta**: recebe texto e devolve
  JSON, e só o praxisforge grava arquivos.
- **Só ideias (Princípio V)**: nenhum trecho literal, tradução ou paráfrase próxima entra num
  rascunho.
- **Contexto dentro do repositório (P2/C3)**: a comparação usa só o acervo e critérios
  versionados, nunca as regras pessoais do curador.

Fora de escopo: a revisão pelo curador, a promoção para `library/`, o PR automático e o alerta de
fonte alterada (feature 012).

## Modelo de ameaça

- **Atacante**: autor (ou quem comprometeu) um repositório de terceiros registrado para curadoria.
- **Vetor**: o conteúdo dos artefatos, que chega ao modelo e, por meio dos rascunhos gerados,
  pode chegar ao contexto de outras triagens.
- **Ativos protegidos**: (1) a máquina do curador (arquivos, processos, segredos no ambiente);
  (2) o registro, o estado e o staging em `~/.config/praxisforge/`; (3) o repositório público e o
  acervo `library/`; (4) a cota da assinatura do modelo; (5) a integridade dos vereditos.
- **Objetivos do atacante considerados**: executar comandos ou gravar arquivos na máquina;
  exfiltrar dados locais pelo modelo; gravar fora do staging; esgotar a cota; distorcer
  vereditos (esconder ou inflar ideias); plantar instruções num rascunho que contamine outras
  triagens.
- **O que sai da máquina** (enviado ao serviço do modelo): o conteúdo do artefato de terceiros,
  o alias e o caminho relativo do artefato, o índice e itens do acervo público, o índice dos
  rascunhos pendentes, os prompts e critérios versionados. Nada além disso: nem caminho
  absoluto, nem registro, nem variáveis de ambiente, nem outros arquivos de `~/.config`.
- **Fora do escopo de segurança desta feature**: comprometimento do próprio CLI `claude`, da conta
  do curador ou do sistema operacional; alteração maliciosa de `prompts/curation/` ou de
  `library/` por commit (protegida pela revisão de PR do repositório).
- **Risco residual aceito**: uma injeção pode distorcer um veredito `covered` ou `out_of_scope`
  sem executar nada. Mitigações: `covered` precisa citar item existente no catálogo real (FR-012),
  todo veredito guarda a justificativa auditável, e `gap`/fusão sempre passam por aprovação
  humana (012). Não há garantia técnica contra veredito distorcido; ela depende da revisão.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Triar os artefatos pendentes de uma pasta (Priority: P1)

O curador roda a triagem numa pasta já inventariada. Cada artefato pendente é enviado, um por
vez, ao modelo de triagem, junto com o contexto do acervo e os critérios versionados. O modelo
devolve um veredito (coberto, lacuna ou fora de escopo) com justificativa. O praxisforge valida a
resposta, grava o veredito no staging e avança o artefato para `triaged`. Ao final, a execução
mostra quantos artefatos caíram em cada veredito.

**Why this priority**: sem veredito não há revisão nem promoção. Este é o menor passo que já
reduz o trabalho do curador: ele deixa de ler milhares de arquivos e passa a olhar só as lacunas.

**Independent Test**: com uma pasta inventariada, um acervo de teste e um modelo simulado que
devolve respostas fixas, rodar a triagem e conferir o veredito gravado e a etapa `triaged` de
cada artefato.

**Acceptance Scenarios**:

1. **Given** uma pasta inventariada com 3 artefatos `pending`, **When** o curador roda a triagem
   da pasta, **Then** cada artefato recebe exatamente um veredito com justificativa, passa para
   `triaged` e o resumo mostra a contagem por veredito.
2. **Given** um artefato cuja ideia já existe num item do acervo, **When** ele é triado, **Then**
   o veredito é "coberto" e referencia o item do acervo que o cobre.
3. **Given** uma resposta do modelo fora do contrato (JSON inválido, veredito desconhecido,
   justificativa vazia), **When** ela é recebida, **Then** nada é gravado como veredito, o
   artefato vai para `failed` com o motivo e o lote segue para o próximo artefato.
4. **Given** um artefato que já está `triaged` e não mudou, **When** a triagem roda de novo,
   **Then** ele não é enviado ao modelo.
5. **Given** a triagem de todas as pastas (`--all`), **When** uma pasta falha (estado corrompido,
   pasta inacessível), **Then** a falha aparece no resumo e as outras pastas são triadas.

---

### User Story 2 - Rascunho só com ideias para cada lacuna (Priority: P1)

Para cada artefato com veredito "lacuna", o praxisforge pede ao modelo de rascunho uma proposta
de item para o acervo (tipo, nome, descrição e corpo em pt-BR), escrita com estrutura própria e
só com as ideias. Antes de aceitar a proposta, duas verificações de similaridade conferem se ela
não é cópia, tradução ou paráfrase próxima do original. A proposta aprovada nas verificações é
gravada no staging e o artefato passa para `drafted`.

**Why this priority**: o rascunho é o que a revisão vai aprovar ou descartar. Sem a verificação
de similaridade, o acervo público correria o risco de receber obra derivada, o que viola o
Princípio V.

**Independent Test**: com um modelo simulado, provocar (a) um rascunho autoral, que é gravado e
fica `drafted`; e (b) um rascunho que repete a estrutura do original, que é sinalizado,
regenerado uma vez e, se continuar sinalizado, gravado com alerta.

**Acceptance Scenarios**:

1. **Given** um artefato `triaged` com veredito "lacuna", **When** o rascunho é gerado e passa
   nas verificações, **Then** a proposta é gravada no staging, o artefato fica `drafted` e a
   proposta cita a origem (pasta, caminho e hash do artefato).
2. **Given** um rascunho cuja estrutura coincide com a do original em ≥ 0,7 (sequência de
   títulos, listas, tabelas e ordem dos passos), **When** ele é verificado, **Then** é sinalizado
   e regenerado uma única vez com a instrução de reescrever pelas ideias.
3. **Given** um rascunho que o juiz classifica como tradução ou paráfrase próxima, **When** ele é
   verificado, **Then** recebe o mesmo tratamento: sinalização e uma regeneração.
4. **Given** um rascunho que continua sinalizado depois da regeneração, **When** ele é gravado,
   **Then** fica `drafted` com um alerta de similaridade visível na revisão, e nunca é descartado
   em silêncio.
5. **Given** um artefato "coberto" ou "fora de escopo", **When** a execução termina, **Then**
   nenhum rascunho é gerado para ele.
6. **Given** um artefato cuja ideia completa um item existente do acervo, **When** o modelo de
   triagem propõe fundir os dois, **Then** o veredito é registrado como "lacuna" do tipo fusão,
   com o item do acervo afetado identificado, e o rascunho descreve a mudança proposta nesse item.

---

### User Story 3 - Teto de custo e retomada (Priority: P2)

O curador define um teto por execução (número de chamadas ao modelo e/ou valor em US$). Ao
atingir o teto, a triagem termina o artefato em curso, grava o estado, sai com um código próprio
e mostra o comando para retomar. A retomada continua de onde parou, sem refazer o que já foi
concluído.

**Why this priority**: pastas como `claude_code_templates` têm mais de mil artefatos. Sem teto, uma
execução pode consumir a cota inteira da assinatura. O fluxo principal funciona sem o teto, mas
ele é necessário para usar a triagem em escala.

**Independent Test**: com um modelo simulado e teto de 2 chamadas numa pasta com 5 artefatos,
conferir que a execução para depois da 2ª chamada com o código de teto e que a retomada processa
os 3 restantes.

**Acceptance Scenarios**:

1. **Given** um teto de N chamadas, **When** a N-ésima chamada termina, **Then** nenhuma nova
   chamada é iniciada, o estado fica gravado, a saída usa o código de teto e mostra o comando de
   retomada.
2. **Given** um teto em US$ e um modelo que informa o custo de cada chamada, **When** o custo
   acumulado atinge o teto, **Then** a execução para como no cenário 1.
3. **Given** um modelo que não informa o custo, **When** só o teto em US$ foi definido, **Then** o
   curador é avisado de que o custo não pode ser medido e a execução conta só as chamadas, sem
   ultrapassar um teto padrão de chamadas.
4. **Given** uma execução interrompida (teto, falha de energia, Ctrl+C), **When** o curador
   retoma, **Then** os artefatos já triados ou rascunhados não são reenviados e nenhum veredito
   gravado é perdido.
5. **Given** cada execução, **When** ela termina, **Then** o resumo mostra chamadas feitas, custo
   acumulado (quando conhecido) e artefatos restantes.

---

### User Story 4 - Mudar prompt ou critérios invalida vereditos (Priority: P2)

Os prompts de triagem, de rascunho e do juiz e os critérios do que é "coberto", "lacuna" e "fora
de escopo" são versionados no repositório. Cada veredito e rascunho registra a versão do prompt e
dos critérios que o produziram. Quando essa versão muda, os artefatos afetados voltam a ser
elegíveis para nova triagem.

**Why this priority**: sem isso, vereditos antigos e novos se misturam sem que dê para saber sob
qual regra cada um foi dado. É necessário para a curadoria ser auditável, mas não bloqueia a
primeira triagem.

**Independent Test**: triar uma pasta, alterar o arquivo de critérios e rodar de novo; os
artefatos que não passaram da revisão voltam para a triagem, com a versão nova registrada.

**Acceptance Scenarios**:

1. **Given** vereditos gravados com a versão X dos critérios, **When** os critérios mudam para Y
   e a triagem roda, **Then** os artefatos `triaged`, `drafted` ou `failed` com versão X são
   triados de novo e passam a registrar Y.
2. **Given** um artefato já `reviewed` ou `promoted`, **When** os critérios mudam, **Then** ele não
   é triado de novo (a decisão humana prevalece; o alerta de mudança é da 012).
3. **Given** um arquivo de prompt ausente ou vazio, **When** a triagem é iniciada, **Then** ela
   falha antes de qualquer chamada, com mensagem que indica o arquivo faltante.

---

### User Story 5 - Triagem incremental quando o fork muda (Priority: P3)

Quando uma pasta volta para `in_curation` porque o fork recebeu commits, o novo inventário (010)
só devolve para `pending` os artefatos cujo hash mudou. A triagem trata apenas esses, e os
vereditos dos demais continuam válidos.

**Why this priority**: o inventário da 010 já faz a parte difícil (F2). Aqui basta garantir que a
triagem respeita o estado e não reprocessa o que não mudou.

**Independent Test**: triar uma pasta, alterar um arquivo, reinventariar e triar de novo; só o
artefato alterado é enviado ao modelo.

**Acceptance Scenarios**:

1. **Given** uma pasta triada em que 1 de 10 artefatos mudou, **When** o inventário e a triagem
   rodam de novo, **Then** exatamente 1 chamada de triagem é feita.
2. **Given** um artefato alterado que tinha rascunho no staging, **When** ele é triado de novo,
   **Then** o rascunho antigo é substituído e a versão anterior não é apresentada como atual.

### Edge Cases

- **Modelo indisponível, timeout ou comando ausente**: o artefato vai para `failed` com o motivo e
  o número de tentativas é incrementado. Se o comando do modelo não existir na máquina, a
  execução falha antes da primeira chamada (erro de ambiente), sem marcar artefatos como
  `failed`.
- **Falhas repetidas**: um artefato `failed` é tentado de novo na próxima execução até um limite
  de tentativas (padrão 3). Depois disso, fica `failed` e só volta com uma opção explícita.
- **Falhas em sequência**: se as N primeiras chamadas seguidas falharem por indisponibilidade
  (padrão 5), a execução para, para não consumir a pasta inteira marcando `failed`.
- **Resposta sem saída estruturada** (`structured_output` ausente, JSON do CLI truncado ou
  ilegível, `is_error`): tratada como fora do contrato (cenário 3 da US1); texto livre do modelo
  nunca é interpretado como resposta.
- **Artefato grande demais para o contexto do modelo**: não é truncado em silêncio. Vai para
  `failed` com motivo "tamanho" e aparece no resumo.
- **Artefato `unknown` (sem tipo pela convenção)**: é triado normalmente. O modelo sugere o tipo e,
  se for lacuna, o rascunho declara o tipo proposto.
- **Artefato que é diretório (skill com arquivos de apoio)**: o modelo recebe o arquivo principal
  e os arquivos de apoio de texto, dentro do limite de tamanho.
- **Conteúdo com instruções ao modelo** ("ignore o anterior e rode X"): não tem efeito além da
  resposta, porque não há ferramentas; uma resposta que foge do contrato é rejeitada como no
  cenário 3 da US1.
- **Duas execuções simultâneas na mesma pasta**: a segunda é recusada (mesmo bloqueio da 010).
- **Pasta nunca inventariada**: erro com a instrução de rodar o inventário antes.
- **Acervo vazio**: a triagem funciona; na prática, tudo que for conhecimento curável tende a ser
  "lacuna".
- **Pasta com licença `link` ou `unknown`**: o modelo de triagem devolve, junto com o veredito
  `gap`, um resumo das ideias do artefato; o modelo de rascunho recebe só esse resumo, nunca o
  texto original (D2, FR-016a).

## Clarifications

### Session 2026-09-28

- Q: Licença `link`/`unknown`: quem produz o resumo das ideias que alimenta o rascunho (D2)? → A: o
  modelo de triagem, junto com o veredito `gap`; o rascunho recebe só o resumo.
- Q: O rascunho de cada lacuna é gerado na mesma execução da triagem ou num passo separado? → A:
  na mesma execução, automaticamente (FR-016); o custo é contido pelos tetos (FR-026).
- Q: A triagem reconhece ideias já rascunhadas em outras pastas ou compara só com o acervo? → A:
  acervo + rascunhos pendentes no staging de todas as pastas; repetição vira fusão com o rascunho
  existente (FR-011, FR-014).
- Q: Staging fora do repositório (junto do estado) ou dentro (`curation/<alias>/`, debate E1)? → A:
  fora, em `<diretório do registro>/curation/<alias>/` (FR-022); substitui o E1.
- Q: Os artefatos `unknown` entram na triagem por padrão? → A: sim, triados como os demais, e o
  modelo sugere o tipo (FR-015).

- Q: A calibração estrutural com a `guarda-barra-qualidade` não é atingível (0,28; síntese autoral
  até 0,77). Como seguir? → A: recalibrar — par sintético para a camada estrutural (limiar 0,7
  mantido) e `guarda-barra-qualidade` como caso do juiz no teste `live` (FR-019, SC-004).

## Requirements *(mandatory)*

### Functional Requirements

**Execução e seleção**

- **FR-001**: O praxisforge MUST oferecer a triagem de uma pasta por alias ou de todas as pastas
  inventariadas (`--all`), mutuamente exclusivos. Pastas com status `ignore` no registro são
  puladas, como no inventário.
- **FR-002**: A triagem MUST processar só artefatos elegíveis: `pending`; `failed` abaixo do
  limite de tentativas; e `triaged`/`drafted` produzidos com versão de prompt ou critérios
  diferente da atual (FR-020). Artefatos `reviewed`, `promoted`, `discarded` e `removed` MUST
  NOT ser enviados ao modelo.
- **FR-003**: A triagem MUST exigir inventário prévio e recusar pasta nunca inventariada com
  mensagem que indica o comando de inventário.
- **FR-004**: A ordem de processamento MUST ser determinística (por caminho relativo), para que
  execuções e retomadas sejam reproduzíveis.

**Chamada ao modelo (segurança)**

- **FR-005**: Toda chamada ao modelo MUST ser feita sem nenhuma ferramenta habilitada: nem
  execução de comandos, nem leitura ou escrita de arquivos, nem acesso à rede além da própria
  chamada. A entrada é só texto e a saída é só texto.
- **FR-006**: Só o praxisforge MUST gravar arquivos. Nenhum caminho, comando ou nome de arquivo
  vindo da resposta do modelo pode ser usado para decidir onde gravar; o destino é sempre
  derivado do alias e do caminho relativo do artefato.
- **FR-007**: Toda resposta MUST ser validada contra um contrato versionado (JSON Schema) antes
  de qualquer gravação. Resposta fora do contrato MUST ser tratada como falha do artefato.
  A validação que vale é a feita pelo praxisforge: uma validação do lado do CLI/modelo (saída
  estruturada) é conveniência e nunca substitui a do código.
- **FR-008**: O conteúdo do artefato MUST ser enviado ao modelo delimitado como dado e
  identificado como conteúdo de terceiros não confiável, separado das instruções.
- **FR-009**: Dois modelos MUST ser configuráveis: um para triagem e juiz (mais barato) e outro
  para rascunho. Ambos têm padrão definido e podem ser sobrescritos na execução.

**Isolamento e segurança (modelo de ameaça)**

- **FR-037**: Antes da primeira chamada, o praxisforge MUST verificar a versão do CLI `claude`
  contra a faixa testada (declarada no código, inicialmente `2.1.x` a partir de 2.1.283). Versão
  fora da faixa ou flag de isolamento recusado pelo CLI → a execução MUST falhar fechada (exit 3,
  nenhuma chamada), a menos que o curador passe `--allow-untested-cli`. Ampliar a faixa exige
  rodar o teste `live` de isolamento (SC-009).
- **FR-038**: Cada chamada MUST rodar com: nenhuma ferramenta nativa, nenhum servidor MCP, nenhuma
  setting de usuário/projeto/local (o que desliga hooks e permissões configurados), nenhuma skill
  ou slash command, sem persistência de sessão e com system prompt próprio. A única capacidade
  interna tolerada é a de saída estruturada (`StructuredOutput`), que só devolve dados ao
  praxisforge e não tem efeito colateral. A lista exata de flags MUST ser coberta por teste de
  regressão.
- **FR-039**: O processo do modelo MUST rodar num diretório temporário vazio, criado para a
  chamada e removido ao fim (inclusive em timeout ou erro), e MUST receber só as variáveis de
  ambiente necessárias à autenticação e à execução (`HOME`, `PATH`, `LANG`/`LC_*`, `TERM`,
  `TMPDIR`, `CLAUDE_CONFIG_DIR` se definida); as demais, incluindo segredos e `PRAXISFORGE_*`,
  MUST NOT ser repassadas.
- **FR-040**: O prompt MUST ser enviado pelo stdin do processo, e nunca como argumento de linha de
  comando.
- **FR-041**: O prompt MUST NOT conter caminho absoluto: o artefato é identificado por alias e
  caminho relativo.
- **FR-042**: Todo conteúdo de terceiros no prompt MUST ser delimitado como dado não confiável
  (FR-008): o artefato e o índice de rascunhos pendentes (que derivam de terceiros). Os itens do
  acervo `library/` são tratados como confiáveis (versionados e revisados). Do rascunho pendente,
  só entram no contexto o id, o tipo, o nome e a descrição, e nunca o corpo.
- **FR-043**: Os arquivos criados em `curation/` (estado, rascunhos, locks) MUST ter permissão
  `0600` e os diretórios `0700`. Se algum diretório ou arquivo de `curation/` for link
  simbólico, a execução MUST falhar com erro de ambiente (exit 3) antes de gravar.
- **FR-044**: Um rascunho corrompido ou fora do schema em `_drafts/` MUST interromper a execução
  antes da primeira chamada (exit 1), identificando o `draft_id`, porque ele entraria no contexto
  de outras triagens.

**Triagem**

- **FR-010**: Cada chamada de triagem MUST tratar um único artefato (C4).
- **FR-011**: O contexto de cada triagem MUST ser composto só de conteúdo do repositório: o índice
  do acervo (`library/INDEX.md`), o conteúdo completo de até 3 itens do acervo do mesmo tipo mais
  parecidos com o artefato (escolhidos sem modelo, por palavras-chave de nome e descrição) e os
  critérios versionados. Regras pessoais do curador ou arquivos fora do repositório MUST NOT
  entrar no contexto.
- **FR-011a**: O contexto de triagem MUST incluir também um índice dos rascunhos pendentes no
  staging de **todas** as pastas (nome, tipo, ideia central e identificador), atualizado a cada
  rascunho gravado na execução, para que uma ideia já rascunhada não gere outro rascunho.
- **FR-012**: O veredito MUST ser um de: `covered` (coberto), `gap` (lacuna) ou `out_of_scope`
  (fora de escopo), acompanhado de justificativa não vazia. `covered` MUST citar ao menos um item
  do acervo existente; um item citado que não existe **no catálogo real do acervo** (e não na
  lista enviada no prompt) torna a resposta inválida.
- **FR-013**: "Fora de escopo" MUST significar "não é conhecimento curável" (por exemplo: template
  de issue, changelog, tradução de outro artefato, arquivo de configuração de site), e não "tema
  distante do trabalho do curador": a base é agnóstica (A4).
- **FR-014**: O modelo de triagem MAY propor uma fusão com um item do acervo. Toda fusão MUST ser
  registrada como `gap` com o subtipo fusão e o item afetado (K3), para que passe pela aprovação
  na 012. O alvo da fusão MAY ser um item do acervo ou um rascunho pendente (FR-011a); fusão com
  rascunho pendente atualiza esse rascunho, acrescentando a nova origem à proveniência, em vez de
  criar outro.
- **FR-011b**: O contexto de cada chamada MUST respeitar limites determinísticos: artefato até
  256 KiB; itens parecidos do acervo até 96 KiB no total (entram inteiros, por ordem de
  similaridade, até caber); índice do acervo e índice de rascunhos pendentes até 64 KiB cada.
  Quando o índice de rascunhos excede o limite, entram primeiro os do mesmo tipo e depois os
  mais parecidos, com desempate por id, e o resumo da execução avisa que a deduplicação foi
  parcial.
- **FR-015**: Para artefatos `unknown`, a resposta de triagem MUST incluir o tipo sugerido entre
  os tipos do acervo.

**Rascunho e similaridade**

- **FR-016**: Todo artefato com veredito `gap` MUST receber um rascunho do modelo de rascunho:
  tipo, nome, descrição e corpo em pt-BR, com estrutura própria, apenas com ideias, sem trechos
  literais, tradução ou paráfrase próxima do original.
- **FR-015a**: A resposta do modelo MUST ter limites de tamanho no contrato: justificativa até
  2.000 caracteres, resumo de ideias até 4.000, descrição do rascunho até 1.024, corpo do
  rascunho até 64 KiB, `covered_by` com até 3 itens; o alvo de fusão MUST ter formato restrito
  (`<tipo>/<nome>` para item do acervo, 16 hex para rascunho). Nenhum campo da resposta entra em
  nome de arquivo.
- **FR-016a**: Quando a licença da pasta no registro for `link` ou `unknown`, a resposta de
  triagem com veredito `gap` MUST incluir um resumo não vazio das ideias do artefato, e o modelo
  de rascunho MUST receber só esse resumo (nunca o conteúdo original). Nesses casos, a verificação
  estrutural do FR-017 continua comparando o rascunho com o original.
- **FR-017**: Todo rascunho MUST passar por duas verificações antes de ser aceito: (a) estrutural,
  feita pelo código, que compara a sequência de títulos, a quantidade de itens de lista e de
  tabelas e a ordem dos passos com o original, e sinaliza quando a sobreposição é ≥ 0,7; (b) um
  juiz (modelo barato, sem ferramentas, com contrato validado) que responde se a proposta é
  tradução ou paráfrase próxima, com justificativa.
- **FR-018**: Um rascunho sinalizado por qualquer verificação MUST ser regenerado uma única vez com
  a instrução de reescrever pelas ideias. Se continuar sinalizado, MUST ser gravado com alerta de
  similaridade (qual verificação, pontuação e justificativa), e nunca descartado em silêncio.
- **FR-019**: O limiar estrutural (0,7) MUST ser configurável e MUST ter um teste de calibração
  com um par sintético versionado (original em inglês × tradução em pt-BR com a mesma estrutura),
  que MUST ser sinalizado pela camada estrutural. A `guarda-barra-qualidade` (derivada por
  adaptação, com estrutura reorganizada) é caso de calibração do **juiz**, no teste `live`: a
  camada estrutural não a distingue de uma síntese autoral (medição de 28/09/2026: 0,28 contra até
  0,77 de uma síntese autoral).

**Versionamento de prompts e critérios**

- **FR-020**: Os prompts (triagem, rascunho, juiz) e os critérios MUST ficar versionados no
  repositório. Cada veredito e rascunho MUST registrar a impressão digital (hash) do conjunto de
  prompts e critérios que o produziu. Mudança nessa impressão digital torna elegíveis para nova
  triagem os artefatos ainda não revisados (FR-002).
- **FR-021**: Prompt ou critério ausente ou vazio MUST impedir a execução antes da primeira
  chamada (erro de ambiente).

**Staging e estado**

- **FR-022**: Vereditos e rascunhos MUST ser gravados na área de staging da pasta, junto do estado
  da 010 (`<diretório do registro>/curation/<alias>/`), fora do repositório, com gravação atômica
  e validação de schema na escrita e na leitura.
- **FR-023**: Cada registro no staging MUST conter a proveniência: alias, caminho relativo e hash
  do artefato triado, modelo usado, impressão digital dos prompts/critérios, custo (quando
  conhecido) e data/hora com fuso `America/Sao_Paulo`.
- **FR-024**: O estado da 010 MUST ser atualizado a cada artefato concluído (e não só no fim),
  com as transições `pending → triaged → drafted`, ou `→ failed` com motivo e tentativas. O
  veredito da triagem MUST ficar em campo próprio, distinto do veredito da revisão (012). Uma
  interrupção a qualquer momento MUST perder no máximo o artefato em curso.
- **FR-025**: Um artefato reprocessado MUST ter o registro anterior no staging substituído, sem
  sobras que possam ser confundidas com o atual.

**Teto e retomada**

- **FR-026**: A execução MUST aceitar teto de chamadas e/ou teto de custo em US$. Sem teto
  informado, MUST valer um teto padrão de chamadas por execução. O teto é **por execução**,
  somando todas as pastas quando a execução é `--all`, e nunca por pasta.
- **FR-027**: Ao atingir o teto, a execução MUST concluir o artefato em curso, gravar o estado,
  sair com código próprio (4) e mostrar o comando de retomada.
- **FR-028**: Quando o modelo não informa custo, o teto em US$ MUST ser declarado não mensurável
  no resumo, e só o teto de chamadas é aplicado.
- **FR-029**: A retomada MUST continuar de onde a execução parou, sem reenviar artefatos já
  concluídos. Como o estado é gravado por artefato, a retomada é a própria regra de elegibilidade
  (FR-002) aplicada de novo.

**Robustez, saída e observabilidade**

- **FR-030**: Falha em um artefato (timeout, indisponibilidade, resposta inválida, tamanho) MUST
  NOT interromper o lote. Falhas MUST ser agregadas no resumo e registradas no estado.
- **FR-031**: A execução MUST parar após um número configurável de falhas de indisponibilidade
  consecutivas (padrão 5), gravando o estado, com código de falha de ambiente.
- **FR-032**: Cada chamada MUST ter timeout configurável.
- **FR-033**: O resumo final MUST mostrar, por pasta, a contagem por veredito, os rascunhos
  gravados, os rascunhos com alerta, as falhas, as chamadas, o custo e os restantes. Os caminhos
  exibidos MUST ser relativos à pasta; caminho absoluto MUST NOT aparecer na saída nem nos logs.
- **FR-034**: Os logs estruturados MUST registrar cada etapa (triagem, rascunho, juiz) por
  artefato, com resultado e tipo de erro, sem o conteúdo do artefato nem a resposta completa do
  modelo. A mesma restrição vale para stderr, mensagens de erro e exceções: da saída de erro do
  CLI, só a primeira linha é aproveitada, até 200 caracteres, sem caminhos absolutos.
- **FR-035**: Códigos de saída: 0 sucesso; 1 falha de lote ou de dados (alias inexistente, estado
  ou rascunho corrompido, falhas agregadas); 2 uso incorreto; 3 ambiente (modelo ausente, versão
  do CLI fora da faixa testada, prompt faltando, execução concorrente, falhas consecutivas, link
  simbólico em `curation/`); 4 teto atingido.
- **FR-036**: `curation status` (010) MUST passar a mostrar, por pasta, as contagens por veredito
  da triagem e os rascunhos com alerta.

### Key Entities

- **Veredito de triagem**: resultado da triagem de um artefato: tipo (`covered`, `gap`,
  `out_of_scope`), subtipo fusão (opcional, com item afetado), justificativa, itens do acervo
  citados, tipo sugerido (para `unknown`), resumo das ideias (licença `link`/`unknown`), modelo, impressão digital dos prompts, custo e data.
- **Rascunho**: proposta de item para o acervo derivada de uma lacuna: tipo, nome, descrição,
  corpo em pt-BR, proveniência (uma ou mais origens: alias, caminho, hash), resultado das duas verificações de
  similaridade e alerta, quando houver.
- **Verificação de similaridade**: pontuação estrutural (0–1) com os elementos comparados e o
  parecer do juiz (é ou não é tradução/paráfrase próxima, com justificativa).
- **Conjunto de prompts e critérios**: arquivos versionados no repositório (triagem, rascunho,
  juiz, critérios) e a impressão digital do conjunto.
- **Execução de triagem**: tetos, chamadas feitas, custo acumulado, falhas consecutivas e motivo
  de parada. Não é persistida; aparece no resumo.
- **Estado do artefato (010, estendido)**: etapa, tentativas, último erro, e agora o veredito de
  triagem e a impressão digital da versão que o produziu.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos artefatos elegíveis de uma pasta terminam a execução com veredito gravado
  ou em `failed` com motivo; nenhum fica sem registro, com ou sem teto.
- **SC-002**: Numa retomada após interrupção, 0 artefatos já concluídos são reenviados ao modelo.
- **SC-003**: Numa pasta em que só k artefatos mudaram desde a última triagem, a nova execução faz
  exatamente k chamadas de triagem.
- **SC-004**: 0 rascunhos gravados sem as duas verificações de similaridade registradas; o caso
  de calibração estrutural (par sintético original × tradução) é sinalizado, e o juiz sinaliza a
  `guarda-barra-qualidade` × origem no teste `live`.
- **SC-005**: Uma execução com teto de N chamadas nunca faz mais de N chamadas.
- **SC-006**: 0 arquivos são criados ou alterados fora da área de staging da pasta, qualquer que
  seja o conteúdo do artefato ou a resposta do modelo (verificado com artefatos que contêm
  instruções de *prompt injection*), incluindo o diretório de trabalho temporário do processo do
  modelo, que não existe mais ao fim da chamada.
- **SC-009**: Cada requisito de isolamento (FR-005, FR-037 a FR-042) tem ao menos um teste
  automatizado de falha correspondente, e o teste `live` de isolamento passa na versão do CLI
  declarada como testada.
- **SC-007**: O curador precisa ler só os artefatos com veredito "lacuna" (rascunhos) para decidir
  o que entra no acervo, e não o total inventariado. Na primeira pasta real triada, a revisão cabe
  numa sessão de trabalho.
- **SC-008**: Uma falha de indisponibilidade do modelo em 1 artefato não impede que os demais
  artefatos da pasta sejam triados.

## Assumptions

- O modelo é chamado pelo CLI `claude` instalado e autenticado na máquina do curador (assinatura),
  conforme C1. A forma de desabilitar ferramentas e obter saída JSON é definida no plano; se o CLI
  não permitir garantir "sem ferramentas", a feature não pode ser entregue como está (K4 é
  inegociável).
- Modelos padrão: um modelo da família mais barata para triagem e juiz e um modelo intermediário
  para o rascunho; nomes concretos e sobrescrita ficam no plano.
- Teto padrão sem opção: 50 chamadas por execução. Timeout padrão por chamada: 120 s. Tentativas
  por artefato: 3. Falhas consecutivas: 5.
- Tamanho máximo do artefato enviado: o limite de 256 KB já aplicado pelo inventário (arquivos
  maiores nem são artefatos).
- A área de staging é a indicada na entrada (`~/.config/praxisforge/curation/<alias>/`, junto do
  estado da 010), confirmada na clarificação de 28/09/2026 e substituindo o E1 do debate
  (`curation/<alias>/` no repositório): o repositório é público e o staging contém material ainda
  não revisado.
- O estado da 010 ganha campos novos (veredito da triagem e impressão digital). Se isso exigir nova
  versão de schema, a migração do estado existente faz parte desta feature.
- Os prompts ficam em `prompts/curation/` (triagem, rascunho, juiz e critérios), conforme C6.
- A revisão, a aprovação de lacunas e fusões, a promoção e o PR automático ficam na 012.
- Testes automatizados nunca chamam o modelo real: usam um modelo simulado atrás da mesma porta.
