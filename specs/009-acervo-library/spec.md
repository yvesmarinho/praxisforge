<!-- Criado em: 25/09/2026 11:40 -->
<!-- Modificado em: 25/09/2026 12:40 -->

# Feature Specification: Acervo `library/` por tipo de recurso

**Feature Branch**: `009-acervo-library`

**Created**: 25/09/2026

**Status**: Draft

**Input**: User description: "Feature 009 da curadoria automatizada (debate em docs/debates/curadoria-automatizada.md, 25/09/2026). O acervo deixa de ser só skills/ e passa a ser library/, com um diretório por tipo de recurso (skills, commands, agents, hooks, rules, references), um INDEX.md geral e um template por tipo; validação por tipo; migração de skills/ para library/skills/; remoção da publicação no escopo global (mantida a publicação em pastas de projeto); registro de fonte passa a admitir só extração de ideias (source-schema v3); emendas na constituição e ADRs. Fora de escopo: inventário, triagem por LLM, revisão e promoção (features 010–012)."

## Clarifications

### Session 2026-09-25

- Q: Que tipos de recurso podem ser publicados na pasta de um projeto? → A: Skills, commands,
  agents e rules; hooks e references não (references vão junto do item que as cita). O objetivo
  principal é a base de conhecimento; a publicação é secundária.
- Q: O que acontece com os comandos atuais `praxisforge skills validate|catalog|publish`? → A:
  Removidos; `skills ...` sai com erro de uso indicando o comando `library ...` equivalente.
- Q: Um item marcado como "reescrita pendente" pode ser publicado num projeto? → A: Pode; a
  marca é só informativa (aparece na validação e no índice).
- Q: Como os 2 registros de fonte atuais (v2) chegam ao novo formato? → A: Conversão manual
  única nesta feature; o validador recusa v2 com a mensagem de como converter.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Guardar e validar qualquer tipo de recurso no acervo (Priority: P1)

O curador quer guardar no repositório não só skills, mas também commands, agents, hooks, rules e
references. Ele cria o item a partir do template do tipo, preenche e pede a validação. O acervo
diz, por item, se está válido ou o que falta, sem que um item quebrado impeça a validação dos
outros.

**Why this priority**: é a base de tudo o que vem depois. Sem um lugar e um contrato para cada tipo,
a curadoria completa decidida no debate (A1) não tem onde gravar o resultado.

**Independent Test**: criar um item de cada tipo a partir dos templates, validar o acervo inteiro e
obter "6 ok"; quebrar um deles e obter "5 ok, 1 com falha" com o motivo.

**Acceptance Scenarios**:

1. **Given** um acervo com um item válido de cada um dos seis tipos, **When** o curador valida o
   acervo inteiro, **Then** todos são reportados como válidos e o comando termina com sucesso.
2. **Given** um command sem descrição e uma skill válida, **When** o curador valida o acervo,
   **Then** o command é reportado com o motivo, a skill é reportada como válida e o comando termina
   com código de falha de validação.
3. **Given** um item que cita uma fonte inexistente, **When** o curador valida o item, **Then** a
   falha cita a fonte ausente.
4. **Given** um item sem nenhuma fonte e sem a marca de autoral, **When** o curador valida o item,
   **Then** a validação falha exigindo fonte ou autoria.
5. **Given** um hook cuja pasta não tem o script referenciado pela sua definição, **When** o curador
   valida o hook, **Then** a falha cita o arquivo ausente.
6. **Given** o curador pede a validação só de um tipo (ex.: agents), **When** o comando roda,
   **Then** só os itens desse tipo são validados.

---

### User Story 2 - Migrar o acervo atual sem perder nada (Priority: P1)

O repositório já tem duas skills (`diretrizes-codificacao`, `guarda-barra-qualidade`) e o template
em `skills/`. Elas precisam passar para `library/skills/` com conteúdo, versão e histórico
preservados, e nada deve continuar lendo o local antigo.

**Why this priority**: sem a migração, o acervo fica dividido em dois lugares e as validações
divergem.

**Independent Test**: depois da migração, validar o acervo e obter as mesmas 2 skills válidas, com
conteúdo idêntico ao anterior; o diretório `skills/` não existe mais.

**Acceptance Scenarios**:

1. **Given** as 2 skills atuais em `skills/`, **When** a migração é aplicada, **Then** elas estão em
   `library/skills/` com conteúdo idêntico byte a byte, exceto a marca de reescrita pendente e o
   aumento de versão da `guarda-barra-qualidade` (FR-025) e o histórico do git as acompanha como
   renomeação.
2. **Given** o acervo migrado, **When** qualquer comando procura skills no local antigo, **Then**
   nenhum comando lê mais `skills/`.
3. **Given** um projeto onde uma skill foi publicada antes da migração, **When** o curador publica
   de novo, **Then** a publicação reconhece o item como publicado pelo praxisforge e o atualiza em
   vez de tratá-lo como de terceiro.

---

### User Story 3 - Índice geral do acervo (Priority: P2)

O curador e os agentes que consomem o acervo precisam de um ponto de entrada único: o
`library/INDEX.md`, com uma linha por item (tipo, nome, ideia central, versão, fontes). Ele
substitui o catálogo que hoje só lista skills.

**Why this priority**: é a "porta de entrada" do acervo e o contexto de comparação que a triagem
(feature 011) vai usar, mas o acervo funciona sem ele.

**Independent Test**: gerar o índice duas vezes seguidas sem mudança no acervo e obter arquivos
idênticos; alterar a descrição de um item e ver só a linha dele mudar.

**Acceptance Scenarios**:

1. **Given** um acervo com itens de vários tipos, **When** o índice é gerado, **Then** ele lista
   todos os itens válidos, agrupados por tipo e ordenados por nome.
2. **Given** o índice já gerado e nenhuma mudança no acervo, **When** ele é gerado de novo,
   **Then** o arquivo não muda.
3. **Given** um item inválido, **When** o índice é gerado, **Then** o item fica fora do índice e é
   reportado como omitido com o motivo.

---

### User Story 4 - Publicar em projetos, nunca no escopo global (Priority: P2)

O curador publica itens do acervo na pasta de um projeto (`<projeto>/.claude/...`). A publicação no
escopo global do usuário deixa de existir, conforme decidido no debate (D4/K1).

**Why this priority**: mantém a entrega de valor que já existe para skills, estende aos tipos que o
Claude Code consome por projeto e remove um caminho que foi rejeitado.

**Independent Test**: publicar uma skill, um command, um agent e uma rule num projeto temporário e
encontrar cada um no lugar esperado; pedir publicação global e receber recusa de uso.

**Acceptance Scenarios**:

1. **Given** itens válidos de tipos publicáveis, **When** o curador publica num projeto, **Then**
   cada item aparece no diretório do projeto correspondente ao seu tipo.
2. **Given** qualquer item, **When** o curador pede publicação no escopo global, **Then** o comando
   recusa com erro de uso e explica que só projetos são alvo.
3. **Given** um item de mesmo nome no projeto que não foi publicado pelo praxisforge, **When** o
   curador publica, **Then** o item de terceiro não é tocado e a recusa é reportada.
4. **Given** a publicação já feita e nenhuma mudança, **When** o curador publica de novo, **Then**
   nada muda no projeto.

---

### User Story 5 - Registro de fonte só com ideias (Priority: P3)

A partir desta feature, o praxisforge só extrai **ideias** das fontes (D1). O registro de fonte
deixa de ter níveis de extração; a licença continua registrada, como informação. Registros antigos
são convertidos, e o item derivado que já existe fica marcado para reescrita.

**Why this priority**: muda o contrato das fontes antes de a triagem automática existir, mas não
bloqueia a organização do acervo.

**Independent Test**: converter os 2 registros atuais para o novo formato e validá-los; um registro
no formato antigo é recusado com a indicação de conversão.

**Acceptance Scenarios**:

1. **Given** os registros de fonte atuais (formato v2), **When** a conversão é aplicada, **Then**
   eles passam no novo contrato sem perder origem, autor, data, licença e relevância.
2. **Given** um registro ainda no formato v2, **When** é validado, **Then** a validação falha
   indicando a conversão necessária.
3. **Given** a skill `guarda-barra-qualidade` (obra derivada), **When** o acervo é validado,
   **Then** ela continua válida, mas aparece sinalizada como "reescrita pendente" no relatório e no
   índice.

---

### Edge Cases

- Item num diretório de tipo que não existe (ex.: `library/prompts/x.md`): reportado como tipo
  desconhecido, sem derrubar a validação dos demais.
- Dois itens de tipos diferentes com o mesmo nome (ex.: skill `review` e command `review`):
  permitido, porque o nome é único **dentro do tipo**.
- Item cujo nome no conteúdo difere do nome do arquivo ou pasta: falha de validação.
- Hook sem descrição do evento que o dispara: falha de validação.
- Reference citada por uma skill mas ausente do acervo: falha na skill, citando a reference.
- Acervo vazio: validação e índice terminam com sucesso e reportam zero itens.
- `library/` ausente (ex.: clone antigo antes da migração): erro de ambiente com a indicação de
  migrar.
- Publicação de um tipo não publicável (hook, reference) pedida explicitamente: recusa de uso
  explicando o motivo.
- Arquivo ilegível no acervo: falha daquele item, lote continua.

## Requirements *(mandatory)*

### Functional Requirements

**Acervo e tipos**

- **FR-001**: O acervo MUST viver em `library/`, com um diretório por tipo: `skills`, `commands`,
  `agents`, `hooks`, `rules` e `references`.
- **FR-002**: Cada tipo MUST ter um formato definido e um template em `library/_templates/`; o
  formato de skills, commands, agents e rules MUST continuar aceito pelo Claude Code quando
  publicado.
- **FR-003**: Todo item MUST declarar nome, descrição, versão (semver) e proveniência (fontes
  citadas ou marca de autoral), no formato de metadados adequado ao seu tipo.
- **FR-004**: O nome MUST ser único dentro do tipo e igual ao nome do arquivo ou pasta do item
  (minúsculas, dígitos e hífens, até 64 caracteres).
- **FR-005**: Um hook MUST declarar o evento que o dispara, o que ele faz e os arquivos que
  executa; todos os arquivos referenciados MUST existir na pasta do hook.
- **FR-006**: Toda referência relativa dentro de um item (arquivos de apoio, references citadas)
  MUST existir.

**Validação**

- **FR-007**: O curador MUST poder validar o acervo inteiro, um tipo ou um item.
- **FR-008**: A validação MUST reportar cada item como válido ou com a lista de motivos, e a falha
  de um item MUST NOT impedir a validação dos outros.
- **FR-009**: Um item não autoral MUST citar ao menos uma fonte válida; cada fonte citada MUST
  existir e passar no contrato de fonte vigente.
- **FR-010**: A validação MUST terminar com código de sucesso só quando todos os itens pedidos forem
  válidos.

**Índice**

- **FR-011**: O índice `library/INDEX.md` MUST listar todos os itens válidos com tipo, nome, ideia
  central (descrição), versão, fontes e a sinalização de reescrita pendente quando houver.
- **FR-012**: A geração do índice MUST ser determinística: sem data no conteúdo, ordem fixa (tipo,
  depois nome) e resultado idêntico quando nada mudou.
- **FR-013**: Itens inválidos MUST ficar fora do índice e ser reportados como omitidos com o motivo.
- **FR-014**: O índice MUST substituir o catálogo atual de skills (`skills/README.md`).

**Migração**

- **FR-015**: As skills e o template atuais MUST ser movidos de `skills/` para
  `library/skills/` e `library/_templates/` com conteúdo idêntico (única exceção: FR-025),
  preservando o histórico como renomeação (`git log --follow` alcança os commits da 008). A
  migração é uma operação única registrada em commit, não um comando repetível.
- **FR-016**: Nenhum comando MUST continuar lendo `skills/` depois da migração.
- **FR-017**: Uma publicação feita antes da migração (cópia com marcador antigo ou symlink que
  aponta para `skills/`) MUST continuar sendo reconhecida como do praxisforge. O hash de conteúdo
  é calculado com caminhos relativos à pasta do item, então a mudança de local não altera o hash.
- **FR-017b**: Ao republicar um item cujo marcador está no formato antigo e cujo conteúdo e versão
  não mudaram, a publicação MUST só regravar o marcador no formato novo (sem tocar no conteúdo),
  reportando "marcador atualizado"; isso não conta como mudança de conteúdo para a regra de versão.
  Uma nova publicação logo em seguida MUST não mudar nada. Symlink antigo quebrado (alvo em
  `skills/`) MUST ser recriado apontando para `library/`.
- **FR-017a**: Os comandos `skills validate|catalog|publish` MUST ser removidos; invocá-los MUST
  resultar em erro de uso que indica o comando `library` equivalente.

**Publicação**

- **FR-018**: A publicação MUST aceitar apenas pastas de projeto como alvo; o alvo global MUST ser
  removido e seu uso MUST resultar em erro de uso com explicação. O praxisforge MUST NOT tocar no
  escopo global depois da migração; eventuais publicações globais anteriores (marcador
  `.praxisforge-skill.json` em `~/.claude/skills`) são removidas à mão, com instrução no guia.
  Em 25/09/2026 não existe nenhuma.
- **FR-019**: Skills, commands, agents e rules MUST ser publicáveis no diretório do projeto que o
  Claude Code lê para cada tipo; hooks e references MUST NOT ser publicáveis nesta feature (hooks
  exigem configuração do projeto; references acompanham os itens que as citam).
- **FR-020**: A publicação MUST continuar idempotente, só publicar itens válidos e nunca alterar um
  item de mesmo nome que não foi publicado pelo praxisforge.
- **FR-021**: Uma reference citada por uma skill publicada MUST ser publicada junto dela, como
  arquivo de apoio. Nesta feature só skills podem citar references (ver research R3).

**Fontes (só ideias)**

- **FR-022**: O contrato de registro de fonte MUST passar a uma nova versão major, sem níveis de
  extração: toda fonte é usada só pelas ideias; a licença continua obrigatória como informação.
- **FR-023**: Registros no formato anterior MUST ser recusados com mensagem que explica como
  convertê-los. Os registros existentes MUST ser convertidos nesta feature por edição única, sem
  comando de conversão permanente e sem perda de origem, autor, data, licença, relevância e status.
- **FR-024**: Um item MUST poder ser marcado como "reescrita pendente" (obra derivada anterior à
  regra de só ideias); a marca MUST aparecer na validação e no índice, sem invalidar o item.
- **FR-024a**: A marca de reescrita pendente MUST NOT bloquear a publicação; ela MUST ser só
  informativa.
- **FR-025**: A skill `guarda-barra-qualidade` MUST receber a marca de reescrita pendente na
  migração e, por ter o conteúdo alterado, a versão MUST subir para `1.0.1` (regra da 008: conteúdo
  diferente com a mesma versão é recusado na publicação).

**Governança**

- **FR-026**: A constituição MUST ser emendada: Princípio VI passa a tratar do acervo `library/`
  com todos os tipos e só publicação em projetos; Princípio V passa a registrar que só ideias são
  extraídas. As decisões MUST ser registradas em ADR.

### Key Entities

- **Item do acervo**: recurso reutilizável de um dos seis tipos. Atributos: tipo, nome, descrição,
  versão, fontes citadas ou marca de autoral, marca de reescrita pendente, arquivos de apoio.
- **Tipo de recurso**: skill, command, agent, hook, rule ou reference. Define o formato, os
  metadados, o template e se o item é publicável.
- **Registro de fonte**: origem de ideias usadas por itens do acervo. Atributos: origem, autor,
  data, licença (informativa), relevância, status. Sem nível de extração.
- **Índice do acervo**: visão gerada de todos os itens válidos; ponto de entrada do acervo.
- **Publicação**: cópia ou vínculo de um item do acervo no projeto, com marcação que identifica o
  praxisforge como autor da publicação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Os seis tipos de recurso podem ser guardados e validados; um item de cada tipo criado
  a partir do template passa na validação sem edição além dos campos do template.
- **SC-002**: 100% das skills existentes estão no novo acervo após a migração, com conteúdo
  idêntico, e nenhuma referência ao local antigo resta no código ou nos guias.
- **SC-003**: Gerar o índice duas vezes seguidas sem mudanças produz arquivos idênticos em 100% das
  execuções.
- **SC-004**: Validar um acervo de 200 itens (mistura de tipos) leva menos de 5 segundos.
- **SC-005**: Em um lote com itens inválidos, 100% dos itens válidos ainda são validados e
  reportados.
- **SC-006**: Nenhuma operação escreve fora de `library/` (validação e índice) e das pastas de
  projeto indicadas pelo curador (publicação).

## Assumptions

- Os formatos de commands, agents e rules seguem as convenções do Claude Code (Markdown com
  frontmatter), que admitem os metadados de proveniência do praxisforge sem quebrar o
  carregamento; o plano confirma os campos exatos.
- Hooks são guardados como pasta (definição do evento, script e documentação) só para curadoria e
  reuso manual; a ligação automática na configuração do projeto fica fora desta feature.
- O atalho `scripts/publish-skills` é renomeado ou ajustado para o acervo.
- O `library/INDEX.md` guarda só a descrição de cada item; a síntese de `CLAUDE.md`/`AGENTS.md` de
  terceiros (A3/K2) chega pela curadoria das features seguintes.
- Inventário, triagem por LLM, similaridade, revisão, promoção e refação das curadorias antigas
  são as features 010–012 e estão fora de escopo.
- A publicação em projetos mantém os modos já existentes (cópia e vínculo simbólico).
