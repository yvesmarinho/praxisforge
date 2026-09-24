<!-- Criado em: 24/09/2026 15:12 -->
<!-- Modificado em: 24/09/2026 15:12 -->

# Implementation Plan: Biblioteca de skills versionada

**Branch**: `008-biblioteca-skills` | **Date**: 24/09/2026 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-biblioteca-skills/spec.md`

## Summary

Nova área `skills/` na raiz do repositório (template em `skills/_template/`). Domínio ganha a
entidade `Skill` (nome, descrição, versão semver, fontes, autoral, licença, arquivos referenciados)
com as regras de forma do `SKILL.md`; a regra de proveniência (fontes existentes e válidas, ao
menos uma `summary`/`verbatim` ou autoral) fica no caso de uso `validate_skills`, que reaproveita
`validate_sources` (feature 006). `build_catalog` gera `skills/README.md` determinístico.
`publish_skills` publica por cópia (padrão) ou symlink em `~/.claude/skills/` ou
`<projeto>/.claude/skills/`, reconhecendo o que o praxisforge publicou por um marcador
`.praxisforge-skill.json` (versão + hash do conteúdo) ou por symlink apontando para o repositório;
recusa mudança de conteúdo sem nova versão; lista órfãs e remove só com `--prune`.
`scripts/publish-skills` repassa para `praxisforge skills publish`.

## Technical Context

**Language/Version**: Python 3.12+ (mesmo ambiente das features 001–007)

**Primary Dependencies**: nenhuma nova (pyyaml, jsonschema, stdlib `hashlib`, `shutil`, `re`)

**Storage**: `skills/<nome>/SKILL.md` + apoio (repo); `skills/README.md` gerado;
`schemas/skill-frontmatter-v1.json` e `schemas/skill-publication-v1.json` (marcador) novos

**Testing**: pytest + pytest-cov; publicação sempre em `tmp_path` (nunca no `~/.claude` real —
fixture autouse redireciona `HOME`); escala com 50 skills (SC-005)

**Target Platform**: CLI Linux

**Project Type**: CLI (single project, 4 camadas)

**Performance Goals**: validar/catalogar/publicar 50 skills em < 5 s cada

**Constraints**: domínio só stdlib; publicação atômica por skill (temporário + rename); nunca tocar
destino de terceiros; catálogo sem data; nenhum caminho de máquina no código (global =
`Path.home()/.claude/skills`)

**Scale/Scope**: dezenas de skills; arquivos de apoio pequenos (Markdown/scripts)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Camadas**: PASS. Domain: `Skill`, `SkillName`, regras de forma e semver (stdlib). Application:
  casos de uso `validate_skills`, `build_catalog`, `publish_skills` sobre portas `SkillRepository`,
  `SkillPublisher`, `CatalogWriter` (e `SourceReader`/`ContractValidator` existentes).
  Infrastructure: adapters de filesystem. Presentation: subcomandos `skills`.
- **II. Contratos**: PASS. Frontmatter do `SKILL.md` validado por `skill-frontmatter-v1.json`;
  marcador de publicação (saída estruturada JSON) com `schema_version` e schema
  `skill-publication-v1.json`.
- **III. Test-First**: PASS (tasks/implement); filesystem com falhas de permissão, destino de
  terceiros, symlink quebrado.
- **IV. Erros semânticos**: PASS. `InvalidSkillError` (com lista de violações),
  `SkillNotFoundError`, `ForeignSkillDestinationError`, `SkillVersionNotBumpedError`,
  `SkillPublicationError`; lotes agregam falha por skill.
- **V. Proveniência/Licença**: PASS — fontes da skill validadas pela política de extração (006) e
  exigência de ao menos uma fonte `summary`/`verbatim` (FR-007a).
- **VI. Skills versionadas**: PASS — objetivo desta feature (`skills/`, validação antes de
  publicar, `scripts/publish-skills` idempotente, vault só com catálogo manual).
- **VII**: N/A.

**Resultado**: sem violações.

## Project Structure

### Documentation (this feature)

```text
specs/008-biblioteca-skills/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/cli-skills.md, contracts/skill-frontmatter-v1.json, contracts/skill-publication-v1.json
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
skills/
├── _template/SKILL.md                      # NOVO: modelo + instruções
└── README.md                               # GERADO por `skills catalog`
schemas/skill-frontmatter-v1.json, schemas/skill-publication-v1.json   # NOVOS
scripts/publish-skills                      # NOVO (bash, repassa para `skills publish`)
src/praxisforge/
├── domain/
│   ├── skill.py                            # NOVO: SkillName, Skill, regras de forma/semver/links
│   └── errors.py                           # + exceções de skill
├── application/
│   ├── ports.py                            # + SkillRepository, SkillPublisher, CatalogWriter
│   ├── validate_skills.py                  # NOVO (forma + proveniência, lote)
│   ├── build_catalog.py                    # NOVO (markdown determinístico)
│   └── publish_skills.py                   # NOVO (idempotência, versão, órfãs, prune)
├── infrastructure/
│   ├── filesystem_skill_repository.py      # NOVO (lê SKILL.md, frontmatter, links, hash)
│   ├── filesystem_skill_publisher.py       # NOVO (cópia atômica, symlink, marcador, remoção)
│   └── filesystem_catalog_writer.py        # NOVO (escrita atômica)
└── presentation/cli.py                     # + skills validate|catalog|publish
docs/decisions/0009-biblioteca-de-skills.md, docs/guides/criar-publicar-skills.md
```

**Structure Decision**: mesmas 4 camadas; três casos de uso novos sobre três portas novas.

## Complexity Tracking

Nenhuma violação.
