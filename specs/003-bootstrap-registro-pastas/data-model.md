<!-- Criado em: 22/09/2026 16:55 -->
<!-- Modificado em: 22/09/2026 14:57 -->

# Data Model: Bootstrap do Registro de Pastas

## Entidades existentes alteradas

### `CurationStatus` (domain/curation_status.py) — +1 valor

| Valor | Rótulo pt-BR | Observação |
|---|---|---|
| `IGNORE` = `"ignore"` | "ignorada" | **Novo**. Só aplicado manualmente via `folders update --status ignore` (FR-012); nunca pelo bootstrap. |

Os 5 valores existentes (`not_scanned`, `scanned`, `in_curation`, `curated`, `pending`) não mudam.

### `Folder` (domain/folder.py) — invariante relaxada

Invariante atual: `license == "unknown"` ⇒ `status == PENDING`.
Invariante nova: `license == "unknown"` ⇒ `status in {PENDING, IGNORE}`.

Nenhum campo novo na entidade. `UnknownLicenseRequiresPendingError` continua sendo levantado
quando `license == "unknown"` e `status` não é nem `PENDING` nem `IGNORE`.

### `schemas/folders-schema-v1.json` — mudança aditiva no lugar

```diff
  "status": {
-   "enum": ["not_scanned", "scanned", "in_curation", "curated", "pending"]
+   "enum": ["not_scanned", "scanned", "in_curation", "curated", "pending", "ignore"]
  }
```

```diff
  {
    "if": { "properties": { "license": { "const": "unknown" } }, "required": ["license"] },
-   "then": { "properties": { "status": { "const": "pending" } } }
+   "then": { "properties": { "status": { "enum": ["pending", "ignore"] } } }
  }
```

Todo documento válido hoje continua válido (nenhum campo removido, nenhum valor existente deixa
de ser aceito) — mudança puramente aditiva, permanece `schema_version: "1"`.

### `ScanBatchReport` (application/scan_folders.py, feature 002) — +1 campo

| Campo | Tipo | Observação |
|---|---|---|
| `ignored` | `list[str]` (default `[]`) | **Novo**. Aliases com `status == IGNORE` pulados na varredura em lote (FR-013); não entram em `ok` nem `failures`. |

## Entidades novas (Application, não persistidas)

### `BootstrapReport`

Resultado de uma execução do bootstrap sobre uma pasta-raiz.

| Campo | Tipo | Descrição |
|---|---|---|
| `root` | `Path` | pasta-raiz de origem (uso interno do relatório; **nunca serializado/impresso** — FR-014) |
| `registered` | `list[str]` | aliases de subpastas novas registradas com sucesso nesta execução |
| `skipped_existing` | `list[str]` | aliases já existentes antes desta execução (não-`ignore`), intocados |
| `skipped_ignored` | `list[str]` | aliases já existentes com `status == IGNORE`, pulados |
| `failures` | `list[ItemFailure]` | falhas por subpasta (alias inválido após slugificação, ou colisão de alias dentro da mesma execução) — reaproveita `ItemFailure` de `application/resolve_folder_path.py` |

- **Lifecycle**: existe só durante a chamada; não é persistido. `folders.yaml` é a única fonte de
  verdade duradoura do resultado (as novas entradas em `registered`).

## Portas novas (Application)

### `RootFolderProbe` (application/ports.py)

| Método | Assinatura | Descrição |
|---|---|---|
| `list_subfolders` | `(root: Path) -> list[Path]` | subpastas de primeiro nível dentro de `root` (só diretórios, segue link simbólico, ignora links quebrados) |
| `read_description` | `(path: Path) -> str \| None` | primeiro parágrafo útil do README de `path`, ou `None` se não houver README |
| `detect_license` | `(path: Path) -> str \| None` | identificador de licença reconhecido no LICENSE de `path` (MIT/Apache-2.0/GPL-3.0/BSD-3-Clause), ou `None` |

Implementação concreta: `infrastructure/filesystem_folder_probe.py`
(`FilesystemFolderProbe`).

## Relações

```text
bootstrap_folders(root) ──produces──> BootstrapReport
BootstrapReport (1) ──has many──> registered (str) | skipped_existing (str) |
                                   skipped_ignored (str) | failures (ItemFailure)
RootFolderProbe ──used by──> bootstrap_folders()
FolderRegistry.add() ──called only for──> subpastas novas (não em existing_at_start)
```

## Transições de estado (`status`, incluindo o novo valor)

```text
NOT_SCANNED --[scan_folder, sucesso]--> SCANNED                    (feature 002, inalterado)
* --[folders update --status ignore]--> IGNORE                     (NOVO, sempre manual)
IGNORE --[folders scan --all]--> IGNORE (pulada, não processada)   (NOVO, FR-013)
IGNORE --[folders update --status <outro>]--> <outro>               (reversível manualmente)
(bootstrap) --[subpasta nova, license reconhecida]--> NOT_SCANNED
(bootstrap) --[subpasta nova, license não reconhecida]--> PENDING
(bootstrap) --[subpasta já registrada, qualquer status]--> inalterada (pulada)
```
