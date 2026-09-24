<!-- Criado em: 24/09/2026 11:25 -->
<!-- Modificado em: 24/09/2026 14:20 -->

# Feature Specification: Registro de pastas fora do repositório

**Feature Branch**: `007-registro-fora-do-repo`

**Created**: 24/09/2026

**Status**: Draft

**Input**: User description: "Registro de pastas fora do repositório (feature 007, constituição v3.0.0, Princípio V). O registro de pastas com caminhos absolutos deixa de ser src/data/folders.yaml versionado: local padrão $XDG_CONFIG_HOME/praxisforge/folders.yaml (fallback ~/.config/praxisforge/folders.yaml), substituível por --registry (maior precedência) e pela variável PRAXISFORGE_REGISTRY. O repositório (público) passa a versionar só src/data/folders.example.yaml, sem caminhos pessoais, validado no CI (make validate-data) e no guarda test_no_absolute_paths. Comandos que criam o registro (add, bootstrap) criam a pasta de configuração quando ausente; demais comandos com registro ausente mantêm o erro atual citando o local resolvido. Migração do registro local existente: mover src/data/folders.yaml populado para o novo local sem perder dados e sem sobrescrever registro já existente no destino. Documentar o local e a precedência. Fora de escopo: múltiplos registros simultâneos, sincronização entre máquinas."

## Contexto

O registro de pastas guarda caminhos absolutos da máquina do curador (feature 005). O repositório
é público, então versionar esse arquivo expõe a estrutura de diretórios pessoal, e hoje o guarda
de caminhos absolutos falha localmente sempre que o registro está populado. A constituição v3.0.0
(Princípio V) determina que o registro viva fora do repositório.

## Terminologia

- **Realocação do registro** (`folders relocate`): mover o arquivo do registro antigo para o novo
  local, sem mudar o formato. É o que esta feature entrega.
- **Migração de formato** (`folders migrate`, feature 005): converter um registro v1 em v2. Não
  muda nesta feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Usar o registro no local padrão fora do repositório (Priority: P1)

O curador roda qualquer comando de pastas sem informar onde está o registro, e o praxisforge usa
o local padrão da configuração do usuário. O repositório não contém mais o registro real, e os
testes e o CI passam mesmo com o registro do curador populado.

**Why this priority**: resolve o problema que motivou a emenda — dados pessoais fora do
repositório público e gates locais verdes.

**Independent Test**: com o diretório de configuração do usuário apontando para uma pasta
temporária, rodar `bootstrap`/`add` e depois `list`/`scan`; o registro é criado e lido no local
padrão, e nenhum arquivo do repositório muda.

**Acceptance Scenarios**:

1. **Given** nenhuma indicação de local e a configuração do usuário definida, **When** o curador roda `folders add`, **Then** o registro é criado em `<config do usuário>/praxisforge/folders.yaml`, criando a pasta `praxisforge` se preciso.
2. **Given** nenhuma configuração do usuário definida, **When** o curador roda `folders add`, **Then** o registro é criado em `~/.config/praxisforge/folders.yaml`.
3. **Given** o registro já existe no local padrão, **When** o curador roda `folders list`, **Then** as pastas do registro são listadas.
4. **Given** o registro não existe no local resolvido, **When** o curador roda `folders list`, `show`, `scan`, `resolve`, `update`, `validate` ou `migrate`, **Then** o comando falha como hoje, informando o local resolvido e sugerindo `folders add` ou `folders bootstrap`.
5. **Given** o repositório clonado do zero, **When** os testes e a validação de dados rodam, **Then** passam sem depender de nenhum registro pessoal.

---

### User Story 2 - Escolher outro local para o registro (Priority: P2)

O curador aponta o registro para outro arquivo, por comando ou por variável de ambiente, para
testar em um registro descartável ou manter o registro em outro disco.

**Why this priority**: permite testes e usos alternativos sem mexer no registro principal;
depende só da regra de resolução da US1.

**Independent Test**: definir a variável e/ou passar a opção de linha de comando com arquivos
diferentes e verificar qual deles é lido e gravado.

**Acceptance Scenarios**:

1. **Given** a variável `PRAXISFORGE_REGISTRY` definida, **When** o curador roda um comando sem `--registry`, **Then** o arquivo da variável é usado.
2. **Given** `PRAXISFORGE_REGISTRY` e `--registry` com arquivos diferentes, **When** o curador roda um comando, **Then** o arquivo de `--registry` é usado.
3. **Given** `PRAXISFORGE_REGISTRY` definida como texto vazio, **When** o curador roda um comando, **Then** a variável é ignorada e vale o local padrão.
4. **Given** um local indicado com `~` ou caminho relativo, **When** o comando roda, **Then** o local é expandido/resolvido antes do uso.

---

### User Story 3 - Realocar o registro existente para o novo local (Priority: P3)

O curador que já tem um registro populado dentro do repositório (`src/data/folders.yaml`) move
esse registro para o novo local com `folders relocate`, sem perder nenhuma pasta e sem apagar um
registro que já exista no destino.

**Why this priority**: operação única por máquina; os usuários novos não precisam dela.

**Independent Test**: com um `src/data/folders.yaml` populado e o local padrão vazio, seguir o
comando de realocação; o destino passa a conter as mesmas pastas e o comando seguinte lê o
novo local. Com o destino já existente, a realocação recusa e nada é sobrescrito.

**Acceptance Scenarios**:

1. **Given** um registro populado em `src/data/folders.yaml` e nenhum registro no local padrão, **When** o curador roda um comando de consulta, **Then** o erro de registro ausente também informa que existe um registro antigo no repositório e sugere `folders relocate`.
2. **Given** o mesmo cenário, **When** o curador roda `folders relocate`, **Then** o registro passa para o local padrão com conteúdo idêntico e o arquivo de origem é removido.
3. **Given** já existe um registro no local de destino, **When** o curador roda `folders relocate`, **Then** a realocação é recusada, nenhum arquivo é alterado e a mensagem cita o destino.
4. **Given** a origem não existe, **When** o curador roda `folders relocate`, **Then** a realocação falha citando a origem e nada é criado.
5. **Given** a origem está no formato v1, **When** o curador roda `folders relocate`, **Then** a realocação é recusada pedindo `folders migrate` antes; nada muda.
6. **Given** a origem é um registro vazio (`folders: {}`), **When** o curador roda `folders relocate`, **Then** a realocação é recusada informando que não há pastas a mover; nada muda.
7. **Given** uma falha de gravação no meio da realocação, **When** ela ocorre, **Then** a origem permanece intacta e nenhum registro parcial fica no destino.
8. **Given** `--registry` ou `PRAXISFORGE_REGISTRY` definidos, **When** o curador roda `folders relocate`, **Then** o destino é o local resolvido por eles (mesma precedência de FR-001).

---

### Edge Cases

- Diretório de configuração do usuário (ou pasta pai do destino da realocação) sem permissão de escrita: `add`/`bootstrap`/`relocate` falham com código de saída 3 (ambiente), citando o local, sem traceback e sem alterar a origem.
- Local resolvido aponta para um diretório (não arquivo): código de saída 2 (uso), citando o local.
- Local resolvido é um link simbólico para arquivo: é seguido normalmente (leitura e gravação no destino do link).
- `PRAXISFORGE_REGISTRY` aponta para arquivo inexistente: comandos de leitura falham como registro ausente (FR-004); `add`/`bootstrap` criam o registro nesse local.
- Registro de exemplo do repositório passado explicitamente com `--registry`: continua funcionando (é só um registro válido sem caminhos pessoais).
- Registro antigo no repositório vazio (`folders: {}`): não gera a dica de realocação e `folders relocate` recusa movê-lo.
- O local resolvido aparece nas mensagens de erro, pois é o próprio item com problema; os caminhos das pastas continuam fora das mensagens em lote.
- Execução a partir de outro diretório de trabalho: o local padrão independe do diretório atual (o registro antigo e as definições de contrato continuam procurados a partir do diretório atual — ver Assumptions).
- Outros clones do repositório: como `src/data/folders.yaml` deixa de ser versionado, atualizar um clone cujo arquivo não foi modificado localmente o remove; a documentação MUST orientar a rodar `folders relocate` antes de atualizar o clone.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O local do registro MUST ser resolvido nesta ordem de precedência: opção `--registry`; variável `PRAXISFORGE_REGISTRY` (quando não vazia); `$XDG_CONFIG_HOME/praxisforge/folders.yaml` (quando `XDG_CONFIG_HOME` estiver definida, não vazia e for um caminho absoluto — valor relativo é ignorado, conforme a especificação XDG); `~/.config/praxisforge/folders.yaml`.
- **FR-002**: O local vindo de `--registry` ou de `PRAXISFORGE_REGISTRY` MUST ter `~` expandido e caminho relativo resolvido a partir do diretório atual antes do uso.
- **FR-003**: `folders add`, `folders bootstrap` e `folders relocate` MUST criar a pasta do registro quando ausente, ao criar o registro.
- **FR-004**: Os demais comandos de pastas (`list`, `show`, `update`, `resolve`, `scan`, `validate` e `migrate`) MUST falhar com o erro de registro ausente (código de saída 1), citando o local resolvido e sugerindo `folders add` ou `folders bootstrap`, sem criar nada.
- **FR-005**: O repositório MUST NOT versionar registro de pastas com caminhos pessoais; `src/data/folders.yaml` MUST ser removido do versionamento e passar a ser ignorado.
- **FR-006**: O repositório MUST versionar `src/data/folders.example.yaml`, um registro válido no contrato vigente, com pastas de exemplo sob caminhos genéricos: nenhum caminho pode conter `/home/`, `/Users/` ou `C:\` (mesmo critério do guarda de caminhos pessoais).
- **FR-007**: A validação de dados do CI MUST validar o registro de exemplo contra o contrato vigente, e o guarda de caminhos pessoais MUST continuar cobrindo todo o conteúdo versionado.
- **FR-008**: Quando o registro não existir no local resolvido e existir um registro antigo com ao menos uma pasta em `src/data/folders.yaml` (a partir do diretório atual), a CLI MUST escrever na saída de erro, além do erro de registro ausente, a linha `registro antigo encontrado em src/data/folders.yaml — execute: praxisforge folders relocate`.
- **FR-009**: `folders relocate [--from ARQUIVO]` (origem padrão `src/data/folders.yaml` a partir do diretório atual) MUST mover o registro para o local resolvido (FR-001) de forma que o conteúdo do destino seja idêntico, byte a byte, ao da origem; ao concluir, a origem MUST ser removida. A realocação MUST recusar sem alterar nada quando já houver registro no destino, quando a origem não existir ou quando a origem não tiver nenhuma pasta.
- **FR-010**: A realocação MUST validar a origem contra o contrato vigente antes de mover; origem no formato v1 MUST ser recusada pedindo `folders migrate`; origem inválida MUST ser recusada com a lista de violações.
- **FR-013**: Se a realocação falhar depois de começar a gravar o destino, a origem MUST permanecer intacta e nenhum arquivo parcial MUST permanecer no destino (código de saída 3).
- **FR-014**: O local resolvido do registro MAY aparecer nas mensagens de erro sobre o próprio registro (é o item com problema, conforme o Princípio V); os caminhos das pastas registradas continuam fora das mensagens em lote.
- **FR-011**: A documentação de operação (guia da CLI, referência do registro e a seção da CLI no README) MUST descrever o local padrão, a precedência, a variável, o exemplo versionado, a realocação e o cuidado com outros clones.
- **FR-012**: Nenhum caminho fixo de máquina MUST aparecer no código-fonte; o local padrão MUST ser derivado do ambiente do usuário.

### Key Entities

- **Local do registro**: arquivo onde o registro de pastas é lido e gravado; derivado da regra de precedência (FR-001).
- **Registro de exemplo**: registro versionado, válido, sem caminhos pessoais, usado para documentação e para o CI.
- **Registro antigo**: `src/data/folders.yaml` de clones anteriores a esta feature; só existe na máquina do curador após a mudança; é a origem padrão de `folders relocate`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com um registro pessoal populado no local padrão, 100% dos testes e da validação de dados passam localmente, e nenhum teste lê ou grava o local real de configuração do usuário.
- **SC-002**: O conteúdo versionado não contém nenhum caminho de diretório de usuário (verificado pelo guarda automático).
- **SC-003**: O curador realoca um registro de 50+ pastas para o novo local com um único comando, em menos de 1 segundo, sem perder nenhuma pasta (conteúdo idêntico).
- **SC-004**: Em 100% dos casos de registro ausente, a mensagem informa o local resolvido e o próximo passo.
- **SC-005**: Um clone novo do repositório roda lint, tipagem, testes, validação de dados e segurança sem nenhuma configuração adicional.

## Assumptions

- Plataforma alvo é Linux (constituição); a convenção de configuração do usuário segue a especificação XDG com o fallback `~/.config`. Outros sistemas operacionais estão fora de escopo.
- A CLI continua procurando as definições de contrato (`schemas/`) e o registro antigo a partir do diretório atual, ou seja, deve ser executada na raiz do projeto; suportar outro diretório de trabalho está fora de escopo desta feature.
- A realocação é um comando da CLI (mover arquivo), não uma conversão de formato: o registro antigo já está no contrato v2; registros v1 passam antes por `folders migrate`.
- A opção `--registry` já existe; muda apenas o seu valor padrão.
- O registro de exemplo contém poucas pastas fictícias sob um caminho genérico (ex.: `/srv/praxisforge/...`) e não é usado como padrão por nenhum comando.
- Fora de escopo: múltiplos registros simultâneos, sincronização entre máquinas, mudança do formato do registro.
