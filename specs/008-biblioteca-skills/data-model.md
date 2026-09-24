<!-- Criado em: 24/09/2026 15:12 -->
<!-- Modificado em: 24/09/2026 15:12 -->

# Data Model: Biblioteca de skills versionada

## SkillName (value object)

`^[a-z0-9]+(-[a-z0-9]+)*$`, 1–64 caracteres.

## Skill (entidade)

| Campo | Origem | Regra |
|---|---|---|
| `name` | frontmatter `name` | SkillName; igual ao nome da pasta |
| `description` | frontmatter | 1–1024 caracteres (após `strip`) |
| `version` | `metadata.version` | semver 2.0 obrigatório |
| `sources` | `metadata.sources` | lista de slugs (sem repetição); padrão `[]` |
| `authored` | `metadata.authored` | bool; padrão `false` |
| `license` | frontmatter `license` | opcional |
| `references` | links do corpo | caminhos relativos; todos dentro da pasta e existentes |

Regras de forma na entidade; `sources` vazio e `authored` falso → violação (FR-007).
Violações coletadas **todas de uma vez** (`InvalidSkillError(name, violations)`).

## Regra de proveniência (caso de uso)

Para cada slug: existe (único) → válido em `validate_sources` → política. Skill não autoral sem
fonte `summary`/`verbatim` → violação (FR-007a).

## PublicationRecord (marcador `.praxisforge-skill.json`, schema `skill-publication-v1`)

`schema_version: "1"`, `name`, `version`, `content_sha256` (64 hex), `source` (`skills/<nome>`).

## Estado do destino (por skill)

| Estado | Detecção | Ação da publicação |
|---|---|---|
| ausente | não existe | publica |
| nosso-cópia igual | marcador com mesmo hash | "inalterada" |
| nosso-cópia diferente, versão nova | hash ≠, version ≠ | atualiza |
| nosso-cópia diferente, mesma versão | hash ≠, version = | recusa (versão) |
| nosso-symlink | link → pasta da skill | modo symlink: "inalterada"; modo cópia: troca |
| terceiro | qualquer outro | recusa (terceiro) |
| órfã nossa | nossa e sem skill no repo | lista; remove com `--prune` |

## Exceções

`InvalidSkillError`, `SkillNotFoundError`, `ForeignSkillDestinationError`,
`SkillVersionNotBumpedError` (exit 1); `SkillPublicationError` (exit 3).
