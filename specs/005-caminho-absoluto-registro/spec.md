<!-- Criado em: 23/09/2026 12:52 -->
<!-- Modificado em: 23/09/2026 15:29 -->

# Feature Specification: Caminho absoluto no registro de pastas

**Feature Branch**: `005-caminho-absoluto-registro`

**Created**: 23/09/2026

**Status**: Draft

**Input**: User description: "Caminho absoluto no registro de pastas (constituição v2.0.0, Princípio V). Cada pasta em src/data/folders.yaml passa a ter um campo obrigatório com o caminho absoluto da pasta, que a identifica de forma única: duas entradas não podem apontar para o mesmo caminho real. Motivo: hoje o alias vem só do nome da subpasta e o caminho vem de variável de ambiente por alias, então duas subpastas homônimas de pastas-raiz diferentes colidem no bootstrap e manter uma variável por pasta não escala (registro local já tem 54 pastas). O bootstrap deve gravar o caminho absoluto de cada subpasta e gerar aliases distintos quando houver nomes repetidos. folders add passa a receber o caminho. resolve, scan, update --status curated e demais comandos passam a usar o caminho do registro. Decidir: destino das variáveis de ambiente, migração dos registros existentes sem caminho, versão do schema. Caminho absoluto continua proibido no código-fonte e restrito ao mínimo em logs/mensagens de erro."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar pastas com o caminho no próprio registro (Priority: P1)

O curador registra pastas (uma a uma ou em lote a partir de uma pasta-raiz) e o registro passa a
guardar onde cada pasta está, sem precisar configurar nada fora dele para localizá-la.

**Why this priority**: É a mudança central — sem o caminho no registro, nenhuma operação passa a
funcionar sem configuração externa por pasta.

**Independent Test**: Registrar uma pasta informando o caminho e, sem nenhuma configuração
externa, consultar, confirmar o caminho e varrer a pasta com sucesso.

**Acceptance Scenarios**:

1. **Given** uma pasta existente, **When** o curador a registra informando alias e caminho,
   **Then** o registro guarda o caminho absoluto normalizado da pasta.
2. **Given** um caminho relativo, com "~" ou com "..", **When** o curador registra a pasta,
   **Then** o caminho é convertido para a forma absoluta canônica antes de gravar.
3. **Given** um caminho inexistente ou que não é pasta, **When** o curador tenta registrar,
   **Then** o registro é recusado com mensagem clara e nada é gravado.
4. **Given** uma pasta já registrada sob outro alias (mesmo caminho real), **When** o curador
   tenta registrá-la de novo, **Then** o registro é recusado informando o alias existente.
5. **Given** uma pasta registrada, **When** o curador consulta, confirma o caminho, varre ou a
   marca como curada, **Then** a operação usa o caminho do registro sem configuração externa.
6. **Given** uma pasta registrada que foi movida, **When** o curador atualiza o caminho para o
   novo local, **Then** o caminho muda e status, licença e versão curada são preservados.
7. **Given** a pasta "/x/forks" registrada, **When** o curador tenta registrar "/x/forks/repo" (ou
   o inverso), **Then** o registro é recusado por aninhamento, citando o alias existente.
8. **Given** o caminho "/x/Forks/Repo" registrado, **When** o curador tenta registrar "/x/forks/repo",
   **Then** é recusado como duplicado.

---

### User Story 2 - Bootstrap sem colisão entre subpastas homônimas (Priority: P1)

Ao gerar o registro a partir de várias pastas-raiz, o curador quer que subpastas com o mesmo
nome em raízes diferentes sejam registradas como pastas distintas, cada uma com seu caminho.

**Why this priority**: É o problema que motivou a mudança — hoje a segunda subpasta homônima
falha por colisão de alias.

**Independent Test**: Fazer bootstrap de duas raízes que contêm uma subpasta de mesmo nome e
verificar que as duas ficam registradas, com aliases distintos e caminhos corretos.

**Acceptance Scenarios**:

1. **Given** duas raízes com uma subpasta de mesmo nome, **When** o curador executa o bootstrap
   em cada raiz, **Then** as duas subpastas são registradas com aliases distintos e cada uma
   com seu caminho absoluto.
2. **Given** uma subpasta já registrada (mesmo caminho), **When** o bootstrap roda de novo,
   **Then** ela é reconhecida como existente e não é duplicada nem alterada (idempotência).
3. **Given** uma pasta marcada como ignorada, **When** o bootstrap roda de novo sobre a raiz,
   **Then** ela continua ignorada e não é registrada outra vez.
4. **Given** uma raiz contendo duas subpastas cujos nomes geram o mesmo alias, **When** o
   bootstrap roda, **Then** ambas são registradas com aliases distintos.
5. **Given** uma raiz "github_forks" com a subpasta "graphify", **When** o bootstrap roda,
   **Then** o alias gerado é "github_forks__graphify".
6. **Given** duas raízes de mesmo nome ("/a/forks" e "/b/forks") com a subpasta "graphify",
   **When** o bootstrap roda nas duas, **Then** os aliases são "forks__graphify" e
   "forks__graphify_2".

---

### User Story 3 - Migrar o registro existente (Priority: P2)

O curador já tem pastas registradas sem caminho (inclusive 54 pastas geradas por bootstrap). Ele
quer levar esse registro para o novo formato sem recadastrar tudo à mão.

**Why this priority**: Necessário para não perder o trabalho já feito, mas só depois que o novo
formato existe.

**Independent Test**: Partir de um registro no formato antigo, executar a migração e verificar
que todas as pastas passam a ter caminho, com o registro válido no novo formato.

**Acceptance Scenarios**:

1. **Given** um registro no formato antigo, **When** o curador executa a migração, **Then** o
   caminho de cada pasta é obtido primeiro da variável de ambiente por alias que já existir e,
   na falta dela, de uma subpasta da pasta-raiz informada na migração cujo nome gere o mesmo
   alias; o caminho encontrado é gravado no registro.
2. **Given** pastas antigas cujo caminho não pode ser determinado, **When** a migração roda,
   **Then** elas são listadas como pendências por item, sem impedir a migração das demais, e o
   registro só é gravado quando todas tiverem caminho (nada fica em estado misto).
3. **Given** um registro já no formato novo, **When** a migração roda de novo, **Then** nada muda.
4. **Given** um registro no formato antigo, **When** o curador executa qualquer outro comando,
   **Then** recebe mensagem clara indicando que o registro precisa ser migrado.
5. **Given** um registro antigo com a pasta-raiz "github_forks" e subpastas dela registradas,
   **When** a migração roda, **Then** a entrada da raiz é removida e listada como
   "removida (pasta-raiz)", e as subpastas são migradas.

---

### Edge Cases

- Caminho que é link simbólico: o registro guarda o caminho real (link resolvido), para que duas
  entradas não apontem para a mesma pasta por caminhos diferentes.
- Pasta registrada que foi movida ou apagada depois: consulta continua funcionando; confirmar
  caminho, varrer e marcar curada falham para essa pasta com mensagem identificando o alias; o
  curador corrige com a atualização do caminho (FR-016).
- Caminho com espaços, acentos ou caracteres especiais: aceito e gravado sem alteração além da
  normalização.
- Duas entradas editadas à mão com o mesmo caminho: o registro é rejeitado na validação.
- Registro compartilhado entre máquinas diferentes: os caminhos refletem a máquina de quem mantém
  o registro (consequência aceita pela constituição v2.0.0).
- Nome de raiz + subpasta longo demais para um alias: truncado conforme FR-007, nunca falha.
- Alias gerado no bootstrap que já existe no registro para outro caminho: novo alias distinto é
  gerado, nunca sobrescreve o existente.

## Clarifications

### Session 2026-09-23

- Q: De onde vem o caminho das pastas já registradas na migração? → A: primeiro da variável de ambiente por alias existente; senão, da subpasta da raiz informada cujo nome normalizado bate com o alias; o resto vira pendência.
- Q: Como gerar alias distinto no bootstrap? → A: sempre prefixar com o nome da pasta-raiz ("<raiz>__<subpasta>").
- Q: O que acontece com as variáveis PRAXISFORGE_FOLDER_<ALIAS>? → A: deixam de ser consultadas; o caminho do registro é a única fonte (exceto na migração).
- Q: Pasta movida pode ter o caminho corrigido pela CLI? → A: sim, `update` aceita novo caminho com as mesmas validações; demais dados preservados.
- Q: Raízes de mesmo nome? → A: o sufixo numérico distingue ("forks__graphify_2").
- Q: Pastas aninhadas (uma dentro da outra)? → A: proibidas; a raiz não é registrada, só as subpastas; na migração a raiz registrada é removida.
- Q: Comparação de caminhos diferencia maiúsculas? → A: não.
- Q: E quando "<raiz>__<subpasta>" passa de 63 caracteres? → A: trunca a parte da subpasta mantendo o prefixo da raiz; colisão resultante recebe sufixo numérico.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada pasta do registro MUST ter um caminho absoluto obrigatório.
- **FR-002**: O caminho MUST ser gravado na forma absoluta canônica, obtida no momento do
  registro/atualização: "~" expandido para a pasta pessoal, caminho relativo resolvido a partir da
  pasta atual, segmentos "." e ".." eliminados, links simbólicos resolvidos até o destino real e
  sem barra final. Se um link mudar de destino depois, o registro continua com o destino gravado.
- **FR-003**: Duas pastas MUST NOT compartilhar o mesmo caminho, e nenhuma pasta registrada pode
  estar dentro de outra registrada (sem aninhamento: nem subpasta nem ancestral). A comparação MUST
  ignorar diferença entre maiúsculas e minúsculas. A mesma regra vale para registrar, bootstrap,
  atualizar caminho, migrar e carregar o registro (inclusive YAML editado à mão); a violação MUST
  informar o alias que já ocupa o caminho.
- **FR-004**: Registrar uma pasta MUST exigir o caminho e MUST recusar caminho inexistente, que
  não seja pasta, ou sem permissão para listar e entrar na pasta.
- **FR-005**: O bootstrap MUST gravar o caminho absoluto de cada subpasta registrada.
- **FR-006**: O bootstrap MUST reconhecer como existente uma subpasta cujo caminho já está
  registrado (idempotência por caminho, não por nome).
- **FR-007**: O bootstrap MUST formar o alias sempre como "<nome da pasta-raiz>__<nome da
  subpasta>", com cada nome normalizado pela regra atual do bootstrap (minúsculas; espaço e hífen
  viram "_"; demais caracteres fora de a-z, 0-9 e "_" removidos, inclusive acentos); nome que fique
  vazio ou comece com dígito recebe o prefixo "p"; as subpastas são processadas em ordem alfabética
  do nome, o que torna determinístico quem recebe cada sufixo; quando ainda assim o
  alias já estiver em uso para outro caminho (no registro ou na mesma execução),
  o bootstrap MUST acrescentar sufixo numérico ("_2", "_3", ...) até o alias ficar livre — é
  também o que distingue raízes de mesmo nome (ex.: "/a/forks" e "/b/forks"). O limite de 63
  caracteres MUST ser aplicado ao alias final já com o sufixo: trunca-se a parte da subpasta,
  preservando o prefixo da raiz, o separador "__" e o sufixo; nenhuma subpasta falha por tamanho.
- **FR-008**: Confirmar caminho, varrer, marcar curada e verificar conteúdo MUST usar exclusivamente
  o caminho do registro; as variáveis de ambiente por alias deixam de ser consultadas por esses
  comandos (única exceção: a migração, FR-014).
- **FR-014**: A migração MUST obter o caminho de cada pasta antiga, nesta ordem: (1) variável de
  ambiente por alias já existente; (2) subpasta de uma pasta-raiz informada pelo curador cujo nome
  normalizado seja igual ao alias. Pastas sem caminho encontrado são pendências (FR-011).
- **FR-015**: A migração MUST preservar o alias de cada pasta existente (a regra de formação da
  FR-007 vale só para pastas novas do bootstrap).
- **FR-009**: A mudança de formato do registro MUST ser tratada como incompatível: nova versão do
  contrato do registro, com a versão anterior reconhecida apenas para migração.
- **FR-010**: A migração MUST converter um registro antigo no novo formato preservando todos os
  demais dados de cada pasta (descrição, tipo, licença, status, última varredura, versão curada).
- **FR-011**: A migração MUST ser atômica (tudo ou nada) e idempotente, e MUST listar por item as
  pastas cujo caminho não pôde ser determinado.
- **FR-012**: Caminho absoluto MUST aparecer apenas no registro, na saída da consulta de uma pasta e
  do comando que confirma o caminho, e em mensagem de erro sobre a própria pasta com problema;
  demais saídas e logs MUST identificar pastas só pelo alias.
- **FR-016**: A atualização de uma pasta MUST aceitar um novo caminho, validado como na FR-004,
  canonizado (FR-002) e único (FR-003), preservando todos os demais dados (inclusive a versão
  curada) numa operação atômica.
- **FR-017**: A pasta-raiz informada ao bootstrap não é registrada como pasta; só as subpastas de
  primeiro nível são. Na migração, uma entrada antiga cujo caminho seja ancestral de outras
  entradas (ex.: a própria raiz registrada como pasta) MUST ser removida do registro e listada no
  relatório como "removida (pasta-raiz)".
- **FR-013**: A listagem de pastas MUST permitir ao curador ver o caminho de cada pasta.

### Key Entities

- **Pasta registrada**: ganha o atributo obrigatório "caminho" (absoluto, canônico, único no
  registro); o alias continua sendo o identificador curto usado nos comandos.
- **Registro de pastas**: passa a garantir unicidade de alias e de caminho; tem nova versão de
  contrato, com a anterior aceita só pela migração.
- **Relatório de migração**: pastas migradas e pastas pendentes (com motivo).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Bootstrap de duas raízes com subpastas homônimas registra 100% das subpastas, sem
  nenhuma falha por colisão.
- **SC-002**: Uma pasta registrada pode ser varrida e marcada como curada com zero configuração
  externa por pasta.
- **SC-003**: A migração do registro atual (54+ pastas) leva todas as pastas com caminho
  determinável ao novo formato em uma única execução, sem perda de nenhum outro dado.
- **SC-004**: 0 entradas duplicadas ou aninhadas por caminho são aceitas pelo registro, em
  qualquer ponto de entrada (registrar, bootstrap, atualizar, migrar, carregar).
- **SC-005**: Repetir bootstrap ou migração sem mudanças no disco não altera o registro — inclusive
  depois de uma pasta ter o caminho corrigido com a atualização (ela é reconhecida pelo novo caminho).
- **SC-006**: Nenhuma saída de varredura em lote ou log contém caminho absoluto.

## Assumptions

- O registro passa a ser específico da máquina de quem o mantém (constituição v2.0.0, Princípio V).
- O alias continua obrigatório, único e com o formato atual; só a forma de gerá-lo no bootstrap muda.
- Todos os campos e comportamentos das features 001–004 (status, licença, versão curada,
  verificação de conteúdo, ignore) são mantidos.
- A migração é um comando explícito executado pelo curador; nenhum comando migra silenciosamente.
