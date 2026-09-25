<!-- Criado em: 25/09/2026 14:35 -->
<!-- Modificado em: 25/09/2026 14:40 -->

# Implementation Plan: Inventário de curadoria por pasta

**Branch**: `010-inventario-curadoria` | **Date**: 25/09/2026 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-inventario-curadoria/spec.md`

## Summary

Inventário determinístico, sem LLM, de cada pasta registrada. Um walker de filesystem aplica
exclusões (lista fixa, `.gitignore` via `pathspec`, 256 KiB, binário, links, ilegível), as
convenções em `~/.config/praxisforge/curation-conventions.yaml` (junto do registro) classificam o resto (`.md` avulso
→ `unknown`, outro texto → excluído `uncurated`), e o manifesto sai ordenado e sem data. Um
reconciliador de domínio compara com o estado anterior (novo/alterado → `pending`, inalterado
mantém, sumido → `removed`). Manifesto e estado ficam em `<dir do registro>/curation/<alias>/`,
com lock `flock` e gravação atômica. CLI nova: `curation inventory` e `curation status`.
Decisões em [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12+ (uv)

**Primary Dependencies**: pyyaml, pydantic, jsonschema (existentes) + `pathspec` (declarada
agora; já presente transitivamente)

**Storage**: JSON fora do repositório (`<dir do registro>/curation/<alias>/manifest.json`,
`state.json`) e convenções `<dir do registro>/curation-conventions.yaml`; no repo só o exemplo
`src/data/curation-conventions.example.yaml`

**Testing**: pytest (unit, integration, contract, architecture), cobertura ≥ 90%; teste de
desempenho marcado `slow`

**Target Platform**: Linux, CLI local (`fcntl` disponível)

**Project Type**: CLI em camadas (Presentation → Application → Domain ← Infrastructure)

**Performance Goals**: 5.000 arquivos em < 10 s (SC-005)

**Constraints**: somente leitura nas pastas; nenhum caminho absoluto no repo nem em mensagens além
do necessário; manifesto byte a byte determinístico

**Scale/Scope**: 55 pastas registradas; dezenas a milhares de arquivos por pasta

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Camadas | Domain: convenções, artefato, reconciliação, situação (puros). Application: `inventory_folders`, `query_curation`. Infra: walker, store JSON, loader de convenções. Portas só para filesystem/armazenamento | ✅ |
| II. Contratos | 3 schemas novos `curation-{conventions,manifest,state}-schema-v1.json` com `schema_version`; validados ao ler e gravar | ✅ |
| III. Test-first | Testes de falha antes: estado corrompido, lock, pasta inacessível, ilegível, link para fora, ciclo, `.gitignore` com negação | ✅ |
| IV. Erros semânticos | `ConventionsError`, `CurationStateCorruptError`, `CurationLockedError`; lote agrega falha por pasta | ✅ |
| V. Fontes/licença/local | Nada é extraído; estado fora do repo junto do registro; caminho absoluto não gravado (paths relativos) | ✅ |
| VI. Acervo | Não toca `library/` | ✅ |
| VII. Vault | Registro da sessão no vault ao fim | ✅ |

Nenhuma violação → Complexity Tracking vazio.

**Pós-design**: reavaliado após data-model e contratos — continua ✅. Nova dependência `pathspec`
é pequena, pura Python e justificada em R3.

## Project Structure

### Documentation (this feature)

```text
specs/010-inventario-curadoria/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli-curation.md
│   ├── curation-conventions-schema-v1.json
│   ├── curation-manifest-schema-v1.json
│   └── curation-state-schema-v1.json
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
schemas/
├── curation-conventions-schema-v1.json   # cópia dos contratos
├── curation-manifest-schema-v1.json
└── curation-state-schema-v1.json
src/data/curation-conventions.example.yaml  # exemplo validado no CI (real: ~/.config/praxisforge/)
src/praxisforge/
├── domain/
│   ├── curation_artifact.py     # ArtifactKind, Stage, ExclusionReason, Artifact, ExcludedEntry, Manifest
│   ├── curation_conventions.py  # ConventionRule, Conventions.classify
│   └── curation_state.py        # ArtifactState, CurationState, reconcile, situation
├── application/
│   ├── ports.py                 # + FolderWalker, CurationStore
│   ├── inventory_folders.py     # inventário de um alias / todos, lote tolerante
│   └── query_curation.py        # status por pasta
├── infrastructure/
│   ├── filesystem_folder_walker.py  # exclusões, gitignore, hash
│   ├── json_curation_store.py       # lock, leitura validada, gravação atômica
│   └── yaml_conventions_loader.py
└── presentation/cli.py          # grupo `curation`
tests/
├── unit/domain/test_curation_{artifact,conventions,state}.py
├── integration/test_filesystem_folder_walker.py
├── integration/test_json_curation_store.py
├── integration/test_inventory_folders.py
├── integration/test_query_curation.py
├── contract/test_curation_schemas.py
└── integration/test_cli_curation.py
docs/decisions/0013-inventario-de-curadoria.md
docs/guides/inventariar-curadoria.md
```

**Structure Decision**: mantém a estrutura única de `src/praxisforge` em quatro camadas; os
módulos novos seguem o prefixo `curation_` para não colidir com `curation_status.py` (status da
pasta no registro, feature 006).

## Complexity Tracking

Sem violações da constituição.
