<!-- Criado em: 23/09/2026 13:03 -->
<!-- Modificado em: 23/09/2026 15:30 -->

# Data Model: Caminho absoluto no registro de pastas

## Folder (alterada)

| Campo | Tipo | Obrigatório | Regra |
|---|---|---|---|
| `path` | `str` | **sim** | absoluto ("/..."), sem "..", sem "~", sem "/" final; violação → `InvalidFolderPathError` (subclasse de `InvalidFolderError`) |
| demais | — | — | inalterados (features 001–004) |

## FolderRegistry (alterado)

- Invariante nova: `path` único **e sem aninhamento** (nenhum path é prefixo de diretório de outro),
  comparando com `casefold()` → `PathAlreadyRegisteredError(owner)` (duplicado) ou
  `NestedFolderPathError(owner)` (aninhado).
- `add` idêntico continua no-op; mesmo alias com path diferente → `AliasAlreadyRegisteredError`.
- `update(..., path: str | None = None)` — atômico, revalida unicidade (ignora a própria pasta).
- `find_by_path(path) -> Folder | None` (bootstrap/migração).

## Contrato

- `folders-schema-v2.json`: `schema_version: "2"`; `path` em `required`.
- `folders-schema-v1.json`: somente leitura pela migração.

## MigrationReport (Application)

| Campo | Tipo |
|---|---|
| `migrated` | `list[str]` (alias) |
| `pending` | `list[ItemFailure]` (alias + motivo) |
| `written` | `bool` (True só se `pending` vazio e houve conversão) |
| `already_current` | `bool` (registro já em v2) |
| `removed_roots` | `list[str]` (aliases removidos por serem ancestrais de outras entradas — FR-017) |

## Exceções novas (Domain)

- `InvalidFolderPathError(InvalidFolderError)`
- `PathAlreadyRegisteredError(PraxisForgeError)` — atributo `owner` (alias que ocupa o caminho)
- `NestedFolderPathError(PraxisForgeError)` — atributo `owner`
- `RegistryMigrationRequiredError(RegistryUnavailableError)` — registro em v1
