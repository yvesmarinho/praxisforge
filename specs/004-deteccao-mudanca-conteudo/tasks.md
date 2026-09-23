<!-- Criado em: 23/09/2026 11:51 -->
<!-- Modificado em: 23/09/2026 11:59 -->

# Tasks: Detecção de mudança de conteúdo pós-curadoria

**Input**: Design documents from `/specs/004-deteccao-mudanca-conteudo/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-content-check.md, quickstart.md

**Tests**: OBRIGATÓRIOS (constituição III — Test-First). Em cada grupo: escrever os testes de falha,
rodar e **confirmar vermelho**, só então implementar.

**Organization**: por user story (US1 e US2 = P1; US3 = P2).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Confirmar baseline verde na branch `004-deteccao-mudanca-conteudo` (`make lint`, `make test` com 262 testes, `make validate-data`) e `git --version` ≥ 2.x

---

## Phase 2: Foundational (bloqueia todas as stories)

**Contrato → exceções → campo no Domain → porta → adapter.**

### Testes (vermelho primeiro)

- [X] T002 [P] Testes de contrato em tests/contract/test_folders_schema.py: documento com `last_curated_commit` de 40 e de 64 hex minúsculos valida; maiúsculo, 39/41 caracteres, não-hex, `null` e número são rejeitados; `src/data/folders.yaml` atual e documentos v1 sem o campo continuam válidos (FR-011, FR-012, SC-004)
- [X] T003 [P] Testes em tests/unit/domain/test_errors.py: `ContentInspectionError` é `PraxisForgeError`; `InvalidCommitHashError` é `InvalidFolderError`; mensagens incluem o alias e nunca caminho absoluto
- [X] T004 [P] Testes em tests/unit/domain/test_folder.py: `Folder` aceita `last_curated_commit=None` (default) e hash válido em qualquer status; hash vazio, maiúsculo, curto/longo ou não-hex levanta `InvalidCommitHashError`
- [X] T005 [P] Testes em tests/unit/domain/test_folder_registry.py: `update(alias, last_curated_commit=...)` aplica só quando informado; omitido mantém o valor atual; atualização atômica (hash inválido não altera nada); mudar status sem informar hash preserva o hash (FR-010)
- [X] T006 [P] Testes em tests/integration/test_yaml_folder_registry.py: round-trip com o campo; chave omitida no YAML quando `None` (registro antigo sem diff após load/save); YAML com hash inválido falha na validação do contrato
- [X] T007 [P] Testes de integração em tests/integration/test_git_cli_inspector.py com repositórios reais em `tmp_path`: `head_commit` → hash (raiz e subpasta), `None` para pasta não-git e repositório sem commits; `changed_since` → `False` sem commits novos, `False` com commit só fora da subpasta, `True` com commit dentro, `True` com commit gravado inexistente, `True` com HEAD retrocedido e conteúdo diferente; arquivos só no working tree/ignorados não contam; mudança do ponteiro de submódulo conta (FR-005, FR-017)
- [X] T008 [P] Testes de falha em tests/integration/test_git_cli_inspector.py: executável `git` ausente (`PATH` vazio via monkeypatch), `subprocess.TimeoutExpired` simulado, código de saída inesperado (repositório corrompido: `.git/HEAD` inválido) → todos levantam `ContentInspectionError` sem caminho absoluto na mensagem; hash malformado nunca chega à linha de comando (FR-009)
- [X] T009 Rodar T002–T008 e **confirmar que falham** (vermelho)

### Implementação (verde)

- [X] T010 Adicionar propriedade opcional `last_curated_commit` (`string`, `pattern ^[0-9a-f]{40}([0-9a-f]{24})?$`, fora de `required`) em schemas/folders-schema-v1.json e atualizar `_meta.modificado_em`
- [X] T011 Adicionar `ContentInspectionError` e `InvalidCommitHashError` em src/praxisforge/domain/errors.py e reexportar em src/praxisforge/application/errors.py
- [X] T012 Adicionar campo `last_curated_commit: str | None = None` com validação de formato em src/praxisforge/domain/folder.py
- [X] T013 Aceitar `last_curated_commit` em `FolderRegistry.update()` em src/praxisforge/domain/folder_registry.py
- [X] T014 (De)serializar o campo (omitido quando `None`) em src/praxisforge/infrastructure/yaml_folder_registry.py
- [X] T015 Declarar a porta `GitContentInspector` (`head_commit(path) -> str | None`, `changed_since(path, commit) -> bool`, ambas `:raises ContentInspectionError:`) em src/praxisforge/application/ports.py
- [X] T016 Implementar `GitCliInspector` em src/praxisforge/infrastructure/git_cli_inspector.py: `subprocess.run` com lista de argumentos, `shell=False`, `timeout=10`, `git -C <pasta>`; `rev-parse --is-inside-work-tree`, `rev-parse --verify -q HEAD`, `cat-file -e <hash>^{commit}`, `diff --quiet <hash> HEAD -- .` (código 0/1/outro); validar hash por regex antes de montar o comando; `# nosec` justificado para B404/B603; logs estruturados sem caminho absoluto (research §R1, §R3, §R4)
- [X] T017 Rodar T002–T008 → verde; `make lint` e `tests/architecture/` sem violações

**Checkpoint**: contrato, Domain, porta e adapter prontos.

---

## Phase 3: User Story 1 — Registrar a versão curada ao marcar curada (P1) 🎯 MVP

**Goal**: `folders update --status curated` grava o HEAD da pasta git.

**Independent Test**: marcar como curada uma pasta git registrada e ver o hash em `folders show` e no YAML (quickstart Cenário 1).

### Testes (vermelho primeiro)

- [X] T018 [P] [US1] Testes em tests/unit/application/test_update_folder.py com fakes de `PathResolver` e `GitContentInspector`: status→curated em pasta git grava hash; pasta não-git não grava e mantém hash anterior se existir (FR-002, FR-016); remarcar curada atualiza hash (US1 cenário 3); status ≠ curated nunca consulta resolver/inspector e preserva hash (FR-010); resolver levanta `FolderPathInvalidError`/`FolderPathNotConfiguredError` → exceção propagada e registro não salvo (FR-003); inspector levanta `ContentInspectionError` → registro não salvo
- [X] T019 [P] [US1] Testes em tests/integration/test_cli_folders.py: `folders update --status curated` imprime `versão curada: <12 chars>` ou `versão curada: (pasta não é repositório git)`; caminho não configurado → exit 3 com YAML inalterado; `folders show` imprime `versão curada: <12 chars>` ou `versão curada: -`; nenhuma saída com caminho absoluto (contrato cli-content-check, FR-011, FR-013)
- [X] T020 [US1] Rodar T018–T019 e confirmar vermelho

### Implementação

- [X] T021 [US1] Estender `update_folder()` em src/praxisforge/application/update_folder.py para receber `resolver: PathResolver` e `inspector: GitContentInspector` e gravar `head_commit()` só quando o status resultante é `curated` (research §R6); log_event com `content_check` sem caminho
- [X] T022 [US1] Injetar `EnvPathResolver` + `GitCliInspector` no subcomando `folders update` e exibir `versão curada` em `update` e `show` em src/praxisforge/presentation/cli.py; mapear `ContentInspectionError` para exit 3
- [X] T023 [US1] Ajustar chamadas existentes de `update_folder()` nos testes da feature 001 (tests/unit/application/test_update_folder.py, tests/integration/test_cli_folders.py) e rodar T018–T019 → verde

**Checkpoint**: US1 entregue e testável isoladamente.

---

## Phase 4: User Story 2 — Reverter pastas curadas que mudaram (P1)

**Goal**: `folders scan` / `scan --all` revertem `curated` → `in_curation` quando o conteúdo da pasta mudou.

**Independent Test**: pasta curada com hash, commit novo dentro dela, `folders scan` → revertida (quickstart Cenários 2, 3, 5).

### Testes (vermelho primeiro)

- [X] T024 [P] [US2] Testes em tests/unit/application/test_scan_folders.py (individual) com fakes: curada + `changed_since=True` → `in_curation`, `ContentCheck.REVERTED`, hash mantido; `False` → `curated`, `UNCHANGED`, só `last_scanned` atualizado; `head_commit=None` → `NOT_GIT`, status mantido; status ≠ curated com hash remanescente → `NOT_APPLICABLE` e inspector nunca chamado (FR-007, FR-015); inspector levanta `ContentInspectionError` → exceção propagada, status/hash/`last_scanned` inalterados (FR-009); `caplog` registra `content_check` com `outcome=reverted` e nenhum caminho absoluto
- [X] T025 [P] [US2] Testes em tests/unit/application/test_scan_folders.py (lote): mistura curada alterada, curada inalterada, `ignore`, não-git, `scanned` uma com `ContentInspectionError` e dois aliases apontando para o mesmo repositório com hashes gravados diferentes (só o que tem hash antigo é revertido) → só a alterada revertida, `ignore` em `ignored`, falha em `failures` como `ItemFailure` com status/`last_scanned` intactos, demais processadas (FR-008, FR-009, SC-001, SC-002, SC-003, SC-005)
- [X] T026 [P] [US2] Testes em tests/integration/test_cli_scan.py com repositórios reais: `folders scan <alias>` imprime linha `conteúdo:` com o rótulo pt-BR; `--all` imprime alias + status + conteúdo por linha e resumo `revertidas: N`; falha do git no individual → exit 3; nenhuma saída com caminho absoluto (FR-013, FR-018, SC-006)
- [X] T027 [US2] Rodar T024–T026 e confirmar vermelho

### Implementação

- [X] T028 [US2] Criar enum `ContentCheck` (not_applicable, not_git, baseline_recorded, unchanged, reverted) com rótulo pt-BR e adicionar `content_check` a `ScanResult` em src/praxisforge/application/scan_folders.py
- [X] T029 [US2] Implementar a verificação em `_aplicar_varredura` (receber `inspector`; só para `curated`; decidir `reverted`/`unchanged`/`not_git`; em `ContentInspectionError` não persistir nada; emitir `log_event(event="content_check", alias, outcome=<ContentCheck>, error_type)` para cada pasta curada verificada, sem caminho absoluto) em src/praxisforge/application/scan_folders.py; atualizar `scan_folder()` e `scan_all_folders()` (falha vira `ItemFailure`)
- [X] T030 [US2] Injetar `GitCliInspector` no subcomando `folders scan` e exibir a coluna/linha `conteúdo` e o resumo `revertidas: N` em src/praxisforge/presentation/cli.py
- [X] T031 [US2] Ajustar testes existentes da feature 002/003 que constroem `ScanResult` ou chamam `scan_*` sem `inspector` (tests/unit/application/test_scan_folders.py, tests/integration/test_cli_scan.py) e rodar T024–T026 → verde

**Checkpoint**: US1 + US2 = valor central completo.

---

## Phase 5: User Story 3 — Pastas curadas sem versão de referência (P2)

**Goal**: legado curado sem hash recebe baseline na varredura; varredura seguinte reverte se a fonte mudar.

**Independent Test**: remover `last_curated_commit` de pasta curada, `folders scan` → `referência registrada`; novo commit + scan → revertida (quickstart Cenário 4).

- [X] T032 [P] [US3] Testes em tests/unit/application/test_scan_folders.py: curada sem hash + pasta git → grava `head_commit()`, `BASELINE_RECORDED`, status `curated`, `changed_since` não chamado; curada sem hash + não-git → `NOT_GIT`, nada gravado; segunda varredura após mudança → `REVERTED` (FR-014, US3 cenários 1–2)
- [X] T033 [P] [US3] Teste em tests/integration/test_cli_scan.py do fluxo legado completo com repositório real (baseline → commit → revertida) e rótulo `referência registrada`
- [X] T034 [US3] Rodar T032–T033 e confirmar vermelho
- [X] T035 [US3] Implementar o ramo `BASELINE_RECORDED` em src/praxisforge/application/scan_folders.py (persistir hash via `FolderRegistry.update`) e rodar T032–T033 → verde

---

## Phase 6: Polish & Cross-Cutting

- [X] T036 [P] Criar ADR docs/decisions/0005-deteccao-mudanca-por-git-cli.md (git via executável, diff restrito à pasta, schema v1 aditivo, legado recebe baseline) e listar no docs/decisions/README.md
- [X] T037 [P] Atualizar docs/reference/folders-yaml.md: substituir a seção "Limitação conhecida" pela documentação do campo `last_curated_commit` e do comportamento de reversão
- [X] T038 [P] Atualizar docs/architecture/overview.md (porta `GitContentInspector`, adapter, fluxo de scan) e docs/guides/operar-cli-praxisforge.md (saídas novas de update/show/scan)
- [X] T039 [P] Acrescentar entradas em docs/INDEX.md e docs/TODO.md (append, sem remover conteúdo)
- [X] T040 Executar os 5 cenários de specs/004-deteccao-mudanca-conteudo/quickstart.md manualmente, conferindo ausência de caminho absoluto
- [X] T041 [P] Teste de escala em tests/integration/test_scan_content_scale.py: 100 pastas curadas (repositórios git reais em `tmp_path`, metade alteradas) varridas com `scan --all` em < 30 s; todas as alteradas revertidas e nenhuma inalterada revertida (Plan §Performance Goals, SC-001, SC-003)
- [X] T042 Gates finais: `make lint`, `make test` (cobertura ≥ 90%), `make validate-data`, `make security` (bandit sem achados não justificados), `tests/architecture/` sem violações; `graphify update .`

---

## Dependencies & Execution Order

- Setup (T001) → Foundational (T002–T017) → US1 (T018–T023) e US2 (T024–T031) → US3 (T032–T035) → Polish (T036–T042).
- US1 e US2 dependem só da Foundational; tocam arquivos diferentes na Application (`update_folder.py` × `scan_folders.py`), mas ambos editam `cli.py` → T022 e T030 em sequência.
- US3 depende de US2 (mesmo `_aplicar_varredura` e enum `ContentCheck`).
- Dentro de cada fase: testes → confirmação do vermelho → implementação → verde.

## Parallel Example

```text
Foundational (testes): T002, T003, T004, T005, T006, T007, T008 em paralelo
US1 (testes): T018 ∥ T019        US2 (testes): T024 ∥ T025 ∥ T026
Polish: T036 ∥ T037 ∥ T038 ∥ T039 ∥ T041
```

## Implementation Strategy

1. **MVP** = Setup + Foundational + US1 (grava a referência) — já torna a mudança detectável.
2. **+ US2** fecha a lacuna documentada (reversão automática) — ponto natural de PR se desejar entregar em duas partes.
3. **+ US3** trata o legado; Polish e gates finais antes do PR.
