<!-- Criado em: 22/09/2026 11:58 -->
<!-- Modificado em: 22/09/2026 11:49 -->

# Data Model: Varredura das Pastas Registradas

Nenhuma entidade de Domain nova é introduzida — a varredura só lê/atualiza o agregado
`FolderRegistry`/`Folder` já definido na feature 001 (`src/praxisforge/domain/folder.py`,
`folder_registry.py`). As "entidades" abaixo são estruturas de saída da Application (dataclasses
não persistidas), conforme a spec (seção Key Entities).

## Entidades reaproveitadas (feature 001, sem mudança)

- **`Folder`** (`domain/folder.py`): `alias`, `description`, `content_type`, `license`,
  `last_scanned: datetime | None`, `status: CurationStatus`. A varredura só toca `last_scanned` e,
  condicionalmente, `status` — via `FolderRegistry.update()`, que já garante as invariantes
  (`last_scanned` timezone-aware e não-futuro; `license == "unknown"` ⇒ `status == PENDING`).
- **`CurationStatus`** (`domain/curation_status.py`): `NOT_SCANNED → SCANNED` é a única transição
  que a varredura pode disparar (FR-002); os demais status (`IN_CURATION`, `CURATED`, `PENDING`)
  permanecem inalterados por ela.

## Entidades novas (Application, não persistidas)

### `ScanResult`

Resultado de uma varredura individual bem-sucedida.

| Campo | Tipo | Descrição |
|---|---|---|
| `alias` | `str` | alias varrido |
| `status` | `CurationStatus` | status após a varredura (igual ou avançado, FR-002) |
| `last_scanned` | `datetime` | timestamp da varredura, timezone-aware |

- **Origem**: devolvido por `scan_folder()`; nunca serializado sozinho — o efeito persistido é o
  `Folder` atualizado no registro (mesma fonte de verdade da feature 001).

### `ItemFailure` (reaproveitada de `application/resolve_folder_path.py`)

| Campo | Tipo | Descrição |
|---|---|---|
| `alias` | `str` | alias que falhou |
| `error_type` | `str` | nome da exceção semântica (`FolderNotFoundError`, `FolderPathInvalidError`, ...) |
| `message` | `str` | mensagem amigável, sem caminho absoluto (FR-010) |

- Nenhum campo novo necessário — o mesmo formato de falha por item da resolução de caminho serve
  para a varredura (FR-003, FR-004, FR-006).

### `ScanBatchReport`

Relatório de uma varredura em lote (`scan_all_folders()`).

| Campo | Tipo | Descrição |
|---|---|---|
| `ok` | `list[ScanResult]` | pastas atualizadas com sucesso |
| `failures` | `list[ItemFailure]` | falhas por item, sem interromper o lote (FR-006/FR-007) |
| `duplicates` | `list[DuplicateAliasGroup]` | grupos de aliases duplicados detectados nesta execução (FR-008) |

- **Lifecycle**: existe só durante a chamada; não é gravado em disco. Cada execução do lote gera
  um relatório novo do zero (Assumptions: duplicidade não é armazenada entre execuções).

### `DuplicateAliasGroup`

Grupo de dois ou mais aliases cujo caminho real resolvido é idêntico.

| Campo | Tipo | Descrição |
|---|---|---|
| `aliases` | `tuple[str, ...]` | aliases envolvidos, ordenados (≥ 2 elementos) |

- **Invariante**: `len(aliases) >= 2` — um grupo com um único alias não é duplicidade e não deve
  ser criado.
- **Nota de segurança (FR-010/SC-004)**: o caminho real resolvido (`Path`) é usado só
  internamente para agrupar; `DuplicateAliasGroup` **não** carrega o campo de caminho — só os
  aliases, para garantir que nenhuma saída da varredura exponha caminho absoluto do filesystem.

## Relações

```text
FolderRegistry (1) ──has many──> Folder (existente, feature 001)
scan_all_folders() ──produces──> ScanBatchReport
ScanBatchReport (1) ──has many──> ScanResult | ItemFailure | DuplicateAliasGroup
```

## Transições de estado (reaproveitadas, sem mudança de regra)

```text
NOT_SCANNED --[scan_folder, sucesso]--> SCANNED
SCANNED --[scan_folder, sucesso]--> SCANNED (só last_scanned muda)
IN_CURATION --[scan_folder, sucesso]--> IN_CURATION (só last_scanned muda)
CURATED --[scan_folder, sucesso]--> CURATED (só last_scanned muda)
PENDING --[scan_folder, sucesso]--> PENDING (só last_scanned muda — licença continua manual)
* --[scan_folder, falha de caminho]--> * (nenhuma mudança; registro intocado)
```
