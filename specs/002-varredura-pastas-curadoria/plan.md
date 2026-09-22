<!-- Criado em: 22/09/2026 11:55 -->
<!-- Modificado em: 22/09/2026 11:48 -->

# Implementation Plan: Varredura das Pastas Registradas

**Branch**: `002-varredura-pastas-curadoria` | **Date**: 22/09/2026 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-varredura-pastas-curadoria/spec.md`

## Summary

Adicionar um caso de uso de varredura (scan) que reaproveita o `PathResolver` e o
`FolderRegistryRepository` da feature 001 para: (1) varrer um único alias, atualizando
`last_scanned` e avançando `status` de "não varrida" para "varrida" quando aplicável;
(2) varrer todos os aliases em lote, com isolamento de falha por item (constituição IV);
(3) detectar, na varredura em lote, grupos de aliases cujo caminho real resolvido é idêntico,
reportando-os de forma apenas informativa. Nenhuma infraestrutura nova é criada — a varredura é
um novo caso de uso Application que compõe `PathResolver.resolve()` + `FolderRegistry.update()`
já existentes.

## Technical Context

**Language/Version**: Python 3.12+ (mesmo ambiente da feature 001)

**Primary Dependencies**: nenhuma nova — reaproveita `pydantic`, `pyyaml`, `jsonschema[format]`
já presentes em `pyproject.toml`

**Storage**: mesmo `src/data/folders.yaml`, mesmo contrato `schemas/folders-schema-v1.json`
(nenhum campo novo é necessário — `status`/`last_scanned` já existem)

**Testing**: pytest + pytest-cov, mesmo padrão de fakes de porta (ABC subclassing) da feature 001

**Target Platform**: CLI Linux (mesmo `praxisforge` entry point)

**Project Type**: CLI (single project, mesma estrutura de camadas da feature 001)

**Performance Goals**: varrer 200 pastas registradas processando as 190 válidas mesmo com 10
falhas, sem interromper o lote (SC-002, mesma ordem de grandeza da feature 001)

**Constraints**: nenhuma saída (mensagem, log, relatório) MUST conter caminho absoluto do
sistema de arquivos fora de uma mensagem de erro sobre a própria pasta (FR-010/SC-004, herdado
da constituição V); varredura NÃO MUST alterar `description`/`content_type`/`license` (FR-011)

**Scale/Scope**: mesma escala da feature 001 — dezenas a poucas centenas de pastas registradas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Arquitetura em Camadas**: PASS. Novo caso de uso vive em `application/scan_folders.py`,
  compõe as portas já existentes (`FolderRegistryRepository`, `PathResolver`); nenhuma
  Infrastructure nova; Presentation ganha só um subcomando CLI fino (`folders scan`).
- **II. Contratos Validados e Versionados**: PASS. Nenhuma mudança de schema — `status` e
  `last_scanned` já fazem parte de `folders-schema-v1.json`; a varredura só grava valores já
  contemplados pelo contrato existente via `FolderRegistry.update()` (que já valida invariantes
  no `Folder.__post_init__`).
- **III. Test-First (NON-NEGOTIABLE)**: PASS (a cumprir em `/speckit-tasks` + `/speckit-implement`
  com a mesma disciplina vermelho→verde da feature 001).
- **IV. Erros Semânticos nas Fronteiras**: PASS. Reaproveita `FolderNotFoundError`,
  `FolderPathNotConfiguredError`, `FolderPathInvalidError`, `FolderPathUnreadableError` já
  definidos no Domain; lote agrega falha por item via `ItemFailure` (mesmo padrão de
  `resolve_folder_path.py`), sem exceção nova necessária.
- **V. Proveniência e Licença das Fontes**: PASS. Varredura não lê nem grava `license`; caminho
  absoluto nunca é exposto fora de mensagem de erro pontual (FR-010), mesma regra já testada na
  feature 001.
- **VI/VII**: N/A para este plano de código (skills/vault não são tocados por esta feature).

Nenhuma violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-varredura-pastas-curadoria/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/praxisforge/
├── application/
│   ├── scan_folders.py       # NOVO — scan_folder(), scan_all_folders()
│   ├── ports.py               # inalterado (reaproveita FolderRegistryRepository, PathResolver)
│   ├── logging_events.py      # inalterado (log_event reaproveitado)
│   └── errors.py              # inalterado (re-exports já cobrem os erros necessários)
├── domain/                    # inalterado — FolderRegistry.update() já cobre a mudança de estado
├── infrastructure/            # inalterado — EnvPathResolver, YamlFolderRegistryRepository
└── presentation/
    └── cli.py                 # +subcomandos `folders scan --alias` e `folders scan --all`

tests/
├── unit/application/
│   └── test_scan_folders.py   # NOVO
├── integration/
│   └── test_cli_scan.py       # NOVO
└── contract/                  # inalterado — nenhum schema novo
```

**Structure Decision**: mesma estrutura em camadas single-project da feature 001; a varredura é
puramente um novo módulo Application + um subcomando CLI, sem novas pastas de topo nem novo
adapter de Infrastructure.

## Complexity Tracking

*Nenhuma violação de constituição — seção não aplicável.*
