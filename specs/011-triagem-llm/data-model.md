<!-- Criado em: 28/09/2026 15:32 -->
<!-- Modificado em: 28/09/2026 15:34 -->

# Data Model: Triagem de curadoria com LLM

Entidades de domínio (puras, sem dependência externa) e documentos persistidos. Os documentos
ficam fora do repositório, em `<dir do registro>/curation/`.

## Domínio

### `TriageVerdict` (enum)

`covered` · `gap` · `out_of_scope`.

### `Triage` (value object, imutável)

| Campo | Tipo | Regra |
|---|---|---|
| `verdict` | `TriageVerdict` | obrigatório |
| `justification` | str | não vazia (strip) |
| `covered_by` | tuple[str, ...] | `covered` → ≥ 1 item, e todo item existe no acervo (`<tipo>/<nome>`); nos outros vereditos, vazio |
| `merge_target` | `MergeTarget \| None` | só com `gap`; alvo = item do acervo ou `draft_id` pendente existente |
| `suggested_kind` | `ArtifactKind \| None` | obrigatório se o artefato é `unknown` e o veredito é `gap`; nunca `unknown` |
| `ideas_summary` | str \| None | obrigatório e não vazio se `gap` e a licença da pasta é `link`/`unknown` (FR-016a) |
| `prompt_fingerprint` | str | SHA-256 hex (R4) |
| `model` | str | nome real do modelo |
| `cost_usd` | Decimal \| None | ≥ 0; None se não informado |
| `triaged_at` | datetime | com fuso `America/Sao_Paulo` |
| `draft_id` | str \| None | preenchido quando o rascunho é gravado |

Erros: `InvalidTriageError` (regra violada), levantado na construção.

### `MergeTarget`

`kind: "library" | "draft"`, `ref: str` (`<tipo>/<nome>` ou `draft_id`).

### `ArtifactState` (010, estendido)

Novo campo `triage: Triage | None` (padrão None). `verdict` continua sendo o veredito da
**revisão** (012). As regras da 010 se mantêm.

### Transições de etapa (011)

```text
pending ──triagem ok, covered/out_of_scope──▶ triaged
pending ──triagem ok, gap──▶ triaged ──rascunho gravado──▶ drafted
pending|triaged ──falha──▶ failed (attempts+1, last_error)
failed (attempts < 3 | --retry-failed) ──▶ elegível de novo
triaged|drafted|failed com prompt_fingerprint ≠ atual ──▶ elegível de novo
reviewed | promoted | discarded | removed ──▶ nunca elegível (011)
```

Um `gap` cujo rascunho falhou fica `failed`, com a `triage` já gravada. Na nova tentativa, a
triagem é refeita (simplicidade; o custo de uma triagem é baixo).

Função pura `is_eligible(state, fingerprint, retry_failed) -> bool` e `next_stage(...)` no
domínio (`curation_triage.py`).

### `DraftProposal` (value object)

| Campo | Tipo | Regra |
|---|---|---|
| `kind` | `ArtifactKind` | tipo do acervo (nunca `unknown`/`project_instruction`→ ver nota) |
| `name` | str | kebab-case, 3–64 caracteres (mesma regra de nome do acervo) |
| `description` | str | não vazia, ≤ 1.024 caracteres |
| `body` | str | Markdown não vazio |

Nota: `project_instruction` não é um tipo do acervo (ADR 0011). Um rascunho vindo de um
`CLAUDE.md`/`AGENTS.md` de terceiros declara `kind` entre os 6 tipos do acervo (normalmente
`rule` ou `reference`), conforme K2.

### `StructureSkeleton` e `SimilarityCheck`

- `Section = (level, list_items, table_rows, code_blocks, numbered_steps)`, com inteiros ≥ 0.
- `StructureSkeleton = tuple[Section, ...]`; `skeleton_of(markdown) -> StructureSkeleton` (puro).
- `structural_score(a, b) -> float` em [0, 1] (R7).
- `SimilarityCheck`: `structural_score`, `threshold`, `judge_is_derivative: bool`,
  `judge_justification: str`, `flagged = score ≥ threshold or judge_is_derivative`.

### `Draft` (entidade)

| Campo | Tipo | Regra |
|---|---|---|
| `draft_id` | str | 16 hex (R8) |
| `proposal` | `DraftProposal` | |
| `origins` | tuple[`DraftOrigin`, ...] | ≥ 1, sem repetição de `(alias, path)` |
| `checks` | tuple[`SimilarityCheck`, ...] | 1 ou 2 (original e regeneração); o último decide |
| `similarity_alert` | bool | = último check `flagged` |
| `merge_target` | `MergeTarget \| None` | cópia do veredito, quando for fusão |
| `prompt_fingerprint`, `model`, `cost_usd`, `updated_at` | | como em `Triage` |

`DraftOrigin = (alias, path, sha256)`. Adicionar uma origem com o mesmo `(alias, path)`
substitui a anterior (FR-025).

### `PromptSet`

`triage`, `draft`, `judge`, `criteria` (str, não vazios) e `fingerprint` (R4).
`PromptSetError` se algum faltar ou estiver vazio.

### `TriageBudget` (application)

`max_calls: int ≥ 1`, `max_cost_usd: Decimal | None`, `calls`, `cost`, `cost_measurable`;
`can_start_artifact(worst_case_calls=5) -> bool`; `record(cost)`. Não é persistido.

### `TriageRun` / relatório (application)

Por pasta: contagem por veredito, rascunhos gravados, com alerta, falhas (caminho + tipo),
chamadas, custo, restantes e motivo de parada (`done` | `budget` | `consecutive_failures` |
`interrupted`).

## Documentos persistidos

| Arquivo | Schema | Conteúdo |
|---|---|---|
| `curation/<alias>/state.json` | `curation-state-schema-v2.json` | estado da 010 + `triage` por artefato |
| `curation/_drafts/<draft_id>.json` | `curation-draft-schema-v1.json` | um rascunho |
| `curation/_drafts/.lock` | — | lock `flock` da área de rascunhos |

Respostas do modelo (validadas antes de virar domínio):

| Papel | Schema |
|---|---|
| triagem | `curation-triage-response-v1.json` |
| rascunho | `curation-draft-response-v1.json` |
| juiz | `curation-judge-response-v1.json` |

Os schemas completos estão em [contracts/](contracts/) e são copiados para `schemas/`.

## Portas novas (application/ports.py)

- `LanguageModel.complete(role: ModelRole, model: str, system_prompt: str, user_prompt: str,
  response_schema: str, timeout_s: int, max_budget_usd: Decimal | None) -> ModelReply`, onde
  `ModelReply = (payload: Mapping, cost_usd: Decimal | None, model: str)`.
- `PromptSource.load() -> PromptSet`.
- `LibraryCatalog.index_text() -> str`, `LibraryCatalog.items(kind) -> list[CatalogItem]`
  (nome, descrição, conteúdo); `exists(ref) -> bool`. Implementado sobre o
  `LibraryRepository` da 009.
- `ArtifactReader.read(folder: Path, artifact_path: str, is_directory: bool) -> str`
  (conteúdo concatenado até 256 KiB, ou `ArtifactTooLargeError`).
- `DraftStore.lock()`, `list_pending() -> list[Draft]`, `load(draft_id)`, `save(draft)`.
- `CurationStore` (010): `save_state(state)` para gravar só o estado, sem manifesto.
