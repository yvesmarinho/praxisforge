<!-- Criado em: 22/09/2026 12:20 -->
<!-- Modificado em: 22/09/2026 12:02 -->

---

description: "Tasks — 002-varredura-pastas-curadoria"

---

# Tasks: Varredura das Pastas Registradas

**Input**: Design documents from `/specs/002-varredura-pastas-curadoria/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: OBRIGATÓRIOS (constituição III — Test-First, NON-NEGOTIABLE). Em cada fase a ordem é: testes de falha → confirmar vermelho → implementação → verde. Implementação escrita antes dos testes deve ser descartada.

**Organization**: agrupadas por user story; cada fase é um incremento testável de forma independente. Nenhuma camada de Domain/Infrastructure nova é criada — toda a feature vive em `application/scan_folders.py` + um subcomando CLI (ver `plan.md`/`research.md`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência em tarefa incompleta)
- **[Story]**: US1–US3 (mapeia para as user stories da spec)
- Caminhos relativos à raiz do repositório

## Convenções de código (valem para toda tarefa que cria/edita `.py`)

- Cabeçalho `# -*- coding: utf-8 -*-` + docstring de programa (NOME, TITULO, DATA, MODIFICADO, VERSÃO, DEPEND, HISTÓRICO, STATUS); datas do sistema em `America/Sao_Paulo`
- Type hints em parâmetros e retornos; docstrings reST (`:param:`, `:return:`); `pathlib`; imports seletivos
- Sem `print()`: a CLI escreve com `sys.stdout.write`/`sys.stderr.write`; logs via `logging`
- Application: reaproveita `ItemFailure` (de `application/resolve_folder_path.py`), `log_event` (de `application/logging_events.py`), portas de `application/ports.py` — nenhuma porta/adapter novo
- Nenhum caminho absoluto em código, saída CLI, logs ou relatório de lote (FR-010/SC-004) — resultados agrupam por `Path` só internamente, nunca serializam o caminho
- Listas em relatórios (ok, failures, duplicates) MUST ser ordenadas por alias — determinismo para testes (checklist CHK020)
- Ao concluir cada grupo: `make lint && make test` verdes antes de seguir

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: confirmar baseline verde; nenhuma dependência nova é necessária (reaproveita 100% o ambiente da feature 001)

- [X] T001 Rodar `uv sync && make lint && make test` a partir da branch `002-varredura-pastas-curadoria` e confirmar baseline 100% verde antes de iniciar qualquer tarefa nova

**Checkpoint**: ambiente confirmado; nenhuma tarefa de infraestrutura adicional necessária.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: nesta feature não há pré-requisito bloqueante além do que a feature 001 já entrega —
`FolderRegistry.update()`, `PathResolver`, `FolderRegistryRepository`, `ItemFailure` e `log_event`
já existem e são reaproveitados sem alteração (ver `research.md`, Decisões 1–3). Nenhuma tarefa
foundational é necessária; as user stories começam diretamente na Fase 3.

**Checkpoint**: N/A — sem tarefas nesta fase.

---

## Phase 3: User Story 1 — Varrer uma pasta registrada (Priority: P1) 🎯 MVP

**Goal**: `folders scan <alias>` atualiza `last_scanned` e avança `status` de "não varrida" para
"varrida" quando aplicável, sem tocar em pastas com falha de resolução.

**Independent Test**: registrar uma pasta, apontar `PRAXISFORGE_FOLDER_<ALIAS>` para um diretório
real, rodar `folders scan <alias>` e confirmar `last_scanned` atualizado e status avançado
(quickstart.md, Cenário 1).

### Testes primeiro (vermelho)

- [X] T002 [P] [US1] Escrever `tests/unit/application/test_scan_folders.py` com os casos de
      `scan_folder()`: pasta `not_scanned` → status vira `scanned` e `last_scanned` recebe o
      timestamp; pasta `scanned`/`in_curation`/`curated`/`pending` → status inalterado, só
      `last_scanned` avança (cobre o edge case de pasta "pendente" da spec e resolve a checklist
      CHK023, deixando explícito que `PENDING` nunca é sobrescrito pela varredura); alias não
      registrado → `FolderNotFoundError` sem chamar `resolver.resolve()` nem `repository.save()`;
      falha de caminho (`FolderPathNotConfiguredError`/`FolderPathInvalidError`/
      `FolderPathUnreadableError`) → propaga a exceção e não altera o registro; log estruturado do
      evento sem caminho absoluto
- [X] T003 [P] [US1] Escrever `tests/integration/test_cli_scan.py` com os casos de
      `folders scan <alias>`: sucesso → exit code 0, mensagem confirma alias/status/last_scanned;
      alias inexistente → exit code 1, mensagem cita o alias; caminho quebrado (variável ausente)
      → exit code 1, mensagem cita o motivo; nenhuma saída contém caminho absoluto do sistema de
      arquivos
- [X] T004 [US1] Rodar `uv run pytest tests/unit/application/test_scan_folders.py tests/integration/test_cli_scan.py -p no:cacheprovider` e **confirmar que T002–T003 falham** (ImportError/AssertionError, `scan_folders.py` e o subcomando `scan` ainda não existem)

### Implementação (verde)

- [X] T005 [US1] Implementar `src/praxisforge/application/scan_folders.py`: dataclass frozen
      `ScanResult` (alias, status, last_scanned) e a função `scan_folder(repository, resolver, alias)`
      — carrega o registro, confirma o alias existe, resolve o caminho via `PathResolver`, monta
      `last_scanned=datetime.now(timezone.utc)`, chama `FolderRegistry.update()` só com
      `status=CurationStatus.SCANNED` quando o status atual é `NOT_SCANNED` (senão sem `status`),
      persiste via `repository.save()`, loga via `log_event` — faz T002 passar
- [X] T006 [US1] Adicionar o subcomando `folders scan <alias>` em `src/praxisforge/presentation/cli.py`
      (novo `scan_parser = folders_sub.add_parser("scan")`, grupo mutuamente exclusivo com `alias`
      posicional opcional, igual ao padrão já usado por `folders resolve`); handler converte
      `ScanResult` em mensagem amigável (exit 0) e cada exceção semântica em mensagem + exit code 1,
      sem vazar caminho absoluto — faz T003 passar
- [X] T007 [US1] Rodar `make lint && make test` e confirmar verde, cobertura ≥ 90%

**Checkpoint**: MVP entregável — varredura individual funciona de ponta a ponta (quickstart.md
Cenários 1–2).

---

## Phase 4: User Story 2 — Varrer todas as pastas em lote (Priority: P2)

**Goal**: `folders scan --all` varre todos os aliases registrados, isolando a falha de cada item
sem interromper os demais, e reporta um resumo com contagem de sucesso/falha.

**Independent Test**: registrar três pastas (duas com caminho válido, uma inválida), rodar
`folders scan --all` e confirmar que as duas válidas são atualizadas e a inválida é reportada como
falha, sem interromper as demais (quickstart.md, Cenário 3).

### Testes primeiro (vermelho)

- [X] T008 [P] [US2] Adicionar a `tests/unit/application/test_scan_folders.py` os casos de
      `scan_all_folders()`: lote com pastas válidas e inválidas → `ok` contém as válidas,
      `failures` contém as inválidas com `alias`/`error_type`/`message`, sem levantar; registro
      vazio (`folders: {}`) → `ok == []` e `failures == []` (resolve checklist CHK001); todas as
      pastas falham → `ok == []` e `failures` com todos os itens, sem levantar (resolve checklist
      CHK002); `ok` e `failures` ordenados por alias (checklist CHK020)
- [X] T009 [P] [US2] Adicionar a `tests/integration/test_cli_scan.py` os casos de
      `folders scan --all`: resumo final cita quantas pastas foram atualizadas e quantas falharam,
      com o motivo de cada falha, exit code 0 mesmo havendo falhas de item; chamar `folders scan`
      com `<alias>` e `--all` ao mesmo tempo → exit code 2 (uso incorreto, grupo mutuamente
      exclusivo)
- [X] T010 [US2] Rodar `uv run pytest tests/unit/application/test_scan_folders.py tests/integration/test_cli_scan.py -p no:cacheprovider` e **confirmar que T008–T009 falham**

### Implementação (verde)

- [X] T011 [US2] Implementar `scan_all_folders(repository, resolver)` em
      `src/praxisforge/application/scan_folders.py`: dataclass frozen `ScanBatchReport` (`ok:
      list[ScanResult]`, `failures: list[ItemFailure]`, `duplicates: list[DuplicateAliasGroup]` —
      campo `duplicates` inicializado vazio nesta tarefa, populado só na US3); itera
      `registry.list()`, chama `scan_folder()` por alias dentro de `try/except Exception` (mesmo
      padrão `# noqa: BLE001` de `resolve_all_folder_paths`), agrega `ItemFailure` por item sem
      interromper o lote, ordena `ok`/`failures` por alias — faz T008 passar
- [X] T012 [US2] Adicionar `--all` (mutuamente exclusivo com o `alias` posicional) ao parser
      `folders scan` em `cli.py`; handler chama `scan_all_folders()` e imprime o resumo
      (contagem de ok/falhas + motivo de cada falha), sem caminho absoluto — faz T009 passar
- [X] T013 [US2] Rodar `make lint && make test` e confirmar verde, cobertura ≥ 90%

**Checkpoint**: varredura em lote funciona com isolamento de falha por item confirmado
(quickstart.md Cenário 3, SC-002).

---

## Phase 5: User Story 3 — Detectar a mesma pasta física sob dois aliases (Priority: P3)

**Goal**: `folders scan --all` detecta e reporta grupos de aliases cujo caminho real resolvido é
idêntico, sem impedir a varredura de nenhum deles.

**Independent Test**: registrar dois aliases apontando para o mesmo diretório real, rodar
`folders scan --all` e confirmar que o relatório final lista o par de aliases duplicados
(quickstart.md, Cenário 4).

### Testes primeiro (vermelho)

- [X] T014 [P] [US3] Adicionar a `tests/unit/application/test_scan_folders.py` os casos de
      detecção de duplicidade dentro de `scan_all_folders()`: dois aliases resolvendo para o mesmo
      caminho real → um `DuplicateAliasGroup` com os dois aliases (ordenados), ambos continuam em
      `ok`; três aliases resolvendo para o mesmo caminho real → um único grupo com os três aliases,
      não três pares (resolve checklist CHK003); `DuplicateAliasGroup` carrega só `aliases`, nunca
      o `Path`/caminho absoluto, nem em `repr()` (resolve checklist CHK019); um alias que falha ao
      resolver o caminho não entra na comparação de duplicidade daquela execução (resolve checklist
      CHK015); nenhum agrupamento é criado quando todos os caminhos resolvidos são distintos
- [X] T015 [P] [US3] Adicionar a `tests/integration/test_cli_scan.py` o caso de `folders scan --all`
      listando os grupos de aliases duplicados no resumo final, sem interromper a varredura de
      nenhum alias envolvido, sem caminho absoluto na saída
- [X] T016 [US3] Rodar `uv run pytest tests/unit/application/test_scan_folders.py tests/integration/test_cli_scan.py -p no:cacheprovider` e **confirmar que T014–T015 falham**

### Implementação (verde)

- [X] T017 [US3] Implementar a dataclass frozen `DuplicateAliasGroup` (`aliases: tuple[str, ...]`,
      ≥ 2 elementos) e a detecção dentro de `scan_all_folders()`: após resolver com sucesso cada
      alias, agrupar por `Path` resolvido (`dict[Path, list[str]]`), gerar um `DuplicateAliasGroup`
      ordenado por alias para cada grupo com ≥ 2 aliases, popular `ScanBatchReport.duplicates`
      (ordenado por primeiro alias do grupo) — faz T014 passar
- [X] T018 [US3] Exibir os grupos duplicados no resumo de `folders scan --all` em `cli.py` (lista de
      aliases por grupo, sem caminho) — faz T015 passar
- [X] T019 [US3] Rodar `make lint && make test` e confirmar verde, cobertura ≥ 90%

**Checkpoint**: as três user stories entregues; `folders scan --all` cobre varredura, isolamento de
falha e detecção de duplicidade (quickstart.md Cenário 4, SC-003).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: documentação e validação final, sem lógica nova

- [X] T020 [P] Atualizar `docs/architecture/overview.md` (mapa de módulos) com
      `application/scan_folders.py` e o subcomando `folders scan`
- [X] T021 [P] Rodar manualmente os 4 cenários de `quickstart.md` (incluindo a verificação de
      segurança — nenhum caminho absoluto na saída de `folders scan --all`) e confirmar aderência
- [X] T022 Atualizar `docs/INDEX.md` e `docs/TODO.md` (acrescentar, nunca sobrescrever): feature 002
      concluída, próximos pendentes
- [X] T023 Marcar T001–T022 como concluídas neste arquivo à medida que forem fechadas

**Checkpoint final**: `make lint && make test` verdes, `make validate-data` verde, cobertura ≥ 90%,
nenhum item pendente na checklist `checklists/batch-robustness.md` sem justificativa registrada.

---

## Dependencies & Execution Order

```text
Phase 1 (Setup) ──> Phase 3 (US1, P1) ──> Phase 4 (US2, P2) ──> Phase 5 (US3, P3) ──> Phase 6 (Polish)
```

- Phase 2 (Foundational) não tem tarefas — nada bloqueia as user stories além do já entregue pela
  feature 001.
- US2 depende de US1 (`scan_all_folders` compõe `scan_folder`); US3 depende de US2 (a detecção de
  duplicidade usa a mesma passada de resolução de caminho do lote). Não é possível paralelizar
  US1/US2/US3 entre si — apenas os pares de testes dentro de cada fase (`[P]`) são paralelizáveis.

## Parallel Execution Examples

Dentro da Fase 3 (US1): T002 e T003 tocam arquivos diferentes (`test_scan_folders.py` vs.
`test_cli_scan.py`) e podem ser escritos em paralelo antes de T004.

Dentro da Fase 4 (US2): T008 e T009 idem, arquivos diferentes.

Dentro da Fase 5 (US3): T014 e T015 idem, arquivos diferentes.

Fase 6: T020 e T021 são independentes entre si (documentação vs. validação manual) e podem rodar
em paralelo.

## Implementation Strategy

- **MVP primeiro**: Fase 1 → Fase 3 (US1) entrega `folders scan <alias>` funcional e já é
  independentemente testável/demonstrável (quickstart.md Cenários 1–2).
- **Incremento 2**: Fase 4 (US2) adiciona `folders scan --all` com isolamento de falha.
- **Incremento 3**: Fase 5 (US3) adiciona a detecção de duplicidade sobre o lote já existente.
- **Fechamento**: Fase 6 documenta e valida ponta a ponta.
