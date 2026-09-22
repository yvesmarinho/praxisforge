<!-- Criado em: 22/09/2026 11:39 -->
<!-- Modificado em: 22/09/2026 11:40 -->

# Feature Specification: Varredura das Pastas Registradas

**Feature Branch**: `002-varredura-pastas-curadoria`

**Created**: 22/09/2026

**Status**: Draft

**Input**: User description: "Varredura das pastas registradas: um scanner que percorre as pastas do
registro (via caminho resolvido pela feature 001), atualiza status de curadoria e última varredura,
e detecta quando a mesma pasta física está registrada sob dois aliases diferentes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Varrer uma pasta registrada (Priority: P1)

Como curador, quero rodar a varredura de uma pasta específica já registrada para confirmar que o
caminho continua acessível e atualizar quando ela foi verificada pela última vez, sem precisar
editar o registro manualmente a cada checagem.

**Why this priority**: é o valor mínimo entregável — sem isso não há "varredura" nenhuma, só o
`update` manual que a feature 001 já oferece. Habilita as demais user stories.

**Independent Test**: registrar uma pasta, apontar `PRAXISFORGE_FOLDER_<ALIAS>` para um diretório
real, rodar a varredura daquele alias e confirmar que `last_scanned` foi atualizado e o status
avançou de "não varrida" para "varrida" (spec cenários 1–4).

**Acceptance Scenarios**:

1. **Given** uma pasta registrada com status "não varrida" e caminho resolvível, **When** o curador
   varre o alias, **Then** o status muda para "varrida" e `last_scanned` recebe a data/hora atual.
2. **Given** uma pasta já "varrida", "em curadoria" ou "curada", **When** o curador a varre de novo,
   **Then** o status permanece o mesmo e só `last_scanned` é atualizado.
3. **Given** um alias não registrado, **When** o curador tenta varrê-lo, **Then** a varredura é
   recusada citando o alias, sem alterar o registro.
4. **Given** uma pasta registrada cujo caminho não resolve (variável ausente, caminho inválido,
   sem permissão), **When** o curador a varre, **Then** a varredura falha citando o motivo e o
   registro não é alterado.

---

### User Story 2 - Varrer todas as pastas em lote (Priority: P2)

Como curador, quero varrer todas as pastas registradas de uma vez, para manter o registro inteiro
atualizado sem repetir o comando pasta por pasta.

**Why this priority**: economiza trabalho manual repetitivo depois que a varredura individual (US1)
já existe; não é o mínimo necessário, mas é o uso real esperado no dia a dia.

**Independent Test**: registrar três pastas (duas com caminho válido, uma com caminho inválido),
rodar a varredura em lote e confirmar que as duas válidas são atualizadas e a inválida é reportada
como falha, sem interromper as demais (spec cenário 5).

**Acceptance Scenarios**:

1. **Given** um registro com várias pastas, **When** o curador roda a varredura em lote, **Then**
   cada pasta é varrida independentemente e o resultado final resume quantas foram atualizadas e
   quantas falharam, com o motivo de cada falha.
2. **Given** uma pasta com falha de caminho no meio do lote, **When** a varredura em lote roda,
   **Then** as demais pastas continuam sendo varridas normalmente (falha de uma não interrompe as
   outras — constituição IV).

---

### User Story 3 - Detectar a mesma pasta física sob dois aliases (Priority: P3)

Como curador, quero ser avisado quando dois aliases diferentes apontam para o mesmo caminho real,
para corrigir o registro (evitar duplicidade de curadoria da mesma pasta).

**Why this priority**: previne inconsistência de dados, mas depende da varredura (US1/US2) já
existir para ter caminhos resolvidos a comparar; tem menor frequência de ocorrência que as demais.

**Independent Test**: registrar dois aliases apontando (via variável de ambiente) para o mesmo
diretório real, rodar a varredura em lote e confirmar que o relatório final lista o par de aliases
duplicados, sem impedir a varredura das demais pastas (spec cenário 6).

**Acceptance Scenarios**:

1. **Given** dois aliases registrados cujos caminhos resolvem para o mesmo diretório real (após
   seguir eventuais links simbólicos), **When** o curador roda a varredura em lote, **Then** o
   relatório final lista os aliases duplicados lado a lado, sem impedir que ambos sejam varridos.
2. **Given** um único alias apontando para um caminho já varrido por outro alias em uma execução
   anterior, **When** a varredura em lote roda novamente, **Then** a duplicidade continua sendo
   reportada em toda execução até que o curador a resolva manualmente (a ferramenta não corrige
   sozinha, só avisa).

---

### Edge Cases

- O que acontece quando a variável de ambiente do alias aponta para um caminho que existia na
  varredura anterior mas foi removido/movido desde então? → tratado como falha de caminho (mesmas
  regras da feature 001: `FolderPathInvalidError`/`FolderPathUnreadableError`), sem alterar o
  registro daquela pasta.
- Como o sistema trata uma pasta cujo `status` já é "pendente" (licença desconhecida)? → a
  varredura ainda atualiza `last_scanned` (confirma que o caminho existe), mas o status permanece
  "pendente" — resolver a licença continua sendo ação manual (`folders update`).
- O que acontece se duas pastas apontam para caminhos diferentes que são, na verdade, o mesmo
  diretório acessado por caminhos distintos sem link simbólico (ex.: montagens/bind mounts)? →
  fora do escopo desta feature; a detecção de duplicidade compara apenas o caminho real resolvido
  (`Path.resolve()`), que já cobre o caso mais comum (link simbólico) coberto pela feature 001.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir varrer uma única pasta registrada pelo alias, atualizando
  `last_scanned` para a data/hora da varredura.
- **FR-002**: Ao varrer uma pasta com status "não varrida", o sistema DEVE avançar o status para
  "varrida"; para pastas em qualquer outro status (varrida, em curadoria, curada, pendente), o
  sistema DEVE manter o status atual e só atualizar `last_scanned`.
- **FR-003**: O sistema DEVE recusar a varredura de um alias não registrado, citando o alias, sem
  alterar o registro.
- **FR-004**: Quando o caminho de uma pasta não resolve (variável ausente, caminho inválido, sem
  permissão — reaproveitando as regras da feature 001), o sistema DEVE recusar a varredura daquela
  pasta citando o motivo, sem alterar seu registro.
- **FR-005**: O sistema DEVE permitir varrer todas as pastas registradas em uma única operação.
- **FR-006**: Na varredura em lote, a falha de uma pasta NÃO DEVE impedir a varredura das demais;
  o sistema DEVE agregar e reportar cada falha individualmente ao final.
- **FR-007**: O sistema DEVE reportar, ao final de qualquer varredura em lote, um resumo com a
  contagem de pastas atualizadas e de pastas com falha.
- **FR-008**: O sistema DEVE detectar quando dois ou mais aliases registrados resolvem para o
  mesmo caminho real (após seguir link simbólico) e reportar cada grupo de aliases duplicados.
- **FR-009**: A detecção de duplicidade NÃO DEVE impedir a varredura normal das pastas envolvidas;
  é apenas informativa, cabendo ao curador corrigir o registro manualmente.
- **FR-010**: Nenhuma saída da varredura (mensagens, logs, relatório) DEVE conter caminho absoluto
  do sistema de arquivos, exceto quando explicitamente citando o caminho de uma pasta em uma
  mensagem de erro sobre aquela própria pasta (mesma regra da feature 001, FR-004/FR-016).
- **FR-011**: A varredura NÃO DEVE alterar `description`, `content_type` ou `license` de nenhuma
  pasta — esses campos continuam sendo definidos manualmente via `folders add`/`folders update`.

### Key Entities *(include if feature involves data)*

- **Resultado de varredura (por pasta)**: alias, resultado (atualizada/falha), motivo da falha
  quando aplicável. Não é persistido como entidade própria — só reflete no `last_scanned`/`status`
  do registro existente (feature 001).
- **Grupo de aliases duplicados**: conjunto de dois ou mais aliases cujo caminho real resolvido é
  idêntico. Não é persistido; existe só como saída do relatório de uma execução da varredura em
  lote.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma pasta com caminho válido tem seu status e última varredura atualizados em uma
  única operação, sem exigir nenhuma edição manual do registro.
- **SC-002**: Em uma varredura de 200 pastas com 10 caminhos inválidos, as 190 restantes são
  atualizadas com sucesso e as 10 falhas são reportadas individualmente, sem interromper a
  execução (mesmo padrão de escala da feature 001, SC-003/SC-004).
- **SC-003**: 100% dos pares de aliases que apontam para o mesmo caminho real são detectados e
  reportados em uma varredura em lote.
- **SC-004**: Nenhuma execução da varredura expõe caminho absoluto do sistema de arquivos fora do
  contexto de uma mensagem de erro sobre a própria pasta.

## Assumptions

- A varredura reaproveita a resolução de caminho já validada pela feature 001
  (`PRAXISFORGE_FOLDER_<ALIAS>`, segue link simbólico, exige permissão de leitura); nenhuma nova
  fonte de caminho é introduzida.
- A varredura é iniciada manualmente pelo curador (comando/CLI); não há agendamento automático
  nesta feature.
- O escopo desta feature é confirmar acessibilidade e atualizar metadados de controle
  (`status`, `last_scanned`); inspecionar o conteúdo da pasta (contar arquivos, detectar tipo de
  conteúdo, sugerir `content_type`) fica para uma feature futura, se necessário.
- A detecção de duplicidade é feita a cada execução da varredura em lote (não é armazenada entre
  execuções); o curador é responsável por corrigir manualmente qualquer duplicidade reportada.
- Requer que a feature 001 (registro de pastas e resolução de caminho) já esteja implementada e
  mergeada — depende de `FolderRegistry`, `PathResolver` e dos erros semânticos de caminho já
  existentes.
