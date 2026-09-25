<!-- Criado em: 25/09/2026 12:21 -->
<!-- Modificado em: 25/09/2026 12:27 -->

# Data Model: Acervo `library/`

## ItemKind (enum, Domain)

`skill` · `command` · `agent` · `hook` · `rule` · `reference`

| Kind | Layout | Arquivo principal | Nome vem de | Publicável | Destino no projeto |
|------|--------|-------------------|-------------|------------|--------------------|
| skill | pasta | `SKILL.md` | frontmatter `name` = pasta | sim | `.claude/skills/<nome>/` |
| command | arquivo | `<nome>.md` | nome do arquivo | sim | `.claude/commands/<nome>.md` |
| agent | arquivo | `<nome>.md` | frontmatter `name` = arquivo | sim | `.claude/agents/<nome>.md` |
| rule | arquivo | `<nome>.md` | nome do arquivo | sim | `.claude/rules/<nome>.md` |
| hook | pasta | `HOOK.md` | frontmatter `name` = pasta | não | — |
| reference | arquivo | `<nome>.md` | frontmatter `name` = arquivo | não (vai dentro da skill que a cita) | — |

A tabela é regra de domínio: um `KindSpec` imutável por tipo.

## ItemName (value object)

`^[a-z0-9]+(-[a-z0-9]+)*$`, até 64 caracteres. Reaproveita a regra atual de `SkillName` (renomeada
para uso geral). A unicidade vale dentro do tipo; os tipos são diferenciados pela chave `(kind, name)`.

## ItemMetadata (value object)

| Campo | Tipo | Regra |
|-------|------|-------|
| `version` | semver | obrigatório |
| `sources` | lista de slugs únicos | opcional; vazia exige `authored: true` |
| `authored` | bool | padrão `false` |
| `rewrite_pending` | bool | padrão `false`; só informativo (FR-024a) |
| `references` | lista de nomes de reference | só em `skill` (R3); cada uma MUST existir |

## LibraryItem (entidade, Domain)

| Campo | Origem |
|-------|--------|
| `kind` | diretório de tipo |
| `name` | ver tabela de ItemKind |
| `description` | frontmatter; 1–1024 caracteres |
| `metadata` | ItemMetadata |
| `support_files` | alvos locais citados no corpo (só `skill` e `hook`); não saem da pasta |
| `hook_event`, `hook_matcher`, `hook_run` | só `hook`; `event` no enum de eventos; `run` não vazio e cada arquivo existe |
| `rule_paths` | só `rule`; lista de globs, opcional |

Construção por `LibraryItem.from_parts(kind, file_name, frontmatter, references, missing)`, que
coleta **todas** as violações e levanta `InvalidLibraryItemError(kind, name, violations)`.

Regras cruzadas (Application, `validate_library`):
- cada `source` existe uma única vez em `src/data/sources/**` e passa no `source-schema-v3`;
- item não autoral tem ≥ 1 fonte válida (FR-009);
- cada `metadata.references` existe como item `reference` válido.

## SourceRecord v3 (Domain, alterado)

Campos: `schema_version: "3"`, `origin`, `author` (opcional), `date`, `license`, `relevance` e
`status`. Saem `extract_policy`, `extract_scope`, `notice_preserved` e `modified`.
`schema_version` `"1"` ou `"2"` → `SourceSchemaMigrationRequiredError` com instrução de conversão.

## LibraryIndex (visão gerada)

Uma linha por item válido, agrupado por tipo na ordem da tabela e ordenado por nome dentro do tipo.
Colunas: nome, descrição, versão, fontes, caminho e `⚠ reescrita pendente` quando for o caso. Não
leva data. Itens inválidos → lista `omitted` com motivos (FR-013).

## PublicationMarker v1 (`library-publication-v1`)

| Campo | Regra |
|-------|-------|
| `schema_version` | `"1"` |
| `kind` | skill, command, agent ou rule |
| `name` | ItemName |
| `version` | semver do item |
| `content_sha256` | hash de caminho + bytes (mesma regra da 008) |
| `source` | `library/<kind>s/<nome>` |

Local: `<skill>/.praxisforge-skill.json` para skill; `.<nome>.md.praxisforge.json` ao lado do
arquivo para command, agent e rule. Marcador legado `skill-publication-v1` é lido como nosso
(FR-017).

## Estados de publicação (por item e destino)

`ausente` → publicar · `nosso, igual` → nada · `nosso, igual, marcador antigo` → só regrava o
marcador · `nosso, symlink quebrado para skills/` → recria o link · `nosso, versão/conteúdo diferente` → atualizar
(conteúdo diferente com a mesma versão → recusa, regra da 008) · `terceiro` → recusa sem tocar ·
`órfão` (nosso, mas saiu do acervo) → só removido com `--prune`.
