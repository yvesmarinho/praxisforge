<!-- Criado em: 25/09/2026 14:35 -->
<!-- Modificado em: 25/09/2026 14:40 -->

# Data Model: Inventário de curadoria por pasta

Domain puro (dataclasses frozen, sem pydantic nem logging — ADR 0001). Validação de arquivo por
JSON Schema na Infrastructure.

## ArtifactKind (enum)

`skill`, `command`, `agent`, `hook`, `rule`, `reference`, `project_instruction`, `unknown`.

## Stage (enum)

`pending`, `triaged`, `drafted`, `reviewed`, `promoted`, `failed`, `discarded`, `removed`.

- Atribuídas na 010: `pending`, `removed`.
- `is_final(stage, verdict)`: `promoted`, `discarded`, `removed`, ou `reviewed` com
  `verdict == "accepted"`.

## ExclusionReason (enum)

`fixed_dir`, `gitignore`, `too_large`, `binary`, `symlink_outside`, `symlink_dir`, `unreadable`,
`uncurated` (texto fora das convenções que não é `.md` — FR-005).

## ConventionRule

| Campo | Tipo | Regra |
|---|---|---|
| kind | ArtifactKind | ≠ `unknown` |
| pattern | str | glob relativo, não vazio |
| unit | `file` \| `directory` | `directory`: pattern casa o diretório, que vira um artefato só |
| marker | str \| None | arquivo que precisa existir no diretório (ex.: `SKILL.md`) |

Origem: `<dir do registro>/curation-conventions.yaml` (fora do repo).

`Conventions(rules: tuple[ConventionRule, ...], version: str)` — `version` = SHA-256 canônico.
`classify_directory(rel_dir, names) -> kind | None` e `classify_file(rel) -> kind | None`: primeira
regra que casa vence. Diretórios são avaliados de cima para baixo; o mais externo que casar é dono
de toda a subárvore (U1/U2 da análise).

## Artifact

| Campo | Tipo | Regra |
|---|---|---|
| path | str | relativo POSIX, único no manifesto; diretório termina sem `/` |
| kind | ArtifactKind | |
| size | int | ≥ 0 (soma dos arquivos se diretório) |
| sha256 | str | 64 hex |
| files | int | ≥ 1 (arquivos cobertos) |

## ExcludedEntry

`path: str`, `reason: ExclusionReason`, `is_dir: bool`. Um diretório excluído não lista o
conteúdo (SC-002: o conteúdo é "parte" da exclusão).

## Manifest (`curation-manifest-schema-v1`)

`schema_version "1"`, `alias`, `conventions_version`, `artifacts[]` (ordenados por `path`),
`excluded[]` (ordenados por `path`). **Sem data** (FR-007/SC-003).

Invariante: todo arquivo regular da pasta está em exatamente um `artifact` ou sob um `excluded`.

## ArtifactState

| Campo | Tipo | Regra |
|---|---|---|
| path | str | chave |
| kind | ArtifactKind | |
| sha256 | str | último hash visto |
| stage | Stage | |
| verdict | str \| null | sempre null na 010 |
| last_error | str \| null | |
| attempts | int | ≥ 0 |

## CurationState (`curation-state-schema-v1`)

`schema_version "1"`, `alias`, `conventions_version`, `updated_at` (ISO 8601 -03:00),
`artifacts{path: ArtifactState}`. Só artefatos curáveis (esclarecimento Q1).

### Reconciliação (`reconcile(previous | None, manifest) -> CurationState`)

| Situação | Resultado |
|---|---|
| novo no manifesto | `pending`, attempts 0 |
| mesmo path, hash e kind iguais, mesma versão de convenções | mantém stage/verdict/attempts |
| hash ou kind diferente | `pending`, verdict null, last_error null (attempts mantido) |
| convenções mudaram e kind mudou | `pending` (FR-016) |
| ausente do manifesto | `removed` (fica no estado) |
| `removed` que reaparece | `pending` |

### Situação da pasta

`not_inventoried` (sem estado) · `complete` (todos finais, ≥ 0 artefatos) · `incomplete`.
Relatório: contagem por `Stage`, pendentes, falhas com `last_error`.

## Erros semânticos (domain/application)

`ConventionsError` (convenções inválidas), `ConventionsMissingError` (arquivo ausente), `CurationStateCorruptError`, `CurationLockedError`,
`FolderUnavailableError` (reuso se já existir equivalente em `folders scan`), `AliasNotFoundError`
(reuso).
