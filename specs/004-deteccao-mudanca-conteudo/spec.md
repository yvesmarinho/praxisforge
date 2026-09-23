<!-- Criado em: 23/09/2026 10:23 -->
<!-- Modificado em: 23/09/2026 11:49 -->

# Feature Specification: Detecção de mudança de conteúdo pós-curadoria

**Feature Branch**: `004-deteccao-mudanca-conteudo`

**Created**: 23/09/2026

**Status**: Draft

**Input**: User description: "Detecção de mudança de conteúdo pós-curadoria. Hoje last_scanned só confirma acessibilidade; uma pasta com status curated pode receber novos commits e continuar curated indefinidamente. Quando uma pasta registrada que é repositório git tiver o commit HEAD diferente do hash registrado na última curadoria, o sistema deve reverter automaticamente o status de curated para in_curation, forçando nova revisão. Requer registrar o hash do HEAD no momento em que a pasta é marcada como curated, e a verificação deve ocorrer na varredura (folders scan / scan --all). Pastas que não são repositórios git ficam fora do mecanismo por ora. Pastas com status ignore continuam puladas. Mudança de schema: decidir entre evolução aditiva da v1 ou folders-schema-v2. Não deve alterar pastas cujo status não seja curated."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar a versão curada ao concluir a curadoria (Priority: P1)

Ao marcar uma pasta como curada, o curador quer que o registro guarde automaticamente a
identificação da versão do conteúdo (commit atual do repositório) que foi revisada, sem
precisar informá-la manualmente.

**Why this priority**: Sem a versão de referência gravada, nenhuma mudança posterior pode ser
detectada — é o pré-requisito de toda a feature.

**Independent Test**: Marcar como curada uma pasta registrada que é repositório git e verificar
que o registro passa a conter a identificação do commit atual dela.

**Acceptance Scenarios**:

1. **Given** uma pasta registrada que é repositório git, **When** o curador altera seu status
   para curada, **Then** o registro grava a identificação do commit atual da pasta junto com o status.
2. **Given** uma pasta registrada que não é repositório git, **When** o curador a marca como
   curada, **Then** o status muda normalmente e nenhuma versão de referência é gravada.
3. **Given** uma pasta revertida para "em curadoria" com versão antiga gravada, **When** o curador
   conclui a nova revisão e a marca como curada, **Then** a versão gravada é atualizada para o
   commit atual e a próxima varredura informa "sem mudança".
4. **Given** uma pasta cujo caminho real não está acessível, **When** o curador tenta marcá-la
   como curada, **Then** a operação falha com mensagem clara e o registro não é alterado.

---

### User Story 2 - Reverter automaticamente pastas curadas que mudaram (Priority: P1)

Ao varrer as pastas (individualmente ou em lote), o curador quer que toda pasta curada cujo
conteúdo mudou desde a curadoria volte automaticamente para "em curadoria", para que não fique
considerada revisada quando não está.

**Why this priority**: É o valor central da feature — fecha a lacuna documentada em que uma
pasta curada fica desatualizada indefinidamente.

**Independent Test**: Registrar uma pasta curada com versão gravada, criar um novo commit nela,
varrer e verificar que o status passou a "em curadoria" e a saída informa a reversão.

**Acceptance Scenarios**:

1. **Given** uma pasta curada cujo commit atual difere do gravado, **When** o curador a varre,
   **Then** o status passa a "em curadoria" e a saída indica que houve reversão por mudança de conteúdo.
2. **Given** uma pasta curada cujo commit atual é igual ao gravado, **When** o curador a varre,
   **Then** o status permanece curada (apenas a data da última varredura é atualizada).
3. **Given** um lote com pastas curadas alteradas, inalteradas, ignoradas e em outros status,
   **When** o curador executa a varredura em lote, **Then** somente as curadas alteradas são
   revertidas, as ignoradas são puladas e as demais mantêm o status.
4. **Given** um lote em que a leitura do commit de uma pasta falha, **When** a varredura em lote
   roda, **Then** essa falha é reportada por item e as demais pastas são processadas normalmente.

---

### User Story 3 - Tratar pastas curadas sem versão de referência (Priority: P2)

Pastas marcadas como curadas antes desta feature não têm versão gravada. O curador quer que a
varredura lide com elas de forma previsível e visível.

**Why this priority**: Afeta apenas o registro legado; o mecanismo principal funciona sem isso,
mas o comportamento precisa ser definido para não gerar reversões ou silêncios inesperados.

**Independent Test**: Varrer uma pasta git curada sem versão gravada e verificar o
comportamento definido e a mensagem na saída.

**Acceptance Scenarios**:

1. **Given** uma pasta git curada sem versão gravada, **When** o curador a varre, **Then** o
   sistema grava o commit atual como versão de referência, mantém o status curada e informa
   isso na saída.
2. **Given** uma pasta git curada cuja referência foi gravada numa varredura anterior (cenário 1),
   **When** a fonte recebe novos commits e o curador varre de novo, **Then** o status passa a
   "em curadoria" (mesmo comportamento da User Story 2).

---

### Edge Cases

- Pasta curada que deixou de ser repositório git (ex.: `.git` removido): a varredura não reverte
  e informa que a verificação de conteúdo não pôde ser feita.
- Repositório git sem nenhum commit: mesmo tratamento de pasta não-git (FR-002) — não grava
  referência e a varredura informa "não é repositório git".
- Mudança apenas em arquivos não commitados (working tree suja): não conta como mudança de
  conteúdo — somente o commit atual é comparado.
- Commit atual anterior ao gravado (ex.: checkout de versão antiga): conta como mudança se o
  conteúdo da pasta difere entre os dois commits.
- Pasta em status diferente de curada com versão gravada remanescente: nunca é alterada pela verificação.
- Pasta ignorada: continua pulada na varredura em lote, sem verificação de conteúdo.
- Pasta que é subpasta de um repositório maior: commits novos que só alteram arquivos fora dela
  não revertem o status.
- Commit gravado que não existe mais no histórico (ex.: reescrita de histórico): conta como mudança e reverte.
- Duas pastas (aliases) apontando para o mesmo repositório: cada uma é verificada contra a sua própria versão gravada.
- Registro que contém versão gravada malformada: rejeitado na validação do registro, com mensagem clara.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST gravar no registro a identificação do commit atual de uma pasta git
  sempre que o status dela for alterado para curada.
- **FR-002**: O sistema MUST NOT gravar versão de referência para pastas que não são repositórios
  git ou que não têm commits; o status muda normalmente.
- **FR-003**: Ao marcar uma pasta como curada, se o caminho real não estiver acessível, o sistema
  MUST falhar sem alterar o registro.
- **FR-004**: A varredura individual e a em lote MUST comparar, para cada pasta curada com versão
  gravada, o commit atual com o gravado.
- **FR-005**: Quando os commits diferirem e algum commit entre o gravado e o atual tiver alterado
  arquivos dentro da própria pasta (a pasta pode ser a raiz ou uma subpasta do repositório), o sistema MUST alterar o status de curada para
  "em curadoria" e indicar a reversão na saída, identificando a pasta.
- **FR-006**: Quando os commits forem iguais, ou diferirem apenas por commits que não alteraram
  arquivos dentro da pasta, o sistema MUST manter o status curada.
- **FR-007**: O sistema MUST NOT alterar o status de pastas que não estejam curadas em decorrência
  da verificação de conteúdo.
- **FR-008**: Pastas ignoradas MUST continuar puladas na varredura em lote.
- **FR-009**: Falha na verificação de conteúdo de uma pasta — ferramenta git indisponível,
  verificação que excede 10 segundos, repositório corrompido ou recusado por permissão/propriedade
  — MUST deixar status, versão gravada e última varredura da pasta inalterados. Na varredura em
  lote, a falha é reportada por item e as demais pastas seguem; na varredura individual, a
  operação termina com erro de ambiente identificando a pasta e o motivo.
- **FR-010**: Ao sair do status curada por qualquer meio, a versão gravada MUST ser mantida no
  registro como histórico da última curadoria, e só é substituída quando a pasta for marcada como
  curada novamente.
- **FR-011**: A versão gravada MUST ser exibida na consulta de uma pasta, abreviada nos 12
  primeiros caracteres (ou "-" quando ausente), e validada pelo contrato do registro: 40 (SHA-1) ou
  64 (SHA-256) caracteres hexadecimais minúsculos.
- **FR-012**: A evolução do contrato do registro MUST ser aditiva: a versão gravada é opcional,
  nenhum campo existente muda e todo registro válido antes da feature continua válido sem ser
  reescrito.
- **FR-013**: A saída da varredura MUST NOT expor caminhos absolutos (mantém a regra das features anteriores).
- **FR-014**: Exceção explícita à FR-001 (único caso em que a versão é gravada fora do ato de
  marcar curada): na varredura, pastas git curadas sem versão gravada MUST receber o commit atual como
  versão de referência, sem alterar o status; a partir daí passam a seguir a FR-004/FR-005.
- **FR-016**: Ao marcar como curada uma pasta que não é repositório git (ou sem commits) e que já
  tem versão gravada, a versão existente MUST ser mantida sem alteração.
- **FR-017**: "Arquivos dentro da própria pasta" (FR-005) MUST considerar apenas arquivos versionados
  no próprio repositório sob o caminho da pasta; arquivos ignorados pelo git e o conteúdo interno de
  submódulos não contam (a mudança do commit apontado por um submódulo conta).
- **FR-018**: Cada linha de resultado da varredura MUST informar o alias, o status resultante e o
  resultado da verificação de conteúdo (não aplicável, não é repositório git, referência registrada,
  sem mudança, revertida) ou o motivo da falha.
- **FR-015**: A verificação de conteúdo (FR-004) MUST considerar apenas pastas atualmente curadas;
  uma versão gravada remanescente em pasta de outro status não dispara reversão.

## Clarifications

### Session 2026-09-23

- Q: Como tratar pastas curadas sem versão gravada (legado)? → A: a varredura grava o commit atual como referência e mantém curada; uma varredura posterior reverte quando a fonte for atualizada.
- Q: O que acontece com a versão gravada quando a pasta sai de curada? → A: é mantida como histórico da última curadoria.
- Q: Para pasta que é subpasta de um repositório maior, o que conta como mudança? → A: só commits entre o gravado e o atual que alteraram arquivos dentro da própria pasta.

### Key Entities

- **Pasta registrada**: ganha o atributo "versão da última curadoria" (identificação do commit
  revisado), opcional e presente apenas para pastas git marcadas como curadas.
- **Resultado de varredura**: passa a indicar se houve reversão por mudança de conteúdo, ou se a
  verificação de conteúdo não pôde ser feita (e por quê).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das pastas git curadas com arquivos alterados dentro da própria pasta desde a versão gravada são revertidas para "em curadoria" na primeira varredura após a mudança.
- **SC-002**: 0 pastas em status diferente de curada têm o status alterado pela verificação de conteúdo.
- **SC-003**: 0 pastas curadas inalteradas são revertidas (nenhum falso positivo).
- **SC-004**: Registros existentes antes da feature continuam válidos e carregam sem nenhuma edição manual.
- **SC-005**: Em um lote com uma pasta falhando na leitura do commit, 100% das demais pastas são processadas.
- **SC-006**: O curador identifica, só pela saída da varredura, quais pastas foram revertidas e por quê — 100% das linhas contêm os três dados da FR-018.

## Assumptions

- "Mudança de conteúdo" = arquivos da pasta diferentes entre o commit gravado e o atual; alterações não commitadas não contam.
- A verificação acontece apenas durante a varredura (`folders scan`), não em segundo plano.
- Pastas não-git ficam fora do mecanismo nesta feature.
- O curador marca como curada pelo fluxo existente de atualização de status; não há comando novo para isso.
- A decisão entre evolução aditiva do contrato v1 ou nova versão v2 fica para o plano, respeitando FR-012.
- A ferramenta git (versão 2.x) está instalada no ambiente de quem executa a varredura; sua
  ausência é tratada como falha de verificação (FR-009), não como pasta não-git.
- A pasta real é resolvida pelo mecanismo existente de aliases (variável de ambiente por alias).
