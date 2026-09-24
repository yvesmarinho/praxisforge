<!-- Criado em: 24/09/2026 14:25 -->
<!-- Modificado em: 24/09/2026 14:25 -->

# Tasks: Registro de pastas fora do repositório

**Input**: Design documents from `/specs/007-registro-fora-do-repo/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-registry.md, quickstart.md

**Tests**: OBRIGATÓRIOS (constituição III). Em cada grupo: testes de falha → confirmar vermelho →
implementar → verde.

**Organization**: US1 (P1) local padrão fora do repo; US2 (P2) precedência/override; US3 (P3)
`folders relocate`.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Confirmar baseline verde na branch `007-registro-fora-do-repo` com `src/data/folders.yaml` na versão do HEAD (guardar o registro local em cópia de segurança no scratchpad; `make lint`, `make test`, `make validate-data`; restaurar); nunca commitar o registro local

---

## Phase 2: Foundational (bloqueia todas as stories)

### Testes (vermelho primeiro)

- [X] T002 [P] Testes em tests/unit/domain/test_errors.py: `RegistryFileNotFoundError(location)` mantém a base `RegistryUnavailableError`, expõe `location` e a mensagem contém o local, `folders add` e `folders bootstrap`; `RegistryAlreadyExistsError(location)` e `RegistryRelocationError(reason)` ⊂ `PraxisForgeError` com mensagens citando o local/motivo
- [X] T003 [P] Testes em tests/unit/infrastructure/test_registry_location.py (criar pacote `tests/unit/infrastructure/` se não existir) para `resolve_registry_path(cli_value, env, home, cwd)`: só fallback → `home/.config/praxisforge/folders.yaml`; `XDG_CONFIG_HOME` absoluta → `<xdg>/praxisforge/folders.yaml`; `XDG_CONFIG_HOME` vazia ou relativa → fallback; `PRAXISFORGE_REGISTRY` vence XDG; vazia é ignorada; `cli_value` vence tudo; `~` expandido com o `home` recebido; relativo resolvido contra `cwd` (FR-001, FR-002, FR-012)
- [X] T004 [P] Testes em tests/unit/infrastructure/test_registry_location.py para `find_legacy_registry(cwd)`: devolve o caminho quando `<cwd>/src/data/folders.yaml` existe com ao menos uma pasta; `None` quando ausente, com `folders: {}`, ilegível ou YAML inválido (FR-008)
- [X] T005 Rodar T002–T004 e **confirmar vermelho**

### Implementação

- [X] T006 Em src/praxisforge/domain/errors.py: `RegistryFileNotFoundError` recebe `location: str`; adicionar `RegistryAlreadyExistsError` e `RegistryRelocationError` (+ `__all__`); reexportar em src/praxisforge/application/errors.py; ajustar chamadas existentes (src/praxisforge/infrastructure/yaml_folder_registry.py passa `str(self._path)`)
- [X] T007 Criar src/praxisforge/infrastructure/registry_location.py com `resolve_registry_path` e `find_legacy_registry` (stdlib, sem caminho fixo de máquina; cabeçalho e docstrings reST com doctest)
- [X] T008 Fixture `autouse` em tests/conftest.py: `XDG_CONFIG_HOME=<tmp_path>/xdg` e remove `PRAXISFORGE_REGISTRY` (nenhum teste toca o `~/.config` real — SC-001)
- [X] T009 Rodar T002–T004 e a suíte inteira; **confirmar verde**; `make lint`

**Checkpoint**: resolução do local e exceções prontas.

---

## Phase 3: User Story 1 — Registro no local padrão fora do repo (P1) 🎯 MVP

**Goal**: sem `--registry`, a CLI usa `<config do usuário>/praxisforge/folders.yaml`; o repositório só versiona o exemplo.

**Independent Test**: com `XDG_CONFIG_HOME` temporário, `folders add` cria o registro lá e `folders list` o lê; nenhum arquivo do repositório muda.

### Testes (vermelho primeiro)

- [X] T010 [P] [US1] Testes em tests/integration/test_cli_registry_location.py: sem `--registry`, `folders add` cria `<xdg>/praxisforge/folders.yaml` (pasta criada) e `folders list` lista a pasta; `folders bootstrap` também cria no local padrão; sem `XDG_CONFIG_HOME` (monkeypatch `HOME`) → `<home>/.config/praxisforge/folders.yaml`
- [X] T011 [P] [US1] Acrescentar em tests/integration/test_cli_registry_location.py: com registro ausente, `list`, `show`, `update`, `resolve`, `scan`, `validate` e `migrate` saem com 1, a mensagem cita o local resolvido e sugere `folders add`/`folders bootstrap`, e nada é criado (FR-004, SC-004)
- [X] T012 [P] [US1] Acrescentar em tests/integration/test_yaml_folder_registry.py: `load`/`load_raw` de arquivo ausente levantam `RegistryFileNotFoundError` com `location` igual ao caminho do arquivo
- [X] T013 [P] [US1] Testes de contrato em tests/contract/test_folders_example.py: `src/data/folders.example.yaml` existe, é válido em `folders-schema-v2`, tem ao menos 3 pastas e nenhum caminho com `/home/`, `/Users/` ou `C:\`; `src/data/folders.yaml` está listado no `.gitignore` (FR-005–FR-007)
- [X] T014 [US1] Rodar T010–T013 e **confirmar vermelho**

### Implementação

- [X] T015 [US1] Em src/praxisforge/presentation/cli.py: `--registry` com `default=None`; remover `_DEFAULT_REGISTRY`; resolver com `resolve_registry_path(args.registry, os.environ, Path.home(), Path.cwd())` antes de criar o repositório
- [X] T016 [US1] Criar src/data/folders.example.yaml (v2, 3 pastas fictícias em `/srv/praxisforge/...`, uma `pending`/`unknown`); adicionar `src/data/folders.yaml` ao .gitignore; `git rm --cached src/data/folders.yaml` (o arquivo local permanece no disco)
- [X] T017 [US1] No Makefile, `validate-data` valida `src/data/folders.example.yaml` em vez de `src/data/folders.yaml`
- [X] T018 [US1] Rodar T010–T013 e a suíte inteira **com o registro local populado presente** e **confirmar verde** (SC-001); `make lint`, `make validate-data`

**Checkpoint**: MVP entregue — registro real fora do repo, gates verdes com registro pessoal.

---

## Phase 4: User Story 2 — Outro local por opção ou variável (P2)

**Goal**: `--registry` > `PRAXISFORGE_REGISTRY` > XDG > `~/.config`, ponta a ponta na CLI.

**Independent Test**: variável e opção com arquivos diferentes; conferir qual é lido/gravado.

### Testes (vermelho primeiro)

- [X] T019 [P] [US2] Acrescentar em tests/integration/test_cli_registry_location.py: `PRAXISFORGE_REGISTRY` usada sem `--registry`; `--registry` vence a variável; variável vazia ignorada; variável com `~` expandida; variável para arquivo inexistente → `add` cria lá e `list` falha como ausente (US2 cen. 1–4, Edge Cases)
- [X] T020 [P] [US2] Acrescentar em tests/integration/test_cli_registry_location.py: local resolvido é diretório → exit 2 citando o local; local é link simbólico para arquivo → lido normalmente (Edge Cases)
- [X] T021 [US2] Rodar T019–T020 e **confirmar vermelho** (os casos já cobertos pela Phase 2/3 podem passar; registrar quais falham)

### Implementação

- [X] T022 [US2] Em src/praxisforge/presentation/cli.py: rejeitar local resolvido que é diretório com exit 2 (`_EXIT_USO`) e mensagem citando o local, antes de despachar
- [X] T023 [US2] Rodar T019–T020 e **confirmar verde**; `make lint`

---

## Phase 5: User Story 3 — `folders relocate` (P3)

**Goal**: mover o registro antigo para o local resolvido com segurança.

**Independent Test**: com `src/data/folders.yaml` populado (em `tmp_path` como cwd) e destino vazio, `folders relocate` deixa o destino idêntico e remove a origem; destino existente → recusa.

### Testes (vermelho primeiro)

- [X] T024 [P] [US3] Testes em tests/unit/application/test_relocate_registry.py com fakes (repositório de origem, `RegistryFileMover`): destino existe → `RegistryAlreadyExistsError` e mover não é chamado; origem ausente → `RegistryFileNotFoundError`; origem v1 → `RegistryMigrationRequiredError`; origem inválida → `ContractValidationError`; origem sem pastas → recusa (erro semântico) sem mover; caso válido → mover chamado uma vez e resultado com a quantidade de pastas; falha do mover propaga `RegistryRelocationError` (FR-009, FR-010, FR-013)
- [X] T025 [P] [US3] Testes de integração em tests/integration/test_filesystem_registry_mover.py com arquivos reais em `tmp_path`: move preservando bytes e cria a pasta do destino; origem removida só após verificar o destino; destino sem permissão de escrita → `RegistryRelocationError`, origem intacta e sem arquivo parcial; falha simulada na verificação (monkeypatch) → destino parcial removido, origem intacta (FR-013)
- [X] T026 [P] [US3] Testes em tests/integration/test_cli_relocate.py (monkeypatch do cwd para `tmp_path`): com `src/data/folders.yaml` populado e registro ausente, `folders list` imprime no stderr a dica `registro antigo encontrado em src/data/folders.yaml — execute: praxisforge folders relocate`; registro antigo vazio não gera dica; `folders relocate` → exit 0, `registro movido para <local> (N pastas)`, conteúdo idêntico e origem removida; repetir → exit 1 (destino existe); `--from` com outro arquivo; `--registry`/`PRAXISFORGE_REGISTRY` definem o destino; origem vazia → exit 1; sem permissão → exit 3 (contracts/cli-registry.md)
- [X] T027 [P] [US3] Teste de escala em tests/integration/test_cli_relocate.py: registro de 60 pastas realocado em < 1 s (SC-003)
- [X] T028 [US3] Rodar T024–T027 e **confirmar vermelho**

### Implementação

- [X] T029 [US3] Porta `RegistryFileMover` (`move(source: Path, target: Path) -> None`) em src/praxisforge/application/ports.py e adapter src/praxisforge/infrastructure/filesystem_registry_mover.py (cria pasta do destino, `shutil.copy2`, compara bytes, remove a origem; limpeza do destino parcial em falha; `OSError` → `RegistryRelocationError`)
- [X] T030 [US3] Caso de uso src/praxisforge/application/relocate_registry.py (`relocate_registry(source, target, target_exists, mover) -> RelocationResult`), ordem: destino existe → recusa; `source.load()` valida (v1/inválido/ausente); sem pastas → recusa; mover; log estruturado
- [X] T031 [US3] Em src/praxisforge/presentation/cli.py: subcomando `folders relocate [--from]` (padrão `src/data/folders.yaml` relativo ao cwd); dica de registro antigo (via `find_legacy_registry`) no stderr para comandos de leitura quando o registro resolvido não existe; mapear `RegistryRelocationError` → exit 3
- [X] T032 [US3] Rodar T024–T027 e **confirmar verde**; `make lint`; verificar tests/architecture

**Checkpoint**: todas as stories funcionais.

---

## Phase 6: Polish & Cross-Cutting

- [X] T033 [P] ADR docs/decisions/0008-registro-fora-do-repositorio.md (local, precedência, `relocate` × `migrate`, exemplo versionado, risco em outros clones, limitação do cwd)
- [X] T034 [P] Atualizar docs/reference/folders-yaml.md e docs/guides/operar-cli-praxisforge.md (local padrão, precedência, `PRAXISFORGE_REGISTRY`, `folders relocate`, aviso de rodar `relocate` antes de atualizar outros clones); **acrescentar** ao README.md (sem apagar conteúdo) a atualização da seção da CLI (FR-011)
- [X] T035 [P] Atualizar docs/architecture/overview.md (módulo `registry_location`, porta `RegistryFileMover`, caso de uso `relocate_registry`)
- [X] T036 [P] **Acrescentar** a docs/TODO.md a limitação conhecida: CLI resolve `schemas/` e o registro antigo pelo diretório atual
- [X] T037 Executar os cenários de specs/007-registro-fora-do-repo/quickstart.md com `XDG_CONFIG_HOME` descartável
- [X] T038 **Com confirmação do usuário**: realocar o registro real deste clone (`cp` de segurança → `uv run praxisforge folders relocate` → `folders list`/`validate`)
- [X] T039 Gates finais **com o registro pessoal no local padrão**: `make lint`, `ruff format --check` nos arquivos alterados, `make test` (cobertura ≥ 90%), `make validate-data`, `make security`; `graphify update .`
- [X] T040 Relatório em docs/bugs/ apenas se surgir bug; registrar a sessão no vault `claude_memory` (projects/praxisforge.md)

---

## Dependencies & Execution Order

- Setup (T001) → Foundational (T002–T009) → US1 (T010–T018) → US2 (T019–T023) → US3 (T024–T032) → Polish (T033–T040).
- US2 depende da resolução (Foundational) e do cabeamento da CLI (T015).
- US3 depende das exceções (T006), de `find_legacy_registry` (T007) e do local resolvido (T015); independe da US2.
- T038 só com confirmação explícita do usuário (mexe no registro real).

## Parallel Examples

- Foundational: T002, T003 e T004 juntos.
- US1: T010–T013 juntos.
- US3: T024–T027 juntos; US3 pode andar em paralelo com a US2 após a US1.
- Polish: T033–T036 juntos.

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1 (T001–T018) — registro fora do repo e gates verdes.
2. US2: override por opção/variável (maior parte já coberta pela resolução).
3. US3: realocação segura do registro antigo.
4. Polish: ADR, docs, realocação real (com confirmação), gates.
