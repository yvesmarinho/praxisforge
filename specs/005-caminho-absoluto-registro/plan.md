<!-- Criado em: 23/09/2026 13:03 -->
<!-- Modificado em: 23/09/2026 13:03 -->

# Implementation Plan: Caminho absoluto no registro de pastas

**Branch**: `005-caminho-absoluto-registro` | **Date**: 23/09/2026 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-caminho-absoluto-registro/spec.md`

## Summary

`Folder` ganha o campo obrigatório `path` (absoluto, canônico) e `FolderRegistry` passa a garantir
unicidade de caminho. O contrato evolui para `folders-schema-v2.json` (`schema_version: "2"`,
`path` obrigatório) — mudança incompatível. Comandos deixam de consultar
`PRAXISFORGE_FOLDER_<ALIAS>`: um novo adapter de filesystem canoniza caminhos no registro e valida
acessibilidade nas operações. O bootstrap gera aliases `<raiz>__<subpasta>` (truncamento + sufixo
numérico) e é idempotente por caminho. Novo comando `folders migrate [--root DIR]` converte o
registro v1 (variável de ambiente → subpasta da raiz), de forma atômica. `folders update` aceita
`--path`. A leitura de um registro v1 por qualquer outro comando falha pedindo migração.

## Technical Context

**Language/Version**: Python 3.12+ (mesmo ambiente das features 001–004)

**Primary Dependencies**: nenhuma nova (pathlib/os da stdlib)

**Storage**: `src/data/folders.yaml` em `schema_version: "2"`; `schemas/folders-schema-v2.json` novo;
`folders-schema-v1.json` mantido só para a migração (constituição II: breaking → novo major)

**Testing**: pytest + pytest-cov; fakes de porta; integração com pastas reais em `tmp_path`

**Target Platform**: CLI Linux

**Project Type**: CLI (single project, 4 camadas)

**Performance Goals**: migração e bootstrap de 100 pastas em < 5 s em disco local

**Constraints**: caminho absoluto só no registro, em `show`/`list`/`resolve` e em erro sobre o próprio
item (FR-012); nenhum caminho fixo no código-fonte; migração atômica (FR-011)

**Scale/Scope**: dezenas a poucas centenas de pastas (registro local atual: 55)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Camadas**: PASS. Domain valida só a forma do caminho (absoluto, sem `..`, sem `~`) —
  sem tocar o disco; canonização e checagem de existência ficam atrás da porta
  `FolderLocator` (adapter `FilesystemFolderLocator`); leitura legada de variáveis de ambiente
  fica atrás da porta `LegacyPathSource` (adapter `EnvLegacyPathSource`), usada só pela migração.
- **II. Contratos**: PASS. Campo obrigatório novo = breaking → `folders-schema-v2.json`,
  `schema_version: "2"`; v1 lido apenas pelo caso de uso de migração.
- **III. Test-First**: PASS (tasks/implement); dependência externa (filesystem) com testes de
  pasta inexistente, sem permissão, link simbólico.
- **IV. Erros semânticos**: PASS. Novas exceções: `InvalidFolderPathError` (forma),
  `PathAlreadyRegisteredError` (duplicidade, cita o alias ocupante),
  `RegistryMigrationRequiredError` (registro v1); falhas da migração agregadas por item.
- **V. Proveniência, Licença e Localização (v2.0.0)**: PASS. `path` obrigatório e único no YAML;
  saídas em lote e logs só com alias (FR-012).
- **VI/VII**: N/A.

**Resultado**: sem violações.

## Project Structure

### Documentation (this feature)

```text
specs/005-caminho-absoluto-registro/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/cli-path.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
schemas/folders-schema-v2.json                     # NOVO (path obrigatório, schema_version "2")
src/praxisforge/
├── domain/
│   ├── folder.py                                  # + path (forma absoluta)
│   ├── folder_registry.py                         # unicidade de path; update(path=...)
│   └── errors.py                                  # + InvalidFolderPathError, PathAlreadyRegisteredError,
│                                                  #   RegistryMigrationRequiredError
├── application/
│   ├── ports.py                                   # + FolderLocator, LegacyPathSource; PathResolver removida
│   ├── dto.py                                     # RegisterFolderInput.path, UpdateFolderInput.path
│   ├── register_folder.py / update_folder.py      # canonizar + unicidade
│   ├── resolve_folder_path.py / scan_folders.py   # FolderLocator.check(folder)
│   ├── bootstrap_folders.py                       # alias <raiz>__<sub>, idempotência por path
│   └── migrate_registry.py                        # NOVO caso de uso
├── infrastructure/
│   ├── filesystem_folder_locator.py               # NOVO (canonize/check)
│   ├── env_legacy_path_source.py                  # NOVO (ex-EnvPathResolver, só migração)
│   ├── env_path_resolver.py                       # REMOVIDO
│   └── yaml_folder_registry.py                    # v2; v1 → RegistryMigrationRequiredError; load_raw p/ migração
└── presentation/cli.py                            # --path em add/update; folders migrate; path em list/show
docs/decisions/0006-caminho-absoluto-no-registro.md
```

**Structure Decision**: mesmas 4 camadas; troca de porta (PathResolver → FolderLocator) e um caso
de uso novo (migração).

## Complexity Tracking

Nenhuma violação.
