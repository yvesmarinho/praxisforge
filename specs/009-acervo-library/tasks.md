<!-- Criado em: 25/09/2026 12:29 -->
<!-- Modificado em: 25/09/2026 12:30 -->

# Tasks: Acervo `library/` por tipo de recurso

**Input**: Design documents from `specs/009-acervo-library/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/cli-library.md](contracts/cli-library.md),
[quickstart.md](quickstart.md)

**Tests**: obrigatórios (constituição, Princípio III). Em cada fase, os testes de falha vêm antes da
implementação e precisam falhar antes de seguir (vermelho → verde).

**Organization**: tarefas agrupadas por user story; `[P]` = arquivo diferente e sem dependência de
tarefa incompleta.

## Phase 1: Setup (governança e contratos)

**Purpose**: registrar a mudança de princípio e os contratos antes de qualquer código.

- [X] T001 Emendar a constituição para v4.0.0 (MAJOR) em `.specify/memory/constitution.md`: Princípio VI → acervo `library/` com seis tipos e publicação só em pastas de projeto; Princípio V → só ideias são extraídas, licença obrigatória e só informativa; Sync Impact Report e cabeçalho atualizados (research R9)
- [X] T002 [P] Escrever `docs/decisions/0011-acervo-library.md` (estrutura por tipo, formatos R1–R3, marcador R4, remoção do alvo global) e marcar o ADR 0009 como substituído em `docs/decisions/0009-biblioteca-de-skills.md`
- [X] T003 [P] Escrever `docs/decisions/0012-fontes-so-ideias.md` (fim dos níveis de extração, conversão manual v2 → v3, research R6)
- [X] T004 [P] Criar `schemas/command-frontmatter-v1.json`, `schemas/agent-frontmatter-v1.json`, `schemas/rule-frontmatter-v1.json`, `schemas/hook-frontmatter-v1.json` e `schemas/reference-frontmatter-v1.json` com o bloco `metadata` comum (`version`, `sources`, `authored`, `rewrite_pending`) conforme research R1/R2/R5
- [X] T005 [P] Estender `schemas/skill-frontmatter-v1.json` (aditivo) com `metadata.references` e `metadata.rewrite_pending`
- [X] T006 [P] Criar `schemas/library-publication-v1.json` (`kind`, `name`, `version`, `content_sha256`, `source` = `library/<kind>s/<nome>`) conforme data-model
- [X] T007 [P] Criar `schemas/source-schema-v3.json` sem `extract_policy`, `extract_scope`, `notice_preserved` e `modified` (research R6)
- [X] T008 Testes de contrato em `tests/contract/test_library_schemas.py`: exemplo válido e inválido por schema (T004–T007), incluindo `name` fora do formato, `version` não semver, `event` de hook fora do enum e `run` vazio; atualizar `tests/contract/test_schemas_match_contracts.py` se ele listar os schemas

---

## Phase 2: Foundational (Domain, portas e adapter de leitura)

**Purpose**: o núcleo que todas as histórias usam. Nenhuma user story começa antes.

- [X] T009 [P] Declarar exceções em `src/praxisforge/domain/errors.py`: `InvalidLibraryItemError(kind, name, violations)`, `UnknownItemKindError`, `NotPublishableKindError`, `GlobalTargetRemovedError`, `IndexWriteError`, `LibraryNotFoundError`; reexportar em `src/praxisforge/application/errors.py`
- [X] T010 Testes de falha em `tests/unit/domain/test_library_item.py` (migrando os casos de `tests/unit/domain/test_skill.py`): nome inválido, >64 caracteres, nome ≠ arquivo/pasta, descrição vazia e >1024, versão não semver, fontes repetidas, sem fontes e sem `authored`, referência que escapa da pasta, hook sem `event`, `event` inválido, `run` vazio, arquivo do `run` ausente, `metadata.references` fora de skill, coleta de **todas** as violações de uma vez; confirmar vermelho
- [X] T011 Implementar `ItemKind`, `KindSpec` (tabela do data-model), `ItemName`, `ItemMetadata` e `LibraryItem.from_parts` em `src/praxisforge/domain/library_item.py`, reaproveitando `extract_references` e as regras de `src/praxisforge/domain/skill.py` (que **continua existindo** até T036/T037; remoção em T049)
- [X] T012 Acrescentar, **ao lado** de `SkillDocument`/`SkillRepository`/`CatalogWriter`/`SkillPublisher` (removidos em T049), as portas `ItemDocument`, `LibraryRepository` (`list_items(kind)`, `load(kind, name)`, `content_hash(kind, name)`, `item_path(kind, name)`, `unknown_entries()`), `IndexWriter` e `ItemPublisher` em `src/praxisforge/application/ports.py`
- [X] T013 Testes em `tests/integration/test_filesystem_library_repository.py` (migrando `test_filesystem_skill_repository.py`): layout pasta × arquivo por tipo, entrada fora de diretório de tipo conhecido → `unknown_entries`, arquivo ilegível → falha só do item, `library/` ausente → `LibraryNotFoundError`, hash com caminhos relativos igual antes/depois de mover a pasta
- [X] T014 Implementar `src/praxisforge/infrastructure/filesystem_library_repository.py` (sucede `filesystem_skill_repository.py`, que continua existindo até T049)
- [X] T015 Atualizar `tests/skills_helpers.py` → `tests/library_helpers.py` com `criar_projeto` (cria `library/<tipo>/`, marcador `pyproject.toml`, `schemas/`, `src/data/sources/`) e `escrever_item(kind, nome, ...)`; ajustar os imports dos testes que usam o helper

**Checkpoint**: domínio e leitura do acervo prontos.

---

## Phase 3: User Story 1 - Guardar e validar qualquer tipo de recurso (Priority: P1) 🎯 MVP

**Goal**: validar o acervo inteiro, um tipo ou um item, com falha isolada por item.

**Independent Test**: um item válido de cada tipo → "6 ok"; quebrar um command → "5 ok, 1 com falha" com motivo e código 1 (quickstart §2).

### Tests (vermelho primeiro)

- [X] T016 [P] [US1] Testes em `tests/unit/application/test_validate_library.py` (migrando `test_validate_skills.py`): fonte citada inexistente, fonte duplicada em `src/data/sources/`, fonte inválida, item não autoral sem fonte válida, reference citada inexistente ou inválida, falha de um item não interrompe os demais, filtro por tipo e por nome, entrada de tipo desconhecido conta como falha, `rewrite_pending` reportado sem invalidar
- [X] T017 [P] [US1] Testes em `tests/integration/test_cli_library_validate.py` (migrando `test_cli_skills_validate.py`): códigos 0/1/2/3 do contrato, `<nome>` sem `--type` → 2, tipo desconhecido → 2, `library/` ausente → 3 com dica, saída `<kind>/<nome>: <motivo>` e resumo `N ok, M com falha`

### Implementation

- [X] T018 [US1] Implementar `validate_library` em `src/praxisforge/application/validate_library.py` (sucede `validate_skills.py`; o antigo sai em T049), com índice de fontes carregado uma vez por execução (research R8)
- [X] T019 [US1] Adicionar o grupo `library validate [--type T] [<nome>]` em `src/praxisforge/presentation/cli.py` usando `root / "library"`
- [X] T020 [US1] Criar os templates em `library/_templates/` **exceto o de skill** (que chega por `git mv` em T023): `command.md`, `agent.md`, `hook/HOOK.md` + `hook/run.sh` (versionado com `+x`), `rule.md`, `reference.md`, cada um com instruções de preenchimento e sem links de exemplo fora de blocos de código
- [X] T021 [US1] Teste de contrato em `tests/contract/test_library_templates.py` (migrando `test_skill_template.py`, depois de T023): uma **cópia** de cada template, preenchida só nos campos marcados, passa em `library validate`

**Checkpoint**: US1 funcional e testável sozinha.

---

## Phase 4: User Story 2 - Migrar o acervo atual sem perder nada (Priority: P1)

**Goal**: `skills/` → `library/`, com conteúdo e histórico preservados e compatibilidade com publicações anteriores garantida (FR-015–FR-017b, FR-025).

**Independent Test**: quickstart §1: 2 skills em `library/skills/`, `git log --follow` alcança a 008, nenhuma referência ao local antigo.

- [X] T022 [US2] Teste em `tests/integration/test_library_migration.py`: `skills/` não existe; `library/skills/diretrizes-codificacao/SKILL.md` com conteúdo igual ao de `origin/main`; `guarda-barra-qualidade` só difere por `metadata.rewrite_pending: true` e versão `1.0.1`; `library validate` = 2 ok
- [X] T023 [US2] Executar `git mv skills/diretrizes-codificacao skills/guarda-barra-qualidade library/skills/` e `git mv skills/_template library/_templates/skill`, num commit só de renomeação; depois ajustar as instruções do template para o acervo
- [X] T024 [US2] Em commit separado: acrescentar `rewrite_pending: true` e subir para `1.0.1` a versão em `library/skills/guarda-barra-qualidade/SKILL.md` (FR-025); atualizar o cabeçalho `Modificado em`
- [X] T025 [US2] Remover `skills/README.md` (substituído pelo índice na US3) e apagar a pasta `skills/`
- [X] T026 [US2] Teste de guarda em `tests/contract/test_no_legacy_skills_dir.py`: nenhum arquivo versionado em `src/`, `scripts/`, `docs/guides/`, `README.md` ou `Makefile` referencia `skills/` do repositório (ignorando `.claude/skills` e `library/skills`)
- [X] T027 [US2] Atualizar referências ao local antigo: `README.md`, `docs/architecture/overview.md`, `docs/guides/operar-cli-praxisforge.md`; renomear `docs/guides/criar-publicar-skills.md` → `docs/guides/criar-publicar-acervo.md` e reescrevê-lo para os seis tipos

**Checkpoint**: acervo migrado; US1 valida os itens reais.

---

## Phase 5: User Story 3 - Índice geral do acervo (Priority: P2)

**Goal**: `library/INDEX.md` determinístico no lugar de `skills/README.md` (FR-011–FR-014).

**Independent Test**: quickstart §3: duas gerações seguidas com o mesmo hash; `guarda-barra-qualidade` com `⚠ reescrita pendente`.

- [X] T028 [P] [US3] Testes em `tests/unit/application/test_build_index.py` (migrando `test_build_catalog.py`): ordem por tipo e depois nome, sem data, item inválido omitido com motivo, marca de reescrita pendente, acervo vazio, falha do writer → `IndexWriteError` e o índice anterior intacto
- [X] T029 [P] [US3] Testes em `tests/integration/test_cli_library_index.py` (migrando `test_cli_skills_catalog.py`): idempotência byte a byte, saída `índice: N itens (M omitidos)`, falha de gravação → 3
- [X] T030 [US3] Implementar `build_index` em `src/praxisforge/application/build_index.py` (sucede `build_catalog.py`) e `src/praxisforge/infrastructure/filesystem_index_writer.py` (sucede `filesystem_catalog_writer.py`, com gravação atômica)
- [X] T031 [US3] Adicionar `library index` em `src/praxisforge/presentation/cli.py` e gerar o `library/INDEX.md` real

---

## Phase 6: User Story 4 - Publicar em projetos, nunca no escopo global (Priority: P2)

**Goal**: publicar skills, commands, agents e rules em `<projeto>/.claude/`, com compatibilidade com o marcador antigo (FR-017–FR-021).

**Independent Test**: quickstart §4: publicação em pasta temporária; republicação sem mudança; `--target global` → 2; `skills validate` → 2 com dica.

### Tests (vermelho primeiro)

- [X] T032 [P] [US4] Testes em `tests/unit/application/test_publish_items.py` (migrando `test_publish_skills.py`): estados do data-model (ausente, nosso igual, nosso igual com marcador antigo → só regrava o marcador, nosso com versão nova, mesma versão com conteúdo diferente → recusa, terceiro → intocado, órfão só com `--prune`), tipos não publicáveis → `NotPublishableKindError`, alvo global → `GlobalTargetRemovedError`, item com `rewrite_pending` publicável (FR-024a), falha de I/O no meio do lote → itens anteriores ficam publicados e a falha é reportada por item
- [X] T033 [P] [US4] Testes em `tests/integration/test_filesystem_item_publisher.py` (migrando `test_filesystem_skill_publisher.py`): destinos por tipo, marcador `.praxisforge-skill.json` (skill) e `.<nome>.md.praxisforge.json` (command/agent/rule), leitura do marcador `skill-publication-v1`, symlink antigo para `skills/` quebrado → recriado para `library/`, references citadas copiadas para `<skill>/references/`, modo symlink para arquivo único
- [X] T034 [P] [US4] Testes em `tests/integration/test_cli_library_publish.py` (migrando `test_cli_skills_publish.py`): contrato do `publish` (0/1/2/3), `--prune` sem `--all` → 2, hook/reference → 2, `--target global` → 2, e `skills validate|catalog|publish` → 2 com a mensagem do comando `library` equivalente
- [X] T035 [P] [US4] Teste do atalho em `tests/integration/test_publish_library_script.py` (migrando `test_publish_skills_script.py`), rodando de fora da raiz

### Implementation

- [X] T036 [US4] Implementar `publish_items` em `src/praxisforge/application/publish_items.py` (sucede `publish_skills.py`)
- [X] T037 [US4] Implementar `src/praxisforge/infrastructure/filesystem_item_publisher.py` (sucede `filesystem_skill_publisher.py`), com gravação do `library-publication-v1` e leitura do `skill-publication-v1`
- [X] T038 [US4] Adicionar `library publish` e substituir o grupo `skills` por uma mensagem de erro de uso em `src/praxisforge/presentation/cli.py`; remover o alvo `global` e `_destino_de_publicacao`
- [X] T039 [US4] Renomear `scripts/publish-skills` → `scripts/publish-library` (chama `praxisforge library publish`), com cabeçalho atualizado

---

## Phase 7: User Story 5 - Registro de fonte só com ideias (Priority: P3)

**Goal**: `source-schema-v3`, com recusa de v1/v2 e conversão manual dos 2 registros (FR-022–FR-023).

**Independent Test**: quickstart §5: `sources validate` = 2 ok; um registro v2 é recusado com instrução de conversão.

- [X] T040 [P] [US5] Testes em `tests/unit/domain/test_source_record.py` e `tests/contract/test_source_schema_v3.py`: v3 válido; v1 e v2 → `SourceSchemaMigrationRequiredError` com instrução (remover `extract_policy`/`extract_scope`/`notice_preserved`/`modified`, declarar `schema_version: "3"`); `license` ausente → falha
- [X] T041 [P] [US5] Ajustar `tests/unit/application/test_validate_sources.py` e `tests/integration/test_validate_sources_scale.py` para v3; remover as regras de política por licença dos testes de fonte
- [X] T042 [US5] Atualizar `src/praxisforge/domain/source_record.py` e `src/praxisforge/application/validate_sources.py` para v3 e remover da validação de fontes a política por licença (a regra "≥ 1 fonte válida" já está em T018)
- [X] T043 [US5] Converter à mão `src/data/sources/praticas-agentes/karpathy-guidelines.md` e `src/data/sources/praticas-agentes/agent-skills-constraints.md` para v3, conferindo antes e depois que origem, autor, data, licença, relevância e status não mudaram
- [X] T044 [US5] Atualizar `docs/reference/sources-frontmatter.md` para v3

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T045 [P] Teste de escala em `tests/integration/test_library_scale.py` (sucede `test_skills_scale.py`): 200 itens mistos, validate/index < 5 s (SC-004)
- [X] T046 [P] Rodar `tests/architecture/` e ajustar, sem afrouxar a matriz de camadas, se algum módulo novo acusar violação
- [ ] T047 [P] Atualizar `docs/architecture/overview.md` (fluxos `library validate/index/publish`), `docs/INDEX.md` (linha da 009) e `README.md` (seção da CLI, acrescentando sem apagar)
- [ ] T048 Registrar em `docs/TODO.md`: revisar a "política máxima" exibida por `folders show/list` (research R6); rever o uso de `domain/license_policy.py`
- [X] T049 Remover o código da 008 substituído (`domain/skill.py`, portas `Skill*`/`CatalogWriter`, `validate_skills.py`, `build_catalog.py`, `publish_skills.py`, `filesystem_skill_*`, `filesystem_catalog_writer.py`) e seus testes antigos, depois imports órfãos e `_SKILLS_DIR`; rodar `graphify update .`
- [ ] T050 Rodar o [quickstart.md](quickstart.md) inteiro e `make lint && make test`; registrar desvios em `docs/bugs/` se houver

---

## Dependencies & Execution Order

- **Setup (T001–T008)**: sem dependências; T002–T007 em paralelo; T008 depois de T004–T007.
- **Foundational (T009–T015)**: depois do Setup; bloqueia todas as histórias.
- **US1 (T016–T021)**: depois do Foundational.
- **US2 (T022–T027)**: depois da US1, porque a validação comprova a migração. T021 roda depois de T023 (precisa do template de skill).
- **US3 (T028–T031)** e **US4 (T032–T039)**: depois da US2; independentes entre si.
- **US5 (T040–T044)**: depois do Foundational; pode correr em paralelo com US3/US4, mas T042 muda a regra que `validate_library` (T018) usa. Rodar a suíte da US1 de novo ao terminar.
- **Polish (T045–T050)**: depois de todas as histórias.

## Parallel Example

```text
# Setup
T002, T003, T004, T005, T006, T007
# US4, testes vermelhos
T032, T033, T034, T035
# Depois da US2
Fase 5 (US3) ‖ Fase 6 (US4) ‖ Fase 7 (US5)
```

## Implementation Strategy

- **MVP**: Setup + Foundational + US1 + US2 (acervo migrado e validável com os seis tipos).
- Depois: US3 (índice), US4 (publicação), US5 (fontes v3), um PR revisável por fase, ou a feature
  inteira num PR com commits por fase.
- Em cada fase: testes vermelhos confirmados → implementação → `make lint && make test` antes do commit.
