<!-- Criado em: 21/09/2026 15:55 -->
<!-- Modificado em: 21/09/2026 15:56 -->

# Feature Specification: Registro de Pastas a Curar e Contratos Versionados

**Feature Branch**: `001-registro-pastas-curadoria`

**Created**: 21/09/2026

**Status**: Draft

**Input**: User description: "Primeira feature da Fase 2 do PraxisForge: estrutura do repositório em camadas, contratos (schemas) versionados de fonte e de pasta, e registro das pastas a curar, com o primeiro registro `github_forks` e caminho resolvido por configuração externa."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar e consultar pastas a curar (Priority: P1)

Como curador do PraxisForge, quero manter um registro versionado das pastas que contêm material a curar (caminho, descrição, tipo de conteúdo, licença, data da última varredura e status de curadoria), para saber quais fontes existem e em que estado de curadoria cada uma está, sem depender da minha memória.

**Why this priority**: É a base de dados de todo o ciclo de curadoria. Sem saber quais pastas existem e seu status, nenhuma varredura, curadoria ou publicação é possível. Sozinha já entrega valor: um inventário confiável e versionado.

**Independent Test**: Registrar a pasta `github_forks` com todos os campos obrigatórios, listar o registro e ver a pasta com descrição, tipo, licença e status "não varrida" — sem que nenhuma outra funcionalidade exista.

**Acceptance Scenarios**:

1. **Given** um registro vazio, **When** o curador registra a pasta com alias `github_forks` e todos os campos obrigatórios, **Then** o registro passa a conter a pasta e ela aparece na listagem com descrição, tipo de conteúdo, licença e status de curadoria.
2. **Given** um registro com pastas, **When** o curador consulta uma pasta pelo alias, **Then** recebe todos os seus dados, exceto qualquer caminho absoluto.
3. **Given** um registro com o alias `github_forks`, **When** o curador tenta registrar outra pasta com o mesmo alias, **Then** o registro é recusado com uma mensagem que identifica o alias duplicado e o registro existente permanece inalterado.
4. **Given** uma pasta registrada, **When** o curador atualiza o status de curadoria ou a data da última varredura, **Then** apenas esses campos mudam e a alteração fica visível no histórico do repositório.

---

### User Story 2 - Resolver o caminho real da pasta por configuração externa (Priority: P1)

Como curador, quero que o registro guarde apenas um alias para cada pasta e que o caminho real seja resolvido por configuração do ambiente local, para que o repositório seja reproduzível em qualquer máquina e nunca exponha caminhos pessoais.

**Why this priority**: É requisito de proveniência e privacidade da constituição (caminho absoluto nunca no registro nem no código). Sem isso o registro não pode ser versionado com segurança.

**Independent Test**: Definir a configuração de ambiente para o alias `github_forks`, pedir a resolução do alias e obter o caminho real; remover a configuração e verificar que a resolução falha com mensagem clara.

**Acceptance Scenarios**:

1. **Given** uma pasta registrada e a configuração local definida para o seu alias apontando para uma pasta existente, **When** o caminho é resolvido, **Then** o caminho real é retornado.
2. **Given** uma pasta registrada sem configuração local para o seu alias, **When** o caminho é resolvido, **Then** a operação falha informando qual configuração está ausente, sem revelar caminhos de outras pastas.
3. **Given** a configuração local apontando para uma pasta que não existe ou não pode ser lida, **When** o caminho é resolvido, **Then** a operação falha informando o alias e o motivo (inexistente ou sem permissão), sem afetar as demais pastas do registro.
4. **Given** um registro que contém um caminho absoluto no lugar do alias, **When** o registro é validado, **Then** ele é rejeitado.

---

### User Story 3 - Validar registros contra contratos versionados (Priority: P2)

Como mantenedor, quero que o registro de pastas e o registro de fontes sejam validados automaticamente contra contratos versionados (com versão de contrato obrigatória em cada registro), para que dados inválidos sejam barrados antes de entrar no repositório e mudanças de formato sejam controladas por versão.

**Why this priority**: Garante a qualidade dos dados desde o início e habilita as fases seguintes (varredura, curadoria, publicação) a confiar no formato. Depende do registro (P1), mas pode ser entregue e testada isoladamente contra arquivos de exemplo.

**Independent Test**: Validar um registro de pastas correto (passa) e variações inválidas — sem versão de contrato, versão desconhecida, campo obrigatório ausente, licença vazia, status fora dos valores permitidos —, todas rejeitadas com mensagem que aponta o campo e o motivo.

**Acceptance Scenarios**:

1. **Given** um registro de pastas correto com versão de contrato, **When** é validado, **Then** a validação passa.
2. **Given** um registro sem versão de contrato ou com versão não suportada, **When** é validado, **Then** é rejeitado informando a versão encontrada e as suportadas.
3. **Given** um registro com campo obrigatório ausente ou valor fora do permitido, **When** é validado, **Then** todas as violações são listadas de uma vez, cada uma com o campo e o motivo.
4. **Given** um registro de fonte curada (proveniência) com licença ausente, **When** é validado, **Then** ele só é aceito com status "pendente" e é marcado como sem direito a extrato copiado.
5. **Given** registros de várias pastas em que uma é inválida, **When** o lote é validado, **Then** a falha de uma pasta é registrada e agregada sem impedir a validação das demais.

---

### User Story 4 - Estrutura do repositório em camadas com regras de dependência verificáveis (Priority: P3)

Como mantenedor, quero que o repositório tenha a estrutura de camadas definida (apresentação, aplicação, domínio, infraestrutura) e que as regras de dependência entre elas sejam verificadas automaticamente, para que a arquitetura não se degrade à medida que as próximas features chegam.

**Why this priority**: Prepara o terreno para as demais features, mas não entrega valor de curadoria por si só; pode ser entregue por último sem bloquear os fluxos P1 e P2.

**Independent Test**: Adicionar uma dependência proibida de teste (por exemplo, o domínio importando a infraestrutura) e verificar que a checagem automática falha apontando o arquivo e a regra violada; remover e ver passar.

**Acceptance Scenarios**:

1. **Given** a estrutura de camadas criada, **When** a verificação de dependências é executada, **Then** passa sem violações.
2. **Given** código de domínio que depende de infraestrutura, apresentação ou biblioteca externa, **When** a verificação é executada, **Then** falha indicando o módulo, a dependência proibida e a regra violada.

---

### Edge Cases

- Registro de pastas vazio ou arquivo ausente: tratado como "nenhuma pasta registrada" (vazio válido) ou erro explícito de arquivo ausente, conforme o caso, nunca como erro genérico.
- Arquivo do registro com formato corrompido (não interpretável): falha explícita indicando o arquivo e a posição do problema.
- Alias com caracteres inválidos, vazio, apenas espaços ou apenas maiúsculas/minúsculas diferentes de um alias existente (colisão): rejeitado.
- Data de última varredura no futuro ou em formato inválido: rejeitada.
- Status de curadoria com valor desconhecido: rejeitado com a lista de valores permitidos.
- Mesma pasta física registrada sob dois aliases: sinalizado como aviso, não como erro.
- Configuração local com caminho relativo, com `..` ou com link simbólico para fora da área esperada: tratado como caminho inválido e recusado.
- Pasta registrada mas com licença desconhecida: aceita apenas com status "pendente".
- Muitas pastas registradas (centenas): listagem e validação continuam usáveis (ver critérios de sucesso).
- Versão de contrato mais nova que a suportada pela ferramenta: rejeitada de forma explícita, sem tentativa de interpretação parcial.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST manter um registro versionado no repositório com as pastas a curar; cada pasta MUST ter alias único, descrição, tipo de conteúdo, licença, data da última varredura (ou ausência dela) e status de curadoria.
- **FR-002**: O sistema MUST permitir registrar, consultar, listar e atualizar (status e data da última varredura) pastas do registro.
- **FR-003**: O sistema MUST rejeitar alias duplicado (inclusive diferindo só por maiúsculas/minúsculas), vazio ou com caracteres fora do conjunto permitido, sem alterar o registro existente.
- **FR-004**: O sistema MUST NOT armazenar caminho absoluto no registro nem no código; o registro guarda apenas o alias, e um registro que contenha caminho absoluto no lugar do alias MUST ser rejeitado.
- **FR-005**: O sistema MUST resolver o caminho real de cada alias a partir de configuração do ambiente local e MUST falhar com erro específico e identificável quando a configuração estiver ausente, o caminho não existir ou não puder ser lido.
- **FR-006**: A falha de resolução ou validação de uma pasta MUST ser registrada e agregada, sem impedir o processamento das demais pastas do lote.
- **FR-007**: Todo registro estruturado (pastas e fontes) MUST carregar versão de contrato obrigatória e MUST ser validado contra o contrato versionado correspondente antes de ser aceito.
- **FR-008**: O sistema MUST rejeitar versão de contrato ausente ou não suportada, informando a versão encontrada e as suportadas.
- **FR-009**: A validação MUST reportar todas as violações de um registro de uma vez, cada uma com o campo e o motivo, em vez de parar na primeira.
- **FR-010**: O contrato de fonte curada MUST exigir proveniência (origem, data, licença, relevância); fonte sem licença registrada MUST ter status "pendente" e MUST NOT ser marcada como apta a gerar extrato copiado.
- **FR-011**: O contrato de pasta MUST restringir o status de curadoria a um conjunto fechado de valores e a data da última varredura a um formato de data válido e não futuro.
- **FR-012**: O registro inicial MUST conter a pasta `github_forks` com todos os campos obrigatórios válidos.
- **FR-013**: O repositório MUST ter a estrutura de camadas (apresentação, aplicação, domínio, infraestrutura), com diretórios para contratos, dados versionados e testes, e MUST verificar automaticamente as regras de dependência entre camadas (domínio sem dependência de frameworks, apresentação sem regra de negócio).
- **FR-014**: Erros MUST ser específicos e nomeados por significado (validação de contrato, alias duplicado, configuração ausente, caminho inacessível, versão não suportada), de modo que o registro de log e a mensagem ao usuário distingam falha de validação de falha de ambiente.
- **FR-015**: As operações de escrita no registro MUST ser idempotentes: repetir o mesmo registro ou a mesma atualização não altera o resultado nem duplica entradas.
- **FR-016**: As etapas críticas (leitura, validação, resolução, escrita) MUST gerar logs estruturados sem incluir caminhos absolutos, credenciais ou dados sensíveis.
- **FR-017**: Toda dependência externa desta feature (sistema de arquivos, configuração de ambiente) MUST ter comportamento definido e testado para indisponibilidade ou permissão negada.

### Key Entities *(include if feature involves data)*

- **Pasta a curar**: fonte de material bruto fora do repositório. Atributos: alias (identificador único e estável), descrição, tipo de conteúdo, licença, data da última varredura (opcional até a primeira varredura), status de curadoria. Não guarda caminho absoluto.
- **Registro de pastas**: coleção versionada de pastas a curar, com versão de contrato. Regras: aliases únicos; substituível por versão nova do contrato sem perda de dados.
- **Fonte curada**: item de conhecimento derivado de uma pasta, com proveniência (origem, data, licença, relevância) e status. Regra: sem licença registrada, status "pendente" e sem extrato copiado.
- **Contrato versionado**: definição formal e numerada do formato de um tipo de registro (pasta, fonte). Regra: mudança incompatível exige nova versão principal; mudança aditiva não.
- **Resolução de caminho**: associação, local a cada ambiente, entre um alias e o caminho real da pasta; nunca versionada.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O curador registra uma nova pasta e a vê listada com todos os seus dados em menos de 1 minuto, sem editar arquivos manualmente além dos seus dados.
- **SC-002**: 100% dos registros inválidos usados nos cenários de teste (sem versão, versão desconhecida, campo ausente, valor fora do permitido, alias duplicado, caminho absoluto) são rejeitados, e cada rejeição aponta o campo e o motivo.
- **SC-003**: Em um registro com 200 pastas, listagem e validação completas terminam em menos de 5 segundos em máquina de desenvolvimento comum.
- **SC-004**: Uma pasta inválida ou inacessível em um lote de 100 não impede que as outras 99 sejam processadas; o resumo final informa exatamente quais falharam e por quê.
- **SC-005**: Um clone limpo do repositório, apenas com a configuração local dos aliases, resolve `github_forks` em uma única etapa, sem nenhum caminho pessoal presente nos arquivos versionados (0 ocorrências em varredura do repositório).
- **SC-006**: A verificação de regras de dependência entre camadas detecta 100% das violações introduzidas de propósito nos testes (domínio importando infraestrutura, apresentação com regra de negócio).
- **SC-007**: A cobertura de testes das novas funcionalidades é de no mínimo 90%, com ao menos um cenário de falha para cada dependência externa.

## Assumptions

- O único usuário é o curador (Yves Marinho); não há controle de acesso por perfil nesta feature.
- O registro de pastas fica em `src/data/folders.yaml` e os contratos em `schemas/`, conforme decidido no objetivo-init (versão final, 18/09/2026); o primeiro alias é `github_forks`.
- O material bruto fica fora do repositório (`~/DevOps/github_forks`) e nunca é copiado para ele; o caminho real vem de configuração do ambiente local.
- Fora do escopo desta feature: varredura/coleta do conteúdo das pastas, curadoria e síntese, integração com provedores de IA, criação e publicação de skills. A data da última varredura e o status são apenas armazenados e atualizáveis aqui; quem os atualiza automaticamente é a feature de varredura (próxima).
- O conjunto de valores de status de curadoria será definido na fase de planejamento; assume-se ao menos: não varrida, varrida, em curadoria, curada, pendente.
- O registro é editado por um único curador por vez; conflitos de edição concorrente são tratados pelo controle de versão do repositório, não pela ferramenta.
- Aplicam-se os princípios da constituição v1.0.0: camadas, contratos versionados, test-first, erros semânticos, proveniência/licença e memória no vault.
- Dependência existente reaproveitada: o ambiente reprodutível e os gates de qualidade automáticos (lint, tipagem, testes com cobertura mínima de 90% e CI) já estão configurados no repositório.
