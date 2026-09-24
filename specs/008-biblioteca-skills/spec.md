<!-- Criado em: 24/09/2026 14:52 -->
<!-- Modificado em: 24/09/2026 16:06 -->

# Feature Specification: Biblioteca de skills versionada

**Feature Branch**: `008-biblioteca-skills`

**Created**: 24/09/2026

**Status**: Draft

**Input**: User description: "Biblioteca de skills versionada (feature 008, constituição Princípio VI). O repositório passa a ter skills/<nome>/SKILL.md + arquivos de apoio como fonte de verdade. Entregas: (1) template de skill (skills/_template/) com SKILL.md no formato de skills do Claude (frontmatter com name e description obrigatórios; license e metadata opcionais; metadata.version semver e metadata.sources com os slugs dos registros de fonte em src/data/sources/ que originaram a skill); (2) validação de skills — praxisforge skills validate [nome|--all]: frontmatter válido, name igual ao nome da pasta e no formato minúsculo-com-hífen até 64 caracteres, description não vazia até 1024 caracteres, versão semver, arquivos referenciados no SKILL.md existem, cada fonte citada existe e é válida (source-schema-v2) e skill sem fonte declarada é permitida só se marcada como autoral; falha por item sem derrubar o lote; (3) catálogo gerado — praxisforge skills catalog gera skills/README.md (nome, propósito, versão, caminho, fontes) de forma determinística e idempotente; (4) publicação — praxisforge skills publish [nome|--all] --target global|<pasta-de-projeto> [--mode copy|symlink] publica em ~/.claude/skills/ ou <projeto>/.claude/skills/, só skills válidas, idempotente (segunda execução sem mudanças), nunca sobrescreve uma skill de mesmo nome que não foi publicada pelo praxisforge; scripts/publish-skills como atalho para o comando. Fora de escopo: síntese automática de skills por IA, atualização do catálogo no vault Obsidian (continua manual), definições de agentes (só skills nesta feature)."

## Contexto

O objetivo do praxisforge é transformar conhecimento curado em skills reutilizáveis para o Claude.
Até aqui existem o registro de pastas de origem e os registros de fonte com política de extração
(features 001–007), mas não há onde guardar, validar e distribuir as skills produzidas. A
constituição (Princípio VI) define o repositório como fonte de verdade das skills, exige validação
antes de publicar e publicação por `scripts/publish-skills`.

## Clarifications

### Session 2026-09-24

- Q: Uma skill pode citar como origem uma fonte cuja política de extração é `link`? → A: Pode citar, mas toda skill precisa de ao menos uma fonte `summary` ou `verbatim` (ou ser autoral); skill só com fontes `link` falha na validação.
- Q: A publicação `--all` deve remover do destino skills órfãs publicadas antes pelo praxisforge? → A: Não por padrão; lista as órfãs publicadas pelo praxisforge e `--prune` remove só essas (nunca as de terceiros).
- Q: Conteúdo mudou desde a última publicação, mas a `metadata.version` é a mesma: atualizar ou recusar? → A: Recusar a skill (exit 1) pedindo para incrementar a versão; as demais do lote seguem.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar e validar uma skill no repositório (Priority: P1)

O curador cria uma skill nova a partir do template, preenche o `SKILL.md` e os arquivos de apoio,
declara as fontes curadas que a originaram (ou marca a skill como autoral) e valida. A validação
aponta, por skill, cada problema encontrado.

**Why this priority**: sem estrutura e validação não há biblioteca; é a base das outras histórias
e o critério de qualidade do projeto (≥ 95% das skills aprovadas).

**Independent Test**: copiar o template para `skills/<nome>/`, preencher e rodar a validação;
introduzir erros (nome divergente da pasta, descrição vazia, fonte inexistente, arquivo de apoio
ausente) e conferir que cada um é apontado.

**Acceptance Scenarios**:

1. **Given** uma skill criada a partir do template com todos os campos válidos e fontes existentes, **When** o curador roda `skills validate <nome>`, **Then** a validação passa (exit 0).
2. **Given** uma skill cujo `name` difere do nome da pasta, **When** valida, **Then** falha apontando os dois nomes.
3. **Given** uma skill com `name` fora do formato (maiúsculas, espaços, mais de 64 caracteres) ou `description` vazia/maior que 1024 caracteres, **When** valida, **Then** falha citando o campo e o limite.
4. **Given** uma skill com `metadata.version` fora do formato semver, **When** valida, **Then** falha citando a versão.
5. **Given** um `SKILL.md` que referencia um arquivo de apoio inexistente na pasta da skill, **When** valida, **Then** falha citando o arquivo.
6. **Given** uma skill que cita uma fonte inexistente ou inválida em `src/data/sources/`, **When** valida, **Then** falha citando a fonte e o motivo.
7. **Given** uma skill sem fontes declaradas e sem marca de autoral, **When** valida, **Then** falha pedindo fontes ou a marca; com a marca, passa.
8. **Given** várias skills, algumas inválidas, **When** o curador roda `skills validate --all`, **Then** todas são avaliadas, as falhas são listadas por skill e o resultado final indica falha.
9. **Given** uma skill cujas fontes declaradas têm todas a política `link`, **When** valida, **Then** falha informando que é preciso ao menos uma fonte `summary`/`verbatim` ou a marca de autoral.

---

### User Story 2 - Gerar o catálogo da biblioteca (Priority: P2)

O curador gera o catálogo `skills/README.md` a partir dos `SKILL.md`, com nome, propósito,
versão, caminho e fontes de cada skill.

**Why this priority**: torna a biblioteca navegável e é pré-requisito citado no objetivo
(catálogo gerado a partir dos `SKILL.md`); depende só da leitura/validação da US1.

**Independent Test**: com duas ou mais skills válidas, gerar o catálogo duas vezes e comparar os
arquivos; alterar uma versão e conferir que só a linha correspondente muda.

**Acceptance Scenarios**:

1. **Given** skills válidas no repositório, **When** o curador roda `skills catalog`, **Then** `skills/README.md` lista cada skill em ordem alfabética com nome, propósito, versão, caminho e fontes.
2. **Given** o catálogo já gerado e nenhuma skill alterada, **When** gera de novo, **Then** o arquivo fica idêntico, byte a byte.
3. **Given** uma skill inválida, **When** gera o catálogo, **Then** ela fica fora do catálogo, o comando informa quais foram omitidas e sai com falha.
4. **Given** o template `skills/_template/`, **When** gera o catálogo, **Then** o template não aparece como skill.

---

### User Story 3 - Publicar skills para uso no Claude (Priority: P3)

O curador publica uma ou todas as skills válidas no diretório global de skills do Claude ou no
diretório de skills de outro projeto, por cópia ou por link simbólico.

**Why this priority**: entrega o valor final (skills usáveis), mas depende das US1/US2.

**Independent Test**: publicar em um destino temporário, repetir a publicação e conferir que nada
muda; colocar no destino uma skill de mesmo nome criada à mão e conferir que ela não é tocada.

**Acceptance Scenarios**:

1. **Given** uma skill válida, **When** o curador roda `skills publish <nome> --target global`, **Then** a skill aparece em `~/.claude/skills/<nome>/` com os mesmos arquivos do repositório.
2. **Given** uma pasta de projeto, **When** publica com `--target <pasta>`, **Then** a skill aparece em `<pasta>/.claude/skills/<nome>/`.
3. **Given** `--mode symlink`, **When** publica, **Then** o destino é um link simbólico para a pasta da skill no repositório.
4. **Given** a skill já publicada e sem mudanças, **When** publica de novo, **Then** nada é alterado e a saída informa "inalterada".
5. **Given** a skill publicada por cópia, alterada depois no repositório e com `metadata.version` incrementada, **When** publica de novo, **Then** o destino é atualizado para o conteúdo atual.
5a. **Given** a skill publicada por cópia e alterada depois no repositório **sem** incrementar `metadata.version`, **When** publica de novo, **Then** a skill é recusada (exit 1) pedindo para incrementar a versão, o destino não muda e as demais skills do lote seguem.
6. **Given** no destino uma pasta de mesmo nome que não foi publicada pelo praxisforge, **When** publica, **Then** a skill é recusada, nada é alterado e a mensagem cita o destino.
7. **Given** uma skill inválida, **When** publica, **Then** ela é recusada com os erros de validação; com `--all`, as válidas são publicadas e as inválidas listadas como falha.
8. **Given** o atalho `scripts/publish-skills`, **When** o curador o executa com os mesmos argumentos, **Then** o resultado é o mesmo do comando `skills publish`.
9. **Given** uma skill publicada antes pelo praxisforge que não existe mais no repositório, **When** o curador publica com `--all`, **Then** a saída a lista como órfã e nada é removido; com `--all --prune`, ela é removida do destino, e pastas de terceiros nunca são tocadas.

---

### Edge Cases

- Pasta em `skills/` sem `SKILL.md`: falha de validação da própria pasta ("SKILL.md ausente").
- `SKILL.md` sem frontmatter ou com frontmatter inválido: falha citando o problema, sem derrubar o lote.
- Pastas iniciadas por `_` ou `.` (ex.: `_template`) não são skills: ignoradas por `--all`, catálogo e publicação.
- Referências no `SKILL.md` para URLs externas ou âncoras não contam como arquivos de apoio; referência que sai da pasta da skill (`../`) é falha.
- Diretório `skills/` vazio: validação e catálogo terminam com "0 skills", sem erro; o catálogo informa que não há skills.
- Destino de publicação sem permissão de escrita: falha de ambiente (exit 3) sem publicação parcial.
- Publicação por symlink quando já existe cópia publicada pelo praxisforge (ou vice-versa): o destino é trocado para o novo modo; a troca de modo sempre publica, sem aplicar a regra de versão (não há versão publicada comparável no symlink).
- Nome de skill pedido que não existe no repositório: erro citando o nome (exit 1).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O repositório MUST conter `skills/_template/` com um `SKILL.md` modelo e instruções de preenchimento; pastas iniciadas por `_` ou `.` MUST ser ignoradas como skills.
- **FR-002**: O `SKILL.md` MUST ter frontmatter com `name` e `description` obrigatórios; `license` e `metadata` opcionais. `metadata.version` (semver `MAJOR.MINOR.PATCH`) MUST ser obrigatório nas skills do praxisforge; `metadata.sources` (lista de slugs de registros de fonte) e `metadata.authored` (verdadeiro/falso) opcionais.
- **FR-003**: A validação MUST exigir `name` igual ao nome da pasta, no formato minúsculo com hífens (letras, dígitos e `-`), com até 64 caracteres.
- **FR-004**: A validação MUST exigir `description` não vazia com até 1024 caracteres.
- **FR-005**: A validação MUST exigir que todo arquivo relativo referenciado por link no corpo do `SKILL.md` exista dentro da pasta da skill; URLs externas e âncoras são ignoradas; referências fora da pasta são falha.
- **FR-006**: Cada slug em `metadata.sources` MUST corresponder a um registro de fonte existente em `src/data/sources/<categoria>/<slug>.md` que passe na validação de fontes (contrato v2 e política de extração).
- **FR-007**: Skill sem fontes declaradas MUST ter `metadata.authored: true`; caso contrário a validação falha.
- **FR-007a**: Skill não autoral MUST citar ao menos uma fonte com política `summary` ou `verbatim`; fontes `link` podem ser citadas como referência complementar, mas uma skill cujas fontes são todas `link` MUST falhar na validação.
- **FR-008**: `skills validate <nome>` e `skills validate --all` MUST avaliar todas as skills pedidas, listar cada falha com a skill e o motivo, e sair com falha se houver ao menos uma (sem interromper no primeiro erro).
- **FR-009**: `skills catalog` MUST gerar `skills/README.md` com uma entrada por skill válida (nome, propósito = `description`, versão, caminho, fontes ou "autoral"), em ordem alfabética, com conteúdo determinístico (sem data/hora de geração) e idempotente.
- **FR-010**: O catálogo MUST omitir skills inválidas, listar as omitidas na saída e sair com falha quando houver omissões.
- **FR-011**: `skills publish <nome>|--all --target global|<pasta>` MUST publicar em `~/.claude/skills/<nome>/` (global) ou `<pasta>/.claude/skills/<nome>/`, com `--mode copy` (padrão) ou `--mode symlink`.
- **FR-012**: A publicação MUST validar cada skill antes; skill inválida MUST ser recusada com os erros.
- **FR-013**: A publicação MUST ser idempotente: destino já igual à skill → nada muda e a saída informa "inalterada"; destino publicado pelo praxisforge com conteúdo diferente → atualizado somente se a `metadata.version` da skill for diferente da versão publicada; com a mesma versão, a skill MUST ser recusada pedindo para incrementar a versão, sem alterar o destino. No modo `symlink` o destino reflete o repositório e a regra de versão não se aplica; a troca entre `copy` e `symlink` também não a aplica.
- **FR-014**: A publicação MUST NOT alterar nem remover um destino de mesmo nome que não tenha sido publicado pelo praxisforge; nesse caso a skill é recusada citando o destino. A identificação de "publicado pelo praxisforge" MUST ser verificável no próprio destino (marcador na cópia ou link apontando para a pasta da skill no repositório).
- **FR-015**: Uma falha de gravação durante a publicação MUST deixar o destino como estava antes (sem publicação parcial) e sair com código de ambiente (3).
- **FR-015a**: Com `--all`, a publicação MUST listar como órfãs as skills do destino publicadas pelo praxisforge que não existem mais no repositório, sem removê-las; com `--prune` (só junto de `--all`), MUST removê-las. Destinos não publicados pelo praxisforge MUST NOT ser removidos.
- **FR-016**: `scripts/publish-skills` MUST repassar seus argumentos para `skills publish` e retornar o mesmo código de saída.
- **FR-017**: A documentação MUST descrever a estrutura de uma skill, o template, a validação, o catálogo e a publicação; o catálogo de skills do vault continua manual.

### Key Entities

- **Skill**: pasta `skills/<nome>/` com `SKILL.md` (frontmatter + corpo) e arquivos de apoio; identificada pelo nome.
- **Metadados da skill**: versão semver, fontes curadas de origem (slugs) ou marca de autoral, licença opcional.
- **Catálogo**: `skills/README.md` gerado, uma entrada por skill válida.
- **Destino de publicação**: diretório de skills do Claude (global ou de um projeto); cada skill publicada carrega a identificação de que veio do praxisforge.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das regras de validação (FR-002 a FR-007) têm um caso de falha coberto e apontado com a skill e o motivo.
- **SC-002**: Gerar o catálogo duas vezes seguidas sem mudanças nas skills produz arquivos idênticos.
- **SC-003**: Publicar duas vezes seguidas sem mudanças não altera nenhum arquivo do destino.
- **SC-004**: Nenhuma skill de terceiros (não publicada pelo praxisforge) é alterada pela publicação.
- **SC-005**: Validar, catalogar e publicar uma biblioteca de 50 skills leva menos de 5 segundos cada.
- **SC-006**: O curador cria uma skill nova a partir do template e a publica em menos de 5 minutos seguindo a documentação.

## Assumptions

- O formato do `SKILL.md` segue as skills do Claude (frontmatter YAML com `name` e `description`); os limites de 64 e 1024 caracteres seguem esse formato.
- As skills do praxisforge guardam seus metadados próprios em `metadata` (versão, fontes, autoral), campo opcional aceito pelo formato.
- As fontes são referenciadas por slug (nome do arquivo sem `.md`), único em `src/data/sources/`; slug repetido em categorias diferentes é falha de validação.
- A validação não verifica se o conteúdo da skill respeita a política de extração das fontes (verificação editorial, como na feature 006); exige que as fontes citadas sejam válidas e que ao menos uma permita `summary`/`verbatim` (FR-007a).
- A publicação só remove do destino skills órfãs publicadas pelo praxisforge, e apenas com `--prune` (FR-015a).
- O comando é executado na raiz do projeto (mesma limitação das features anteriores).
- Fora de escopo: síntese automática de skills por IA, atualização do catálogo no vault Obsidian, definições de agentes.
