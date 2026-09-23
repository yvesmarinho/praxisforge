<!-- Criado em: 23/09/2026 11:35 -->
<!-- Modificado em: 23/09/2026 11:35 -->

# Data Model: Detecção de mudança de conteúdo pós-curadoria

## Folder (Domain — alterada)

| Campo | Tipo | Obrigatório | Regra |
|---|---|---|---|
| (campos existentes) | — | — | inalterados |
| `last_curated_commit` | `str \| None` | não (default `None`) | se presente: `^[0-9a-f]{40}([0-9a-f]{24})?$`; violação → `InvalidCommitHashError` (subclasse de `InvalidFolderError`) |

- Nenhuma invariante nova entre `status` e `last_curated_commit`: o campo pode existir em
  qualquer status (histórico, FR-010).
- `FolderRegistry.update(..., last_curated_commit: str | None = None)` — mesmo padrão dos demais
  campos (só aplica se informado).
- YAML: chave `last_curated_commit` omitida quando `None` (mantém o diff dos registros antigos
  vazio e determinístico).

## ContentCheck (Application — novo enum)

| Valor | Quando | Efeito no registro |
|---|---|---|
| `not_applicable` | status ≠ `curated` | nenhum |
| `not_git` | curada, pasta não é repositório (ou sem commits) | nenhum |
| `baseline_recorded` | curada, sem hash gravado | grava HEAD atual; status mantém `curated` |
| `unchanged` | curada, sem diff na pasta | nenhum |
| `reverted` | curada, diff na pasta ou commit gravado ausente | status → `in_curation`; hash mantido |

`ScanResult` ganha `content_check: ContentCheck`.

## Transições de estado (acréscimo às features 001–003)

```text
qualquer ──(update --status curated, pasta git)──▶ curated [hash := HEAD]
curated ──(scan, conteúdo da pasta mudou)──▶ in_curation [hash mantido]
curated ──(scan, sem hash)──▶ curated [hash := HEAD]
```

## Porta GitContentInspector (Application)

- `head_commit(path: Path) -> str | None` — `None` se não é repositório ou não tem commits.
- `changed_since(path: Path, commit: str) -> bool` — `True` se arquivos da pasta mudaram entre
  `commit` e HEAD, ou se `commit` não existe no repositório.
- Ambas levantam `ContentInspectionError` (git ausente, timeout, saída inesperada).

## Exceções novas (Domain `errors.py`)

- `ContentInspectionError(PraxisForgeError)` — falha ao inspecionar o conteúdo de uma pasta.
- `InvalidCommitHashError(InvalidFolderError)` — hash gravado fora do formato.
