<!-- Criado em: 24/09/2026 10:41 -->
<!-- Modificado em: 24/09/2026 10:42 -->

# Data Model: Política de extração por licença

## ExtractPolicy (value object, enum ordenado)

| Valor | Ordem | Pode gravar no repositório |
|---|---|---|
| `link` | 0 | referência + metadados (origem, licença, descrição curta) |
| `summary` | 1 | síntese com palavras próprias + citações curtas com autor e origem |
| `verbatim` | 2 | cópia literal de trechos/arquivos, com aviso de copyright e licença preservados |

## ExtractScope (value object, enum)

`docs` | `code`. Ausente no registro ⇒ `code` (conservador, FR-010).

## Tabela de licenças (domínio, imutável)

`max_policy(license, scope) -> ExtractPolicy` e `is_classified(license) -> bool`; chave comparada
com `casefold` (FR-011). Valores em [research.md R2](./research.md).

## SourceRecord (entidade, evoluída)

| Campo | Tipo | Obrigatório | Regra |
|---|---|---|---|
| `schema_version` | `"2"` | sim | `"1"` ⇒ `SourceSchemaMigrationRequiredError` |
| `origin` | str | sim | não vazio, sem caminho absoluto (inalterado) |
| `author` | str | quando `extract_policy` ≥ `summary` | não vazio (FR-007) |
| `date` | date | sim | não futura (inalterado) |
| `license` | str | sim | SPDX ou `unknown` |
| `relevance` | str | sim | não vazio (inalterado) |
| `status` | `active` \| `pending` | sim | `unknown` ⇒ `pending` (inalterado) |
| `extract_policy` | ExtractPolicy | sim | ≤ `max_policy(license, extract_scope)` (FR-004/005); `pending` ⇒ `link` |
| `extract_scope` | ExtractScope | não | ausência = `code` |
| `notice_preserved` | bool | quando `verbatim` | deve ser `true` (FR-008) |
| `modified` | bool | quando `verbatim` e licença Apache-2.0 | declarado (FR-009) |

Removido: `extract_allowed`.

### Ordem de verificação (determinística)

1. forma (schema v2) → 2. status/licença (`unknown` ⇒ `pending`, `pending` ⇒ `link`) →
3. política ≤ máxima → 4. atribuição (`author`) → 5. `notice_preserved` → 6. `modified` (Apache).
A primeira violação de domínio encerra a validação do arquivo; o lote continua (FR-012).

## Exceções semânticas (novas)

| Exceção | Quando | Mensagem inclui |
|---|---|---|
| `ExtractPolicyExceedsLicenseError` | declarada > máxima | licença, escopo, declarada, máxima |
| `IncompleteAttributionError` | falta `author`/`notice_preserved`/`modified` exigido | campo faltante e política |
| `SourceSchemaMigrationRequiredError` | `schema_version: "1"` ou `extract_allowed` presente | "use `extract_policy` (source-schema-v2)" |

## Folder (existente, sem mudança de schema)

Exposição derivada: `max_policy(folder.license, code)` e `is_classified(folder.license)` em
`show`/`list`. Nada persistido no `folders.yaml`.
