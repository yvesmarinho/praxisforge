<!-- Criado em: 21/09/2026 15:59 -->
<!-- Modificado em: 21/09/2026 16:09 -->

# Data Model — 001-registro-pastas-curadoria

Camada de origem: Domain (Python puro). Documento persistido: `src/data/folders.yaml`.

## Value Object: Alias

| Regra | Detalhe |
|-------|---------|
| Formato | `^[a-z][a-z0-9_]{1,62}$` |
| Imutável | `frozen dataclass` |
| Erro | `InvalidAliasError` |
| Derivado | `env_var_name` = `PRAXISFORGE_FOLDER_` + alias em maiúsculas |

## Enum: CurationStatus

`not_scanned` → `scanned` → `in_curation` → `curated`; `pending` pode ser atribuído em qualquer
momento (licença desconhecida ou revisão bloqueada). Transições livres, exceto: licença
`unknown` ⇒ o status só pode ser `pending`. Para sair de `pending`, a licença precisa ser
atualizada antes ou na mesma operação (ver `update` em FolderRegistry).

| Valor | Rótulo pt-BR |
|-------|--------------|
| `not_scanned` | não varrida |
| `scanned` | varrida |
| `in_curation` | em curadoria |
| `curated` | curada |
| `pending` | pendente |

## Entidade: Folder

| Campo | Tipo | Obrigatório | Regras |
|-------|------|-------------|--------|
| `alias` | Alias | sim | único no registro; imutável após criação |
| `description` | str | sim | não vazia, ≤ 500 caracteres |
| `content_type` | str | sim | slug `^[a-z][a-z0-9_-]{1,62}$` |
| `license` | str | sim | SPDX ou `unknown`; `unknown` ⇒ status `pending` |
| `last_scanned` | datetime \| None | não | ISO 8601 com offset; não futuro; `None` até a 1ª varredura |
| `status` | CurationStatus | sim | ver acima; `not_scanned` exige `last_scanned = None` |

Sem campo de caminho (FR-004). Erros de invariante: `InvalidFolderError` (subtipos
`UnknownLicenseRequiresPendingError`, `FutureScanDateError`).

## Agregado: FolderRegistry

| Campo | Tipo | Regras |
|-------|------|--------|
| `schema_version` | str | obrigatório; versão principal suportada (`"1"`); mais nova ⇒ `UnsupportedSchemaVersionError` |
| `folders` | mapa alias → Folder | aliases únicos; ordenado por alias na persistência |

Operações: `add(folder)` (idempotente se idêntico; senão `AliasAlreadyRegisteredError`),
`get(alias)` (`FolderNotFoundError`), `update(alias, status?, last_scanned?, license?)`, `list()`. A `license` entra em `update`
(extensão do FR-002, que só cita status e última varredura) para que uma pasta com licença
`unknown` — como `github_forks` — não fique presa em `pending`; as invariantes de `Folder` são
reavaliadas após aplicar a mudança inteira (atômica: tudo ou nada).
Aliases que diferem só por caixa não existem (alias só minúsculo → `InvalidAliasError`).

## Entidade: SourceRecord (proveniência)

| Campo | Tipo | Obrigatório | Regras |
|-------|------|-------------|--------|
| `schema_version` | str | sim | `"1"` |
| `origin` | str | sim | não vazia (URL ou descrição da origem; sem caminho absoluto) |
| `date` | date | sim | não futura |
| `license` | str | sim | SPDX ou `unknown` |
| `relevance` | str | sim | não vazia |
| `status` | `active` \| `pending` | sim | `unknown` ⇒ `pending` |
| `extract_allowed` | bool | sim | `false` obrigatório quando `pending` |

## Resolução de caminho (não persistida)

`Alias` → `PathResolver` → `Path` real. Fonte: variável de ambiente. Falhas:
`FolderPathNotConfiguredError` (variável ausente/vazia), `FolderPathInvalidError` (relativo,
`..`, inexistente, não é diretório), `FolderPathUnreadableError` (sem permissão).

## Hierarquia de exceções (Domain/Application)

```text
PraxisForgeError
├── ContractValidationError        # violações do schema (lista de Violation: campo + motivo)
│   └── UnsupportedSchemaVersionError
├── InvalidAliasError
├── InvalidFolderError
│   ├── UnknownLicenseRequiresPendingError
│   └── FutureScanDateError
├── AliasAlreadyRegisteredError
├── FolderNotFoundError
├── RegistryUnavailableError       # arquivo ilegível/corrompido (Infrastructure)
│   └── RegistryFileNotFoundError  # arquivo ausente (só `add` cria o arquivo)
├── FolderPathNotConfiguredError
├── FolderPathInvalidError
└── FolderPathUnreadableError
```

`Violation` = (`field: str`, `reason: str`). Mensagens e logs identificam alias e motivo,
nunca caminho absoluto.

## Documento persistido — `src/data/folders.yaml`

```yaml
schema_version: "1"
folders:
  github_forks:
    description: Forks de repositórios de referência sobre engenharia de agentes
    content_type: repository_forks
    license: unknown
    last_scanned: null
    status: pending
```

Registro inicial coerente com D8: `github_forks` nasce com licença `unknown` ⇒ `pending`
(a licença real é validada **por fonte**, conforme a constituição V).
