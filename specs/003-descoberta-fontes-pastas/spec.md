<!-- Criado em: 22/09/2026 16:00 -->
<!-- Modificado em: 22/09/2026 12:55 -->

# Feature Specification: Descoberta de Fontes dentro de Pastas Registradas

**Feature Branch**: `003-descoberta-fontes-pastas`

**Created**: 22/09/2026

**Status**: Draft

**Input**: User description: "Descoberta de fontes dentro de pastas registradas: ao varrer um
alias, listar as subpastas de primeiro nível dentro do caminho resolvido (ex.: cada repositório
forkado dentro de github_forks), reportando nome e contagem, sem registrar nada automaticamente —
é um relatório informativo que ajuda o curador a decidir quais subpastas registrar manualmente
como fontes em src/data/sources/. Prepara o terreno para a futura feature de
curadoria/proveniência (source-schema-v1.json já existe, mas ainda não há caso de uso que o
produza)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Listar subpastas de uma pasta registrada (Priority: P1)

Como curador, quero ver quais subpastas de primeiro nível existem dentro de uma pasta registrada
(ex.: `github_forks`) para decidir quais delas valem a pena registrar individualmente como fontes,
sem precisar abrir o gerenciador de arquivos ou rodar `ls` manualmente.

**Why this priority**: é o valor mínimo entregável — sem isso não existe "descoberta" nenhuma, só
a confirmação de acessibilidade que a varredura (feature 002) já oferece. Habilita a user story 2.

**Independent Test**: registrar uma pasta, apontar `PRAXISFORGE_FOLDER_<ALIAS>` para um diretório
com 3 subpastas e 1 arquivo solto, rodar a descoberta daquele alias e confirmar que as 3 subpastas
aparecem listadas (o arquivo solto não, cenários 1-3).

**Acceptance Scenarios**:

1. **Given** uma pasta registrada com 3 subpastas de primeiro nível, **When** o curador roda a
   descoberta daquele alias, **Then** o relatório lista os 3 nomes e a contagem total (3).
2. **Given** uma pasta registrada sem nenhuma subpasta (só arquivos soltos ou vazia), **When** o
   curador roda a descoberta, **Then** o relatório indica 0 subpastas encontradas, sem erro.
3. **Given** uma pasta registrada com subpastas e também arquivos soltos no mesmo nível, **When**
   o curador roda a descoberta, **Then** só as subpastas (diretórios) aparecem na lista — arquivos
   soltos são ignorados.
4. **Given** um alias não registrado, **When** o curador tenta descobrir suas subpastas, **Then**
   a operação é recusada citando o alias, sem tentar acessar nenhum caminho.
5. **Given** uma pasta registrada cujo caminho não resolve (mesmas regras da feature 001/002),
   **When** o curador roda a descoberta, **Then** a operação falha citando o motivo, sem listar
   nada.

---

### User Story 2 - Descobrir subpastas de todas as pastas registradas em lote (Priority: P2)

Como curador, quero rodar a descoberta sobre todas as pastas registradas de uma vez, para ter uma
visão consolidada de todos os candidatos a fonte antes de decidir o que registrar.

**Why this priority**: economiza trabalho repetitivo depois que a descoberta individual (US1) já
existe; segue o mesmo padrão de valor incremental da feature 002 (individual → lote).

**Independent Test**: registrar duas pastas (uma com subpastas válidas, outra com caminho
inválido), rodar a descoberta em lote e confirmar que a válida lista suas subpastas e a inválida é
reportada como falha, sem interromper a outra (cenário 6).

**Acceptance Scenarios**:

1. **Given** um registro com várias pastas, **When** o curador roda a descoberta em lote, **Then**
   cada pasta tem suas subpastas listadas separadamente, e o resultado final resume quantas pastas
   foram processadas com sucesso e quantas falharam (mesmo padrão de isolamento de falha por item
   da feature 002 — constituição IV).

---

### User Story 3 - Sinalizar subpastas já registradas como fonte (Priority: P3)

Como curador, quero que o relatório indique quais das subpastas descobertas já têm um registro de
fonte correspondente em `src/data/sources/`, para não perder tempo reavaliando o que já foi
curado.

**Why this priority**: é um refinamento de usabilidade — sem ele a descoberta ainda funciona (US1)
e o curador só perde um pouco de tempo comparando manualmente; não bloqueia o valor central.

**Independent Test**: registrar uma pasta com 2 subpastas, criar manualmente um arquivo de fonte
em `src/data/sources/` correspondente a uma delas, rodar a descoberta e confirmar que essa
subpasta aparece marcada como "já registrada" e a outra como "candidata" (cenário 7).

**Acceptance Scenarios**:

1. **Given** uma subpasta descoberta cujo nome corresponde a uma fonte já registrada em
   `src/data/sources/<categoria>/<slug>.md`, **When** o curador roda a descoberta, **Then** essa
   subpasta aparece marcada como já registrada, distinta das ainda não registradas ("candidatas").

---

### Edge Cases

- O que acontece com um link simbólico dentro da pasta registrada, apontando para outra subpasta
  ou para fora da árvore? → contado como subpasta normal na listagem (mesma decisão de resolver
  por caminho real já usada na feature 002 para links simbólicos do próprio alias); se o link
  estiver quebrado, é ignorado silenciosamente na listagem (não é uma falha da operação inteira).
- O que acontece se a pasta registrada tiver milhares de subpastas? → sem limite de paginação
  nesta primeira versão; a listagem completa é sempre reportada (mesma escala de centenas/milhares
  já assumida nas features 001/002).
- Nomes de subpastas duplicados entre pastas registradas diferentes (ex.: `repo-x` existe tanto
  dentro de `github_forks` quanto dentro de outro alias)? → tratados de forma independente; a
  correspondência com fontes já registradas (US3) usa o nome da subpasta mais o alias de origem,
  nunca o nome isolado, para evitar falso positivo entre pastas diferentes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE listar as subpastas de primeiro nível (diretórios, não arquivos)
  dentro do caminho resolvido de um alias registrado.
- **FR-002**: O sistema DEVE reportar a contagem total de subpastas encontradas junto com a lista
  de nomes.
- **FR-003**: O sistema NÃO DEVE listar arquivos soltos (não-diretórios) no primeiro nível.
- **FR-004**: O sistema NÃO DEVE descer recursivamente além do primeiro nível de subpastas.
- **FR-005**: O sistema DEVE recusar a descoberta de um alias não registrado, citando o alias, sem
  acessar nenhum caminho.
- **FR-006**: Quando o caminho de uma pasta não resolve (mesmas regras de erro semântico das
  features 001/002), o sistema DEVE recusar a descoberta daquela pasta citando o motivo.
- **FR-007**: O sistema DEVE permitir descobrir subpastas de todas as pastas registradas em uma
  única operação em lote.
- **FR-008**: Na descoberta em lote, a falha de uma pasta NÃO DEVE impedir a descoberta das
  demais; o sistema DEVE agregar e reportar cada falha individualmente ao final.
- **FR-009**: O sistema NÃO DEVE registrar, criar ou modificar automaticamente nenhum arquivo em
  `src/data/sources/` nem em `src/data/folders.yaml` como resultado da descoberta — é somente um
  relatório informativo; registrar uma fonte continua sendo uma ação manual do curador.
- **FR-010**: O sistema DEVE indicar, para cada subpasta descoberta, se já existe um registro de
  fonte correspondente em `src/data/sources/` (marcada como "já registrada") ou não ("candidata").
- **FR-011**: Nenhuma saída da descoberta (mensagens, logs, relatório) DEVE conter caminho
  absoluto do sistema de arquivos, exceto quando explicitamente citando o caminho de uma pasta
  registrada em uma mensagem de erro sobre aquela própria pasta (mesma regra das features
  001/002).

### Key Entities *(include if feature involves data)*

- **Resultado de descoberta (por pasta registrada)**: alias de origem, lista de subpastas
  encontradas (cada uma com nome e indicação se já está registrada como fonte), contagem total.
  Não é persistido como entidade própria — existe só como saída de uma execução da descoberta.
- **Subpasta candidata**: nome da subpasta + alias de origem + status (candidata ou já
  registrada). Não é persistida; a correspondência com `src/data/sources/` é recalculada a cada
  execução.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um curador consegue ver todas as subpastas de uma pasta registrada em uma única
  operação, sem precisar abrir um gerenciador de arquivos ou usar comandos de shell separados.
- **SC-002**: Em uma descoberta em lote de 50 pastas registradas com 5 caminhos inválidos, as 45
  restantes têm suas subpastas listadas com sucesso e as 5 falhas são reportadas individualmente,
  sem interromper a execução (mesmo padrão de escala das features 001/002).
- **SC-003**: 100% das subpastas que já têm fonte registrada correspondente são identificadas como
  "já registradas" no relatório, sem falso positivo entre pastas de origem diferentes.
- **SC-004**: Nenhuma execução da descoberta expõe caminho absoluto do sistema de arquivos fora do
  contexto de uma mensagem de erro sobre a própria pasta.

## Assumptions

- A descoberta reaproveita a resolução de caminho já validada pelas features 001/002
  (`PRAXISFORGE_FOLDER_<ALIAS>`, segue link simbólico, exige permissão de leitura); nenhuma nova
  fonte de caminho é introduzida.
- A correspondência entre subpasta descoberta e fonte já registrada (US3) é feita comparando o
  nome da subpasta (e o alias de origem) com o campo de identificação usado em
  `src/data/sources/<categoria>/<slug>.md` — o critério exato de correspondência (nome do arquivo
  `.md`, campo `origin` do frontmatter, ou ambos) fica a cargo da fase de planejamento técnico
  (`/speckit-plan`), não é uma decisão de produto.
- A descoberta é iniciada manualmente pelo curador (comando/CLI), assim como a varredura da
  feature 002; não há agendamento automático nesta feature.
- Esta feature não cria nenhum caso de uso de registro de fonte (isso continua sendo trabalho
  futuro, usando `source-schema-v1.json`, que já existe) — só descobre e reporta candidatos.
- Requer que as features 001 (registro de pastas) e 002 (varredura) já estejam implementadas e
  mergeadas — depende de `FolderRegistry`, `PathResolver` e dos erros semânticos de caminho já
  existentes.
