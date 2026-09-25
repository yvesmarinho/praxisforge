---
description: "Tarefas da feature 010 — inventário de curadoria por pasta"
---
<!-- Criado em: 25/09/2026 14:42 -->
<!-- Modificado em: 25/09/2026 14:59 -->

# Tasks: Inventário de curadoria por pasta

**Input**: `specs/010-inventario-curadoria/` (plan, spec, research, data-model, contracts, quickstart)

**Tests**: obrigatórios (constituição III — test-first). Em cada história: testes de falha
primeiro, confirmados **vermelhos**, depois a implementação.

**Formato**: `- [ ] Tnnn [P?] [USn?] descrição com caminho`. Todo `.py` novo leva o cabeçalho
padrão (NOME, TITULO, DATA, MODIFICADO, VERSÃO, DEPEND, HISTÓRICO, STATUS).

## Phase 1: Setup

- [X] T001 Declarar `pathspec` em `pyproject.toml` (`uv add pathspec`) e atualizar `uv.lock`
- [X] T002 [P] Copiar os schemas de `specs/010-inventario-curadoria/contracts/` para `schemas/curation-conventions-schema-v1.json`, `schemas/curation-manifest-schema-v1.json` e `schemas/curation-state-schema-v1.json` (o teste `tests/contract/test_schemas_match_contracts.py` exige a igualdade)
- [X] T003 [P] Criar `src/data/curation-conventions.example.yaml` com as regras da tabela de `contracts/cli-curation.md` (`schema_version: "1"`, sem caminhos pessoais)
- [X] T004 Incluir `"1"` dos novos schemas em `_SUPPORTED_SCHEMA_VERSIONS` de `src/praxisforge/infrastructure/jsonschema_validator.py`, se a validação for por versão — sem mudança: o validador já aceita "1"

## Phase 2: Foundational (bloqueia todas as histórias)

- [X] T005 [P] Testes de contrato (vermelho) em `tests/contract/test_curation_schemas.py`: exemplo de convenções válido; manifesto e estado rejeitam `schema_version` desconhecida, path absoluto, path com `..`, sha inválido, kind/stage/reason fora do enum, campo extra
- [X] T006 [P] Testes unitários (vermelho) em `tests/unit/domain/test_curation_artifact.py`: `ArtifactKind`/`Stage`/`ExclusionReason.from_str` rejeitam valor desconhecido; `Artifact` rejeita path absoluto, vazio, com `..`, size negativo, files < 1, sha ≠ 64 hex; `Stage.is_final` (inclui `reviewed`+`accepted` e exclui `reviewed` sem veredito)
- [X] T007 Criar exceções semânticas `ConventionsError`, `ConventionsMissingError`, `CurationStateCorruptError`, `CurationLockedError` em `src/praxisforge/domain/errors.py` (reusar as de alias/pasta inexistente já existentes)
- [X] T008 Implementar `src/praxisforge/domain/curation_artifact.py` (enums, `Artifact`, `ExcludedEntry`, `Manifest` com listas ordenadas por path) até T006 passar
- [X] T009 Adicionar portas `FolderWalker`, `ConventionsSource` e `CurationStore` (load_state, save, lock como context manager) em `src/praxisforge/application/ports.py`, e reexportar tipos do domínio usados pela CLI via application (guarda AST)

**Checkpoint**: contratos e entidades verdes.

## Phase 3: User Story 1 — Inventariar uma pasta sem esquecer nada (P1) 🎯 MVP

**Goal**: manifesto completo e determinístico de uma pasta, gravado fora do repo.

**Independent Test**: fixture espelhando o `agent-skills` → todos os tipos classificados; `node_modules`, `graphify-out`, binário e arquivo > 256 KiB excluídos com motivo; duas execuções → manifest.json idêntico byte a byte.

### Testes (vermelho primeiro)

- [X] T010 [P] [US1] `tests/unit/domain/test_curation_conventions.py`: regra com kind `unknown` ou pattern vazio → `ConventionsError`; prioridade pela ordem; `unit: directory` devolve o diretório da skill; `.claude/skills/x/SKILL.md` e `skills/x/SKILL.md` casam; `CLAUDE.md` aninhado casa; versão muda quando uma regra muda e não muda com reformatação
- [X] T011 [P] [US1] `tests/integration/test_yaml_conventions_loader.py`: arquivo ausente → `ConventionsMissingError` com a instrução de cópia; YAML inválido e schema inválido → `ConventionsError`; ilegível (permissão) → `ConventionsError`; carrega o exemplo `src/data/curation-conventions.example.yaml`
- [X] T012 [P] [US1] `tests/integration/test_filesystem_folder_walker.py`: lista fixa de diretórios; `.gitignore` na raiz e aninhado, com negação `!`; arquivo de exatamente 262.144 bytes entra e 262.145 sai (`too_large`); binário (NUL) sai; symlink para fora (`symlink_outside`) e para diretório (`symlink_dir`); symlink em ciclo não trava; arquivo sem permissão → `unreadable` e o resto continua; pasta inexistente → erro de pasta indisponível; nenhuma escrita (mtime da pasta inalterado)
- [X] T013 [P] [US1] `tests/integration/test_json_curation_store.py`: gravação atômica (falha simulada no replace mantém o arquivo anterior); estado com JSON inválido ou `schema_version` "9" → `CurationStateCorruptError` sem sobrescrever; segundo lock no mesmo alias → `CurationLockedError`; diretório do registro sem permissão de escrita → erro de ambiente; manifesto serializado com chaves e listas ordenadas
- [X] T014 [US1] `tests/integration/test_inventory_folders.py` (US1): fixture `agent-skills` completa (skills com apoio, commands, agents, `hooks/`, rules, references, `CLAUDE.md`, `AGENTS.md`, README, `docs/x.md`, `app.py`); README e `docs/x.md` viram `unknown`; `app.py` → excluído `uncurated`; arquivos de apoio da skill não viram artefatos; SC-002 (todo arquivo coberto por exatamente um artefato ou exclusão); determinismo; pasta vazia → manifesto com zero artefatos; pasta com status `pending` é inventariada

### Implementação

- [X] T015 [US1] `src/praxisforge/domain/curation_conventions.py`: `ConventionRule`, `Conventions` (versão SHA-256 canônica), `classify(rel_path)`; o domínio não depende de `pathspec`, então `classify` recebe um `matcher: Callable[[str, str], bool]` injetado; até T010 passar
- [X] T016 [US1] `src/praxisforge/infrastructure/yaml_conventions_loader.py`: resolve `<dir do registro>/curation-conventions.yaml`, valida pelo schema, monta `Conventions` e o matcher `pathspec`; até T011 passar
- [X] T017 [US1] `src/praxisforge/infrastructure/filesystem_folder_walker.py`: `os.walk(followlinks=False)` ordenado, exclusões (R5), `.gitignore` via `GitIgnoreSpec`, SHA-256 em blocos de 64 KiB, devolve arquivos candidatos + exclusões; até T012 passar
- [X] T018 [US1] `src/praxisforge/infrastructure/json_curation_store.py`: `<dir do registro>/curation/<alias>/`, `fcntl.flock` em `.lock`, leitura validada, gravação temp + `os.replace`, JSON com `sort_keys` e `indent=2`; até T013 passar
- [X] T019 [US1] `src/praxisforge/application/inventory_folders.py`: `inventory_folder(alias, …)` — lock → walker → classificação (skill/hook como diretório com hash agregado R4; `.md` avulso → `unknown`; outro texto → `uncurated`) → `Manifest` → grava manifesto e estado inicial (tudo `pending`) → logs estruturados de início/fim; até T014 passar
- [X] T020 [US1] Grupo `curation inventory <alias>` em `src/praxisforge/presentation/cli.py` (mensagens sem caminho absoluto; exit 0/1/2/3 conforme `contracts/cli-curation.md`)
- [X] T021 [US1] `tests/integration/test_cli_curation.py` (US1): sucesso, alias inexistente (2), sem alvo (2), convenções ausentes (3 com instrução), lock ocupado (3), estado corrompido (1)

**Checkpoint**: MVP — `curation inventory <alias>` funciona sozinho.

## Phase 4: User Story 2 — Saber se a curadoria está completa (P1)

**Goal**: situação por pasta (completa / incompleta / sem inventário) e contagem por etapa.

**Independent Test**: inventariar → "incompleta, N pendentes"; editar o estado marcando tudo `promoted` → "completa"; pasta `curated` sem estado → "sem inventário".

- [X] T022 [P] [US2] `tests/unit/domain/test_curation_state.py` (situação): sem estado → `not_inventoried`; zero artefatos → `complete`; um `failed` → `incomplete`; `reviewed` sem veredito → `incomplete`; `reviewed`+`accepted` → final
- [X] T023 [P] [US2] `tests/integration/test_query_curation.py`: contagem por etapa; falhas com `last_error`; estado corrompido de uma pasta não impede as outras (marcado inválido); pastas `ignore` fora
- [X] T024 [US2] `ArtifactState`, `CurationState` e `situation()` em `src/praxisforge/domain/curation_state.py`; até T022 passar
- [X] T025 [US2] `src/praxisforge/application/query_curation.py` (`CurationReport` por pasta); até T023 passar
- [X] T026 [US2] `curation status [<alias>] [--json]` em `src/praxisforge/presentation/cli.py` e casos em `tests/integration/test_cli_curation.py` (tabela, `--json`, alias inexistente 2, estado inválido 1)

## Phase 5: User Story 3 — Refazer só o que mudou (P2)

**Goal**: reinventário incremental por hash.

**Independent Test**: inventariar, marcar tudo `promoted`, alterar 1 arquivo e remover outro, reinventariar → só 1 `pending`, 1 `removed`, resto `promoted` (SC-004).

- [X] T027 [P] [US3] `tests/unit/domain/test_curation_state.py` (reconcile): todas as linhas da tabela de reconciliação do data-model — novo, inalterado, hash alterado, kind alterado após mudar convenções (FR-016), sumido → `removed`, `removed` que reaparece → `pending`, attempts preservado
- [X] T028 [US3] `reconcile(previous, manifest)` em `src/praxisforge/domain/curation_state.py`; até T027 passar
- [X] T029 [US3] Usar `reconcile` em `src/praxisforge/application/inventory_folders.py` e cenário ponta a ponta em `tests/integration/test_inventory_folders.py` (alteração em arquivo de apoio da skill muda só a skill; pasta inacessível mantém o estado anterior intacto)

## Phase 6: User Story 4 — Inventariar todas as pastas (P3)

**Goal**: lote tolerante a falhas.

**Independent Test**: três pastas, uma inacessível → duas ok, uma falha com motivo, exit 1.

- [X] T030 [P] [US4] Casos de lote em `tests/integration/test_inventory_folders.py`: falha de uma não impede as outras; `ignore` pulada; resumo com contagens; lock ocupado numa pasta vira falha dela
- [X] T031 [US4] `inventory_all(...)` em `src/praxisforge/application/inventory_folders.py` com `InventoryReport`; até T030 passar
- [X] T032 [US4] `curation inventory --all` (e erro de uso com alias + `--all`) em `src/praxisforge/presentation/cli.py` e casos em `tests/integration/test_cli_curation.py`

## Phase 7: Polish

- [X] T033 [P] Teste de desempenho `slow` com 5.000 arquivos (< 10 s, SC-005) em `tests/integration/test_inventory_performance.py`
- [X] T034 [P] Teste SC-006 em `tests/integration/test_inventory_folders.py`: nada escrito na pasta nem no repositório (snapshot de mtimes)
- [X] T035 [P] Garantir que `tests/contract/test_no_absolute_paths.py` cobre `src/data/curation-conventions.example.yaml` e que `tests/architecture/` passa com os módulos novos
- [X] T036 [P] ADR `docs/decisions/0013-inventario-de-curadoria.md` (R1–R3, R6: local fora do repo, convenções em `~/.config`, pathspec, flock) e índice em `docs/decisions/README.md`
- [X] T037 [P] Guia `docs/guides/inventariar-curadoria.md` (copiar convenções, inventory, status, reinventário)
- [X] T038 Atualizar `docs/architecture/overview.md`, `README.md`, `docs/INDEX.md` e `docs/TODO.md` (somente acréscimos)
- [X] T039 Rodar gates: `uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest --cov-fail-under=90`; validar o [quickstart.md](quickstart.md) num registro isolado
- [X] T040 `graphify update .` e registro da sessão no vault `claude_memory`

## Dependencies & Execution Order

- Setup (T001–T004) → Foundational (T005–T009) → US1 (T010–T021).
- US2 depende de US1 (precisa de estado gravado); US3 depende de US2 (usa `CurationState`); US4 depende de US1.
- US4 pode correr em paralelo com US2/US3 após o checkpoint do MVP.
- Polish depois de todas.

## Parallel Examples

- Foundational: T005 ∥ T006.
- US1: T010 ∥ T011 ∥ T012 ∥ T013 (arquivos distintos); depois T015–T018 em paralelo por arquivo, T019 → T020 → T021 em sequência.
- US2: T022 ∥ T023.
- Polish: T033 ∥ T034 ∥ T035 ∥ T036 ∥ T037.

## Implementation Strategy

1. MVP = Phases 1–3: `curation inventory <alias>` gera manifesto completo — já corrige o buraco
   que motivou o debate.
2. US2 (status) → US3 (incremental) → US4 (lote), cada uma com suíte verde e commit próprio.
3. Um PR para a feature, aguardando todos os checks antes do merge.
