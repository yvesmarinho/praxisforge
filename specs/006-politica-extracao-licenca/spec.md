<!-- Criado em: 24/09/2026 10:31 -->
<!-- Modificado em: 24/09/2026 10:40 -->

# Feature Specification: Política de extração por licença

**Feature Branch**: `006-politica-extracao-licenca`

**Created**: 24/09/2026

**Status**: Draft

**Input**: User description: "Política de extração por licença (feature 006). Objetivo: o praxisforge compila informações de repositórios curados para uma base de conhecimento pública; a licença de cada fonte deve determinar o que pode ser reproduzido. Substituir o booleano `extract_allowed` do `source-schema-v1` por uma política explícita `extract_policy` com níveis `link` (só referência e metadados), `summary` (síntese com palavras próprias + citações curtas com autor e origem, amparadas na Lei 9.610/98 art. 46 III) e `verbatim` (cópia literal de trechos/arquivos, exigindo preservar aviso de copyright e texto da licença). A política máxima permitida é derivada da licença (tabela no domínio): MIT/BSD-3-Clause/Apache-2.0 → verbatim (Apache exige indicar alterações); GPL-3.0 → verbatim só para documentação, código copiado herda GPL (tratar como summary para código por padrão); Elastic-2.0 → summary (licença não livre); unknown/sem licença → link (status pending). A fonte pode declarar política mais restritiva que a máxima, nunca mais permissiva; violação é erro semântico. Toda fonte com extrato exige atribuição (origem, autor, licença). Registrar decisão em ADR 0007. Fora de escopo: aconselhamento jurídico, detecção automática de trechos copiados."

## Contexto

O praxisforge é um repositório **público**: todo extrato gravado em `src/data/sources/` é
redistribuído. Citar o originador não concede permissão de cópia — é a licença que concede. Hoje o
registro de fonte só tem um booleano (`extract_allowed`), que não distingue "posso resumir" de
"posso copiar literalmente", nem liga a decisão à licença. Esta feature torna a regra explícita,
derivada da licença e verificável por validação.

## Clarifications

### Session 2026-09-24

- Q: A licença de uma fonte deve ser conferida contra a licença da pasta registrada de onde ela veio? → A: Não — cada fonte declara a própria licença de forma independente, sem conferência com o registro de pastas.
- Q: Onde ficam os extratos em relação ao registro da fonte? → A: No mesmo arquivo: frontmatter com proveniência e política, corpo com notas e extratos; preservação de aviso de copyright/licença e indicação de alteração são campos declarados no frontmatter.
- Q: Licença fora da tabela: aceitar limitada a `link` ou rejeitar? → A: Aceitar com máxima `link`, em silêncio (sem aviso na validação).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validar a política declarada de cada fonte contra a licença (Priority: P1)

O curador escreve o registro de uma fonte (proveniência + notas/extratos) declarando a política de
extração que pretende usar. Ao validar os registros, o praxisforge rejeita toda fonte cuja política
declarada seja mais permissiva que a permitida pela licença, ou cujo extrato não traga a atribuição
exigida, informando a fonte, a licença, a política declarada e a máxima permitida.

**Why this priority**: é o núcleo da regra — impede que conteúdo sem permissão seja publicado no
repositório público. Sozinha já entrega valor (gate de validação local e no CI).

**Independent Test**: escrever registros de fonte com combinações licença × política e rodar a
validação de fontes; as combinações proibidas falham com mensagem que cita licença e máxima.

**Acceptance Scenarios**:

1. **Given** uma fonte MIT com política `verbatim` e atribuição completa, **When** as fontes são validadas, **Then** a validação passa.
2. **Given** uma fonte Elastic-2.0 com política `verbatim`, **When** as fontes são validadas, **Then** a validação falha informando que a máxima para Elastic-2.0 é `summary`.
3. **Given** uma fonte com licença `unknown` e política `summary`, **When** as fontes são validadas, **Then** a validação falha informando que a máxima é `link` e que a fonte deve estar `pending`.
4. **Given** uma fonte Apache-2.0 com política `link` (mais restritiva que a máxima), **When** as fontes são validadas, **Then** a validação passa.
5. **Given** uma fonte com política `summary` ou `verbatim` sem autor declarado, **When** as fontes são validadas, **Then** a validação falha por atribuição incompleta.
6. **Given** um lote com fontes válidas e inválidas, **When** as fontes são validadas, **Then** todas são avaliadas, as falhas são listadas por fonte e o resultado final indica falha.

---

### User Story 2 - Consultar a política máxima de uma pasta registrada (Priority: P2)

Antes de começar a curar uma pasta, o curador consulta o registro de pastas e vê, para cada pasta,
a política máxima de extração derivada da licença registrada — sabendo de antemão se pode copiar,
só resumir ou apenas referenciar.

**Why this priority**: orienta o trabalho de curadoria antes de escrever o registro da fonte;
depende só da tabela da US1.

**Independent Test**: listar/exibir pastas com licenças diferentes e conferir a política máxima
exibida para cada uma.

**Acceptance Scenarios**:

1. **Given** uma pasta registrada com licença MIT, **When** o curador exibe a pasta, **Then** vê a política máxima `verbatim`.
2. **Given** uma pasta com licença `unknown`, **When** o curador lista as pastas, **Then** a linha dela mostra política máxima `link`.
3. **Given** uma pasta com licença fora da tabela (ex.: `MPL-2.0`), **When** o curador exibe a pasta, **Then** vê política máxima `link` e a indicação de que a licença não está classificada.

---

### User Story 3 - Distinguir código de documentação em licenças copyleft (Priority: P3)

Para fontes GPL-3.0, o curador declara se o extrato é de documentação ou de código. Documentação
pode ser copiada literalmente; código copiado levaria a obrigação copyleft ao repositório, então
fica limitado a `summary`.

**Why this priority**: refinamento que só afeta fontes GPL; o comportamento conservador (tratar
tudo como código) já é seguro sem esta história.

**Independent Test**: validar fontes GPL-3.0 com política `verbatim` declarando escopo de
documentação (passa) e de código ou sem escopo (falha).

**Acceptance Scenarios**:

1. **Given** uma fonte GPL-3.0 com política `verbatim` e escopo de extrato "documentação", **When** as fontes são validadas, **Then** a validação passa.
2. **Given** uma fonte GPL-3.0 com política `verbatim` e escopo "código", **When** as fontes são validadas, **Then** a validação falha informando máxima `summary` para código.
3. **Given** uma fonte GPL-3.0 com política `verbatim` sem escopo declarado, **When** as fontes são validadas, **Then** o escopo é tratado como "código" e a validação falha.

---

### Edge Cases

- Licença declarada em caixa diferente (`mit`, `apache-2.0`): comparada sem diferenciar maiúsculas; o valor registrado é preservado.
- Licença fora da tabela (MPL-2.0, LGPL, CC-BY-4.0, proprietária): tratada como não classificada → máxima `link` (conservador); a validação não emite aviso por isso.
- Registro de fonte ainda no formato antigo (`extract_allowed`): rejeitado com mensagem indicando o novo campo; não há conversão automática (não existem fontes versionadas hoje).
- Política `verbatim` com licença que exige indicar alterações (Apache-2.0): a validação exige que o registro declare se houve alteração do trecho copiado.
- Fonte com política `link`: atribuição mínima (origem e licença) continua obrigatória; autor é opcional.
- Diretório de fontes vazio ou inexistente: validação reporta zero fontes sem erro (comportamento atual preservado para vazio; inexistente continua erro de uso).
- Valor de política desconhecido (ex.: `full`): falha de contrato antes da regra de licença.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O registro de fonte MUST declarar `extract_policy` com um de três níveis ordenados: `link` < `summary` < `verbatim`; o campo booleano `extract_allowed` deixa de existir.
- **FR-002**: O sistema MUST manter uma tabela única licença → política máxima: MIT, BSD-3-Clause e Apache-2.0 → `verbatim`; GPL-3.0 → `verbatim` para documentação e `summary` para código; Elastic-2.0 → `summary`; `unknown` → `link`.
- **FR-003**: Licença não presente na tabela MUST ser tratada como não classificada, com máxima `link`; a validação de fontes MUST NOT emitir aviso nem falha só por a licença não estar classificada (a indicação aparece apenas na consulta de pastas, FR-013).
- **FR-004**: A validação MUST rejeitar fonte cuja `extract_policy` seja mais permissiva que a máxima da licença, com erro semântico que informe fonte, licença, política declarada e política máxima.
- **FR-005**: Política mais restritiva que a máxima MUST ser aceita.
- **FR-006**: Fonte com licença `unknown` MUST estar com status `pending` e política `link`.
- **FR-007**: Fonte com política `summary` ou `verbatim` MUST declarar atribuição completa: origem, autor e licença.
- **FR-008**: Fonte com política `verbatim` MUST declarar, em campo do próprio registro, que o aviso de copyright e o texto da licença foram preservados junto ao extrato; a validação confere o campo declarado, não o conteúdo do corpo.
- **FR-009**: Fonte Apache-2.0 com política `verbatim` MUST declarar se o trecho copiado foi alterado.
- **FR-010**: Fonte GPL-3.0 MUST poder declarar o escopo do extrato (documentação ou código); ausência de escopo MUST ser tratada como código.
- **FR-011**: A comparação de licença com a tabela MUST ignorar maiúsculas/minúsculas.
- **FR-012**: A validação em lote MUST avaliar todas as fontes, agregar as falhas por fonte e sinalizar falha se houver ao menos uma (sem interromper no primeiro erro).
- **FR-013**: A exibição e a listagem de pastas registradas MUST mostrar a política máxima derivada da licença de cada pasta, indicando quando a licença não está classificada.
- **FR-014**: O contrato do registro de fonte MUST ganhar nova versão de schema (mudança incompatível), e registro na versão antiga MUST ser rejeitado com mensagem que aponte o novo campo.
- **FR-015**: A decisão (níveis, tabela, amparo legal da citação, critério conservador para licença não classificada) MUST ser registrada em ADR.
- **FR-016**: A documentação de operação MUST explicar os três níveis, a tabela e o que o curador pode gravar em cada nível.

### Key Entities

- **Política de extração**: nível ordenado (`link`, `summary`, `verbatim`) que define o que pode ser reproduzido de uma fonte no repositório público.
- **Tabela de licenças**: mapeamento licença → política máxima (com variação por escopo para copyleft); é a fonte única da regra.
- **Registro de fonte**: um único arquivo por fonte — metadados no cabeçalho e notas/extratos no corpo; proveniência de uma fonte curada — origem, autor, data, licença, relevância, status, política declarada, escopo do extrato (opcional), indicadores de preservação de aviso/licença e de alteração.
- **Pasta registrada** (existente): passa a expor a política máxima derivada da sua licença, sem novo campo persistido.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das combinações licença × política da tabela (5 licenças + não classificada × 3 níveis × escopos do GPL) têm resultado de validação coberto por teste e conforme a tabela.
- **SC-002**: Nenhuma fonte com política acima da máxima consegue passar pela validação local nem pelo gate do CI.
- **SC-003**: Toda falha de validação informa, na mesma mensagem, a fonte, a licença, a política declarada e a máxima — o curador corrige sem consultar a documentação.
- **SC-004**: O curador descobre a política máxima de qualquer pasta registrada com um único comando.
- **SC-005**: Validação de 500 registros de fonte conclui em menos de 5 segundos.

## Assumptions

- Não existem registros de fonte versionados hoje (`src/data/sources/` não existe), então a troca de `extract_allowed` por `extract_policy` não exige migração automática.
- A política é derivada da licença e não persistida no registro de pastas; o registro de pastas não muda de schema.
- A tabela cobre só as licenças já reconhecidas pelo bootstrap (MIT, Apache-2.0, GPL-3.0, BSD-3-Clause, Elastic-2.0) mais `unknown`; ampliar a tabela é mudança futura via ADR.
- "Citação curta" em `summary` é regra editorial para o curador (documentada), não verificada automaticamente.
- A licença do registro de fonte é declarada de forma independente e não é conferida contra a licença da pasta registrada; a responsabilidade pela licença correta é do curador.
- A regra é orientação técnica de conformidade, não aconselhamento jurídico.
- Fora de escopo: detecção automática de trechos copiados, verificação do conteúdo do extrato contra a fonte original, licenças por arquivo dentro de um mesmo repositório.
