<!-- Criado em: 23/09/2026 15:31 -->
<!-- Modificado em: 23/09/2026 15:39 -->

# Tasks: Caminho absoluto no registro de pastas

**Input**: Design documents from `/specs/005-caminho-absoluto-registro/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-path.md, quickstart.md

**Tests**: OBRIGATÓRIOS (constituição III). Em cada grupo: testes de falha → confirmar vermelho →
implementar → verde.

**Organization**: US1 (P1) registro com caminho, US2 (P1) bootstrap sem colisão, US3 (P2) migração.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [ ] T001 Confirmar baseline verde na branch `005-caminho-absoluto-registro` (`make lint`, `make test`, `make validate-data`) ; não incluir `src/data/folders.yaml` (alterações locais do usuário) em nenhum commit sem confirmação explícita

---

## Phase 2: Foundational (bloqueia todas as stories)

### Testes (vermelho primeiro)

- [ ] T002 [P] Testes de contrato em tests/contract/test_folders_schema_v2.py: `schemas/folders-schema-v2.json` é Draft 2020-12 válido; exige `schema_version: "2"` e `path` em toda pasta; `path` relativo, vazio ou ausente é rejeitado; mantém todas as regras da v1 (licença unknown, not_scanned, last_curated_commit); documento v1 é rejeitado pela v2 (FR-001, FR-009)
- [ ] T003 [P] Testes em tests/unit/domain/test_errors.py: `InvalidFolderPathError` ⊂ `InvalidFolderError`; `PathAlreadyRegisteredError` e `NestedFolderPathError` ⊂ `PraxisForgeError` com atributo `owner`; `RegistryMigrationRequiredError` ⊂ `RegistryUnavailableError` com mensagem citando `folders migrate`
- [ ] T004 [P] Testes em tests/unit/domain/test_folder.py: `Folder.path` obrigatório; rejeita vazio, relativo, com "..", com "~", com barra final → `InvalidFolderPathError`; aceita espaços e acentos; ajustar o helper `_make` com um `path` padrão (FR-001, FR-002)
- [ ] T005 [P] Testes em tests/unit/domain/test_folder_registry.py: `add` com path duplicado (inclusive só diferindo em maiúsculas) → `PathAlreadyRegisteredError(owner)`; path ancestral ou descendente de outro → `NestedFolderPathError(owner)`; "/x/forks" e "/x/forks2" **não** são aninhados; `update(path=...)` atômico, revalida unicidade ignorando a própria pasta, preserva demais campos; `find_by_path` case-insensitive; ajustar helper `_folder` (FR-003, FR-016, SC-004)
- [ ] T006 [P] Testes em tests/integration/test_yaml_folder_registry.py: round-trip v2 com `path`; `save` grava `schema_version: "2"`; `load` de arquivo v1 → `RegistryMigrationRequiredError`; `load_raw` lê v1 e v2; YAML v2 editado à mão com dois paths iguais ou aninhados → erro ao carregar; ajustar helpers existentes para v2 (FR-003, FR-009)
- [ ] T007 [P] Testes de integração em tests/integration/test_filesystem_folder_locator.py com pastas reais em `tmp_path`: `canonicalize` expande "~" (HOME via monkeypatch), resolve relativo a partir do cwd, elimina ".." e resolve link simbólico; inexistente / arquivo / sem permissão de listar-entrar → `FolderPathInvalidError`/`FolderPathUnreadableError` com alias; `check(alias, path)` retorna o caminho quando acessível e falha para pasta movida; mensagens de `check` só citam o caminho do próprio item (FR-002, FR-004, FR-012)
- [ ] T008 [P] Testes em tests/integration/test_env_legacy_path_source.py (substitui tests/integration/test_env_path_resolver.py): `lookup(alias)` lê `PRAXISFORGE_FOLDER_<ALIAS>`, retorna `None` se ausente/vazia
- [ ] T009 Rodar T002–T008 e **confirmar vermelho**

### Implementação

- [ ] T010 Criar schemas/folders-schema-v2.json (cópia da v1 + `path` obrigatório `^/`, `schema_version: const "2"`) e o espelho em specs/001-registro-pastas-curadoria/contracts/ se `tests/contract/test_schemas_match_contracts.py` exigir; ajustar esse teste para a v2
- [ ] T011 Adicionar as 4 exceções em src/praxisforge/domain/errors.py e reexportar em src/praxisforge/application/errors.py
- [ ] T012 Adicionar `path: str` (obrigatório, validação de forma) em src/praxisforge/domain/folder.py
- [ ] T013 Invariantes de unicidade/aninhamento (casefold, por componentes), `update(path=)` e `find_by_path` em src/praxisforge/domain/folder_registry.py
- [ ] T014 Adapter v2 em src/praxisforge/infrastructure/yaml_folder_registry.py: validar contra `folders-schema-v2`, `RegistryMigrationRequiredError` para v1, serializar `path`, `schema_version: "2"`
- [ ] T015 Porta `FolderLocator` (`canonicalize(alias, raw) -> Path`, `check(alias, path) -> Path`) e `LegacyPathSource` (`lookup(alias) -> str | None`) em src/praxisforge/application/ports.py; remover `PathResolver`
- [ ] T016 [P] Adapter src/praxisforge/infrastructure/filesystem_folder_locator.py (reaproveita a lógica de validação de src/praxisforge/infrastructure/env_path_resolver.py)
- [ ] T017 [P] Adapter src/praxisforge/infrastructure/env_legacy_path_source.py; remover src/praxisforge/infrastructure/env_path_resolver.py e tests/integration/test_env_path_resolver.py
- [ ] T018 Rodar T002–T008 → verde; `tests/architecture/` sem violações

**Checkpoint**: domínio, contrato v2 e adapters prontos (casos de uso e CLI ainda quebrados — próximas fases).

---

## Phase 3: User Story 1 — Registro com caminho (P1) 🎯 MVP

**Goal**: add/update/show/list/resolve/scan/update curated funcionam só com o caminho do registro.

**Independent Test**: quickstart §1, §2, §4.

### Testes

- [ ] T019 [P] [US1] Testes em tests/unit/application/test_register_folder.py: `RegisterFolderInput.path` obrigatório; canoniza via fake `FolderLocator`; duplicado/aninhado → exceção citando owner, nada salvo; locator falha → nada salvo (FR-003, FR-004)
- [ ] T020 [P] [US1] Testes em tests/unit/application/test_update_folder.py: `UpdateFolderInput.path` canoniza e atualiza preservando status/licença/versão curada; duplicado → nada salvo; `--status curated` usa `locator.check(alias, folder.path)` (substituir fakes de `PathResolver` por `FolderLocator`) (FR-008, FR-016)
- [ ] T021 [P] [US1] Adaptar tests/unit/application/test_resolve_folder_path.py e tests/unit/application/test_scan_folders.py para `FolderLocator` (fake com `check`), incluindo pasta movida → falha por item/exceção com alias (FR-008)
- [ ] T022 [P] [US1] Testes CLI em tests/integration/test_cli_folders.py, tests/integration/test_cli_resolve.py e tests/integration/test_cli_scan.py: `add --path` obrigatório (sem ele → exit 2); duplicado → exit 1 citando alias; inexistente → exit 3; `show` exibe `caminho:`; `list` exibe coluna de caminho; `resolve`/`scan`/`update --status curated` funcionam **sem** `PRAXISFORGE_FOLDER_*` (remover usos de `env_folder`); `scan --all` sem caminho absoluto na saída; registro v1 → exit 1 pedindo migração (FR-004, FR-008, FR-012, FR-013, SC-002, SC-006)
- [ ] T023 [US1] Rodar T019–T022 e confirmar vermelho

### Implementação

- [ ] T024 [US1] `path` em `RegisterFolderInput`/`UpdateFolderInput` (src/praxisforge/application/dto.py); `register_folder` e `update_folder` recebem `locator` e canonizam (src/praxisforge/application/register_folder.py, src/praxisforge/application/update_folder.py)
- [ ] T025 [US1] `resolve_folder_path` e `scan_folders` usam `locator.check(alias, Path(folder.path))` (src/praxisforge/application/resolve_folder_path.py, src/praxisforge/application/scan_folders.py)
- [ ] T026 [US1] CLI (src/praxisforge/presentation/cli.py): `--path` em add (obrigatório) e update; coluna/linha de caminho em list/show; injetar `FilesystemFolderLocator`; `RegistryMigrationRequiredError` → exit 1; `NestedFolderPathError`/`PathAlreadyRegisteredError` → exit 1
- [ ] T027 [US1] Adaptar tests/integration/test_scan_content_scale.py (paths no registro, sem variáveis) e rodar T019–T022 → verde

---

## Phase 4: User Story 2 — Bootstrap sem colisão (P1)

**Goal**: aliases `<raiz>__<sub>`, idempotência por caminho.

**Independent Test**: quickstart §3.

- [ ] T028 [P] [US2] Testes em tests/unit/application/test_bootstrap_folders.py: alias `github_forks__graphify`; duas raízes de nomes diferentes com mesma subpasta → ambas registradas; raízes de mesmo nome → `forks__graphify` e `forks__graphify_2`; duas subpastas que normalizam igual → sufixo; nome vazio/iniciado por dígito → prefixo `p`; alias > 63 com sufixo `_10` truncado corretamente; ordem alfabética determinística; reexecução → `skipped_existing` por caminho (mesmo com alias diferente, após `update --path`); `ignore` → `skipped_ignored`; raiz não é registrada; subpasta dentro de pasta já registrada → falha por item (aninhamento); `path` gravado canônico (FR-005–FR-007, FR-017, SC-001, SC-005)
- [ ] T029 [P] [US2] Testes em tests/integration/test_cli_bootstrap.py com duas raízes reais em `tmp_path`: saída só com aliases; repetir não altera bytes do YAML; bootstrap de 100 subpastas em < 5 s (Plan §Performance)
- [ ] T030 [US2] Rodar T028–T029 e confirmar vermelho
- [ ] T031 [US2] Implementar geração de alias (normalização, prefixo `p`, sufixo, truncamento) e idempotência por caminho em src/praxisforge/application/bootstrap_folders.py (recebe `locator` para canonizar); ajustar CLI em src/praxisforge/presentation/cli.py; rodar → verde

---

## Phase 5: User Story 3 — Migração (P2)

**Goal**: `folders migrate [--root DIR]` converte v1 → v2 atômica e idempotente.

**Independent Test**: quickstart §5, §6.

- [ ] T032 [P] [US3] Testes em tests/unit/application/test_migrate_registry.py com fakes: caminho por `LegacyPathSource` primeiro, depois subpasta da raiz com slug igual ao alias; 0 ou >1 candidatos → pendência; pendência → nada gravado (`written=False`); tudo resolvido → v2 gravado uma vez preservando todos os campos e aliases; entrada ancestral de outras → `removed_roots`; duplicados/aninhados após resolver → pendência; registro v2 → `already_current`, nada gravado; registro inexistente → erro (FR-010, FR-011, FR-014, FR-015, FR-017, SC-003)
- [ ] T033 [P] [US3] Testes em tests/integration/test_cli_migrate.py: v1 real com 3 pastas (variável, raiz, sem caminho) → exit 1 listando pendente e YAML intacto; resolvido → exit 0, YAML v2 válido; repetir → "registro já no formato atual"; saída só com aliases; teste de 100 pastas em < 5 s
- [ ] T034 [US3] Rodar T032–T033 e confirmar vermelho
- [ ] T035 [US3] Criar src/praxisforge/application/migrate_registry.py (`MigrationReport`) e subcomando `folders migrate [--root]` em src/praxisforge/presentation/cli.py (injeta `EnvLegacyPathSource`, `FilesystemFolderLocator`); rodar → verde

---

## Phase 6: Polish & Cross-Cutting

- [ ] T036 Migrar o registro **versionado** `src/data/folders.yaml` para v2: pedir ao usuário como tratar as alterações locais não commitadas (55 pastas) antes de rodar `folders migrate --root ~/DevOps/github_forks`; só commitar o YAML com confirmação explícita; `make validate-data` verde
- [ ] T037 [P] ADR docs/decisions/0006-caminho-absoluto-no-registro.md (constituição v2.0.0, schema v2, FolderLocator, alias `<raiz>__<sub>`, migração, alternativas rejeitadas)
- [ ] T038 [P] Atualizar docs/reference/folders-yaml.md (v2, `path`, unicidade/aninhamento, sem variáveis), docs/guides/operar-cli-praxisforge.md (add/update --path, migrate, remoção das variáveis), docs/architecture/overview.md (portas/adapters novos)
- [ ] T039 [P] Acrescentar entradas em docs/INDEX.md e docs/TODO.md (append)
- [ ] T040 Executar quickstart §1–§6 manualmente
- [ ] T041 Gates finais: `make lint`, `make test` (≥ 90%), `make validate-data`, `make security`, `tests/architecture/`; `graphify update .`

---

## Dependencies & Execution Order

- T001 → Foundational (T002–T018) → US1 (T019–T027) → US2 (T028–T031) e US3 (T032–T035) → Polish (T036–T041).
- A Foundational quebra casos de uso e CLI de propósito (porta removida); a suíte completa só volta a ficar verde ao fim da US1 — commits intermediários devem ser feitos só em pontos verdes (fim da US1).
- US2 e US3 tocam arquivos distintos na Application, mas ambas editam cli.py → T031 e T035 em sequência.
- T036 depende de T035 (migrate) e de decisão do usuário.

## Parallel Example

```text
Foundational (testes): T002 ∥ T003 ∥ T004 ∥ T005 ∥ T006 ∥ T007 ∥ T008
US1 (testes): T019 ∥ T020 ∥ T021 ∥ T022
US2 ∥ US3 (testes): T028 ∥ T029 ∥ T032 ∥ T033
Polish: T037 ∥ T038 ∥ T039
```

## Implementation Strategy

1. **MVP** = Foundational + US1: registro com caminho, sem variáveis de ambiente.
2. **+ US2**: bootstrap sem colisão.
3. **+ US3**: migração — necessária antes de usar o registro local existente.
4. Polish com migração do registro versionado mediante confirmação do usuário.
