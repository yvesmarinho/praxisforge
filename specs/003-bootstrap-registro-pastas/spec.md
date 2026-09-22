<!-- Criado em: 22/09/2026 16:30 -->
<!-- Modificado em: 22/09/2026 14:30 -->

# Feature Specification: Bootstrap do Registro de Pastas

**Feature Branch**: `003-bootstrap-registro-pastas`

**Created**: 22/09/2026

**Status**: Draft

**Input**: User description: "Bootstrap do registro de pastas: uma etapa que recebe uma
pasta-raiz como argumento, varre suas subpastas de primeiro nível, lê o README e o LICENSE de
cada uma para tentar preencher description e license automaticamente (heurística simples
reconhecendo licenças comuns: MIT, Apache-2.0, GPL-3.0, BSD-3-Clause; sem reconhecimento
confiável fica "unknown"/pendente), e gera/atualiza entradas em folders.yaml para cada subpasta
descoberta. Um novo status "ignore" é adicionado ao domínio/contrato para o curador marcar
manualmente (via folders update) pastas que o sistema deve sempre pular nas próximas execuções
do bootstrap e da varredura. O bootstrap nunca marca nada como ignore sozinho — é sempre decisão
manual posterior do curador."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerar o registro inicial a partir de uma pasta-raiz (Priority: P1)

Como curador, quero apontar o bootstrap para uma pasta-raiz (ex.: `~/DevOps`) e ter cada subpasta
de primeiro nível automaticamente registrada em `folders.yaml`, com descrição e licença já
preenchidas quando possível, para não precisar rodar `folders add` manualmente uma vez para cada
uma das dezenas de pastas que já tenho.

**Why this priority**: é o valor central da feature — sem isso o bootstrap não existe, só a
descoberta/relatório que já foi descartada em favor deste registro automático.

**Independent Test**: apontar o bootstrap para uma pasta-raiz de teste com 3 subpastas (uma com
README+LICENSE MIT reconhecível, uma com README mas sem LICENSE, uma sem nenhum dos dois), rodar
e confirmar que as 3 aparecem em `folders.yaml`, cada uma com os campos coerentes ao que tinha
disponível (cenários 1-4).

**Acceptance Scenarios**:

1. **Given** uma pasta-raiz com uma subpasta contendo um `README` e um `LICENSE` cujo texto é
   reconhecido por uma das licenças suportadas (MIT, Apache-2.0, GPL-3.0, BSD-3-Clause), **When**
   o curador roda o bootstrap apontando para essa raiz, **Then** a subpasta é registrada com a
   `description` extraída do início do README, a `license` identificada e o `status` inicial
   coerente com o schema (`not_scanned`, já que a licença é conhecida).
2. **Given** uma subpasta com `README` mas sem `LICENSE` (ou com um `LICENSE` cujo texto não é
   reconhecido por nenhuma licença suportada), **When** o bootstrap roda, **Then** a subpasta é
   registrada com `license: unknown` e `status: pending` (mesma invariante já validada pelo
   schema desde a feature 001).
3. **Given** uma subpasta sem `README` nem `LICENSE`, **When** o bootstrap roda, **Then** a
   subpasta ainda é registrada (o registro não é bloqueado pela ausência desses arquivos), com uma
   `description` padrão indicando que não havia README para extrair, e `license: unknown`/status
   `pending`.
4. **Given** uma pasta-raiz sem nenhuma subpasta de primeiro nível, **When** o bootstrap roda,
   **Then** a operação conclui sem erro, relatando 0 pastas registradas.

---

### User Story 2 - Rodar o bootstrap de novo sem duplicar ou perder curadoria manual (Priority: P1)

Como curador, quero poder rodar o bootstrap de novo (ex.: depois de clonar mais repositórios
dentro da pasta-raiz) sem que isso sobrescreva o trabalho de curadoria que já fiz manualmente em
pastas já registradas.

**Why this priority**: sem idempotência, o bootstrap é perigoso de rodar mais de uma vez — mesmo
prioridade da primeira execução, porque é o mesmo comando usado nos dois casos.

**Independent Test**: rodar o bootstrap duas vezes seguidas sobre a mesma raiz, alterando
manualmente `content_type`/`status` de uma pasta entre as duas execuções, e confirmar que a
segunda execução não reverte essa mudança manual, mas ainda registra subpastas novas que
apareceram entre uma execução e outra (cenário 5).

**Acceptance Scenarios**:

1. **Given** uma pasta já registrada (por uma execução anterior do bootstrap ou por `folders add`
   manual), **When** o bootstrap roda de novo sobre a mesma raiz, **Then** essa pasta **não** tem
   `description`, `license`, `content_type` ou `status` sobrescritos — o bootstrap só adiciona
   pastas **novas** que ainda não existem no registro, nunca modifica uma já existente.
2. **Given** uma pasta com `status: ignore` (marcada manualmente numa execução anterior), **When**
   o bootstrap roda de novo, **Then** essa pasta é pulada — nem reprocessada, nem removida do
   registro.

---

### User Story 3 - Marcar uma pasta para ser sempre ignorada (Priority: P2)

Como curador, quero marcar uma pasta como "ignore" (ex.: uma pasta técnica irrelevante, tipo cache
ou dependências) para que nem o bootstrap nem a varredura voltem a mexer nela nas próximas
execuções.

**Why this priority**: refinamento de usabilidade sobre US1/US2 — sem isso o curador teria que
apagar a pasta do registro manualmente toda vez que uma nova execução a redescobrisse (o que nem
seria possível, já que US2 já impede reprocessamento de pastas existentes; mas antes da primeira
marcação, ela ainda seria candidata normal).

**Independent Test**: registrar uma pasta, marcá-la como `ignore` via `folders update --status
ignore`, rodar `folders scan --all` e confirmar que ela é pulada (não gera falha nem tentativa de
resolução de caminho) e aparece separadamente no resumo como ignorada (cenário 6).

**Acceptance Scenarios**:

1. **Given** uma pasta com `status: ignore`, **When** o curador roda a varredura em lote (feature
   002), **Then** essa pasta é pulada — não entra na contagem de "ok" nem de "falha", aparece
   contada separadamente como "ignorada" no resumo.
2. **Given** uma pasta com qualquer outro status, **When** o curador a atualiza para `status:
   ignore` via `folders update`, **Then** a mudança é aceita independentemente da licença atual
   (inclusive licença `unknown`, sem exigir que ela primeiro esteja `pending`).

---

### Edge Cases

- O que acontece se duas subpastas diferentes, depois de "slugificar" o nome para virar alias,
  colidirem no mesmo alias (ex.: `Meu-Repo` e `meu_repo`)? → a segunda é reportada como falha
  individual (mesmo padrão de isolamento de falha por item da feature 002), sem impedir o
  registro das demais; o curador resolve manualmente o conflito de nome depois.
- O que acontece com um nome de subpasta que não é um alias válido mesmo depois de slugificado
  (ex.: começa com dígito, ou fica vazio depois de remover caracteres especiais)? → reportado como
  falha individual pelo mesmo motivo acima, sem interromper o bootstrap das demais.
- O que acontece se o README for muito grande? → só as primeiras linhas (até um limite razoável de
  caracteres) são usadas como `description`, nunca o arquivo inteiro — a descrição do contrato já
  limita a 500 caracteres (schema desde a feature 001).
- O que acontece com um link simbólico como subpasta de primeiro nível? → tratado como as demais
  pastas resolvidas por caminho real (mesma regra da feature 002); se o link estiver quebrado, é
  reportado como falha individual.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE receber uma pasta-raiz como argumento explícito em cada execução
  (nenhuma raiz fixa em configuração).
- **FR-002**: O sistema DEVE identificar as subpastas de primeiro nível dentro da pasta-raiz como
  candidatas a registro (mesma regra de "só diretórios, sem recursão" já usada em decisões
  anteriores do projeto).
- **FR-003**: Para cada subpasta candidata que **ainda não existe** no registro, o sistema DEVE
  criar uma nova entrada com um alias derivado do nome da subpasta.
- **FR-004**: O sistema NÃO DEVE alterar nenhum campo de uma pasta **já registrada** (por execução
  anterior do bootstrap ou por `folders add` manual) — o bootstrap só adiciona pastas novas.
- **FR-005**: O sistema DEVE pular (não processar, não registrar, não reportar como falha)
  qualquer pasta cujo alias correspondente já exista no registro com `status: ignore`.
- **FR-006**: Ao registrar uma nova pasta, o sistema DEVE tentar extrair a `description` a partir
  do início do arquivo README da subpasta, se ele existir; se não existir, DEVE usar uma
  descrição padrão indicando a ausência de README.
- **FR-007**: Ao registrar uma nova pasta, o sistema DEVE tentar identificar a `license` a partir
  do texto do arquivo LICENSE da subpasta, reconhecendo pelo menos MIT, Apache-2.0, GPL-3.0 e
  BSD-3-Clause; quando o arquivo não existir ou o texto não for reconhecido com confiança, a
  `license` DEVE ficar `unknown` (e o `status` correspondente `pending`, conforme a invariante já
  validada pelo contrato desde a feature 001).
- **FR-008**: Um alias cuja derivação do nome da subpasta resultar em conflito com um alias já
  existente, ou em um alias que não atende ao formato válido, DEVE ser reportado como falha
  individual, sem interromper o registro das demais subpastas (isolamento de falha por item,
  mesmo padrão da feature 002).
- **FR-009**: O sistema DEVE reportar, ao final da execução, um resumo com a contagem de pastas
  novas registradas, pastas já existentes puladas (inalteradas), pastas ignoradas (`status:
  ignore`) e falhas individuais.
- **FR-010**: O domínio e o contrato (schema) DEVEM passar a aceitar um novo valor de status,
  `ignore`, além dos cinco já existentes (`not_scanned`, `scanned`, `in_curation`, `curated`,
  `pending`).
- **FR-011**: O status `ignore` DEVE poder ser aplicado a uma pasta com licença `unknown` sem
  exigir que ela seja `pending` — ou seja, a invariante "licença `unknown` ⇒ status `pending`" da
  feature 001 passa a admitir `pending` OU `ignore`.
- **FR-012**: O bootstrap NÃO DEVE, em nenhuma circunstância, atribuir `status: ignore`
  automaticamente a nenhuma pasta — esse status só é aplicado manualmente pelo curador, via
  `folders update`.
- **FR-013**: A varredura (feature 002, `folders scan --all`) DEVE pular pastas com `status:
  ignore` — não tentar resolver o caminho nem contá-las como "ok" ou "falha"; DEVE contá-las
  separadamente como "ignoradas" no resumo.
- **FR-014**: Nenhuma saída do bootstrap (mensagens, logs, relatório) DEVE conter caminho absoluto
  do sistema de arquivos, exceto quando explicitamente citando o caminho de uma subpasta em uma
  mensagem de erro sobre aquela própria subpasta (mesma regra das features 001/002).

### Key Entities *(include if feature involves data)*

- **Pasta registrada** (já existente, feature 001): ganha um sexto valor possível de `status`,
  `ignore`. Nenhum campo novo é adicionado à entidade.
- **Resultado de bootstrap**: pasta-raiz de origem, contagem de novas/puladas/ignoradas/falhas,
  lista de falhas individuais (alias candidato + motivo). Não é persistido como entidade própria
  — só reflete no `folders.yaml` (novas entradas) e existe como saída de relatório da execução.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um curador consegue popular o registro inicial de dezenas de pastas em uma única
  execução, sem rodar `folders add` manualmente para cada uma.
- **SC-002**: Rodar o bootstrap duas vezes seguidas sobre a mesma pasta-raiz sem mudanças no
  filesystem produz o mesmo `folders.yaml` (idempotência) — nenhuma pasta já registrada é
  modificada na segunda execução.
- **SC-003**: Em uma pasta-raiz com 50 subpastas onde 40 têm README+LICENSE reconhecíveis e 10
  não têm nenhum dos dois, as 50 são registradas com sucesso (as 10 como `unknown`/`pending`),
  sem interromper a execução.
- **SC-004**: Uma pasta marcada `ignore` nunca é reprocessada pelo bootstrap nem pela varredura em
  execuções subsequentes, até que o curador mude o status manualmente.
- **SC-005**: Nenhuma execução do bootstrap expõe caminho absoluto do sistema de arquivos fora do
  contexto de uma mensagem de erro sobre a própria subpasta.

## Assumptions

- A extração de `description` a partir do README usa as primeiras linhas de texto útil (ignorando
  cabeçalhos Markdown vazios/badges), truncada em até 500 caracteres (limite já imposto pelo
  contrato); o critério exato de "o que conta como início útil" é decisão técnica de
  `/speckit-plan`, não de produto.
- O reconhecimento de licença é por comparação de texto (heurística), não por biblioteca externa
  de identificação SPDX — mantém a filosofia de dependências mínimas do projeto; um texto de
  licença customizado ou muito alterado sempre cai em `unknown`, nunca é adivinhado.
- `content_type` de uma pasta registrada pelo bootstrap recebe um valor padrão genérico (ex.:
  `unclassified`) — inferir automaticamente o tipo de conteúdo está fora de escopo desta feature;
  o curador ajusta manualmente depois com `folders update` (quando esse campo aceitar edição via
  update — hoje só `status`/`last_scanned`/`license` são editáveis por `update`; se `content_type`
  também precisar virar editável, isso é uma decisão técnica de `/speckit-plan`).
- A derivação de alias a partir do nome da subpasta segue o mesmo padrão de validação já existente
  (`^[a-z][a-z0-9_]{1,62}$`); a slugificação exata (minúsculas, hifens/espaços viram `_`, etc.) é
  decisão técnica de `/speckit-plan`.
- O bootstrap é sempre disparado manualmente pelo curador (mesma filosofia das features 001/002);
  não há agendamento automático.
- Requer que as features 001 (registro) e 002 (varredura) já estejam implementadas e mergeadas.
