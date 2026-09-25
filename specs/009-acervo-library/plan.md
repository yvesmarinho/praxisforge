<!-- Criado em: 25/09/2026 12:21 -->
<!-- Modificado em: 25/09/2026 12:23 -->

# Implementation Plan: Acervo `library/` por tipo de recurso

**Branch**: `009-acervo-library` | **Date**: 25/09/2026 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-acervo-library/spec.md`

## Summary

Generalizar a biblioteca de skills da 008 para um acervo `library/` com seis tipos de recurso
(skill, command, agent, hook, rule, reference). A entidade `Skill` vira `LibraryItem` com um
`KindSpec` por tipo; os casos de uso `validate_skills`, `build_catalog` e `publish_skills` viram
`validate_library`, `build_index` e `publish_items`. A CLI troca `skills` por `library`, a publicação
passa a aceitar só pastas de projeto (skills, commands, agents e rules), o registro de fonte passa a
v3 "só ideias" e a constituição sobe para v4.0.0. Decisões técnicas em [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12+ (uv)

**Primary Dependencies**: pyyaml, pydantic, jsonschema (existentes; nenhuma nova)

**Storage**: arquivos no repositório (`library/`, `src/data/sources/`, `schemas/`); marcadores de
publicação no projeto de destino

**Testing**: pytest (unit, integration, contract, architecture), cobertura ≥ 90%

**Target Platform**: Linux, CLI local

**Project Type**: CLI em camadas (Presentation → Application → Domain ← Infrastructure)

**Performance Goals**: validar 200 itens mistos em < 5 s (SC-004)

**Constraints**: índice determinístico; nenhuma escrita fora de `library/` e das pastas de projeto
indicadas; `library/` resolvido pela raiz do projeto (ADR 0010)

**Scale/Scope**: dezenas a poucas centenas de itens; 2 skills e 2 fontes a migrar

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Situação | Observação |
|-----------|----------|------------|
| I. Camadas | ✅ | `KindSpec` e `LibraryItem` no Domain (stdlib); portas `LibraryRepository`, `IndexWriter` e `ItemPublisher` na Application; adapters de filesystem na Infrastructure; CLI sem regra. Guarda por AST continua valendo |
| II. Contratos versionados | ✅ | um schema por tipo; `source-schema-v3` (breaking, novo arquivo); `library-publication-v1`; mudança aditiva em `skill-frontmatter-v1` |
| III. Test-first | ✅ | ordem contrato → exceções → testes de falha → implementação nas tasks; teste de indisponibilidade do filesystem (arquivo ilegível, falha de gravação do índice e da publicação) |
| IV. Erros semânticos | ✅ | `InvalidLibraryItemError`, `UnknownItemKindError`, `NotPublishableKindError`, `GlobalTargetRemovedError`, `IndexWriteError`; falha por item não derruba o lote |
| V. Proveniência e licença | ⚠️ emenda | "só ideias" muda a regra de extração → **emenda na constituição** (FR-026). A licença continua obrigatória |
| VI. Skills versionadas | ⚠️ emenda | vira "acervo `library/`" com seis tipos e sem alvo global → **emenda MAJOR** |
| VII. Memória no vault | ✅ | sem impacto |

As duas emendas **fazem parte desta feature** (primeira task, junto com os ADRs 0011 e 0012). Elas
não são violações a justificar, e sim a mudança de princípio que o debate aprovou. Por isso não
há Complexity Tracking.

**Re-check pós-design**: ✅. Nenhuma camada ou porta nova além das que substituem as da 008, e
nenhuma dependência nova.

## Project Structure

### Documentation (this feature)

```text
specs/009-acervo-library/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/cli-library.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
library/                                   # NOVO (substitui skills/)
├── INDEX.md
├── _templates/{skill/,command.md,agent.md,hook/,rule.md,reference.md}
├── skills/  commands/  agents/  hooks/  rules/  references/

schemas/
├── {command,agent,rule,hook,reference}-frontmatter-v1.json   # novos
├── library-publication-v1.json                                # novo
├── source-schema-v3.json                                      # novo
└── skill-frontmatter-v1.json                                  # aditivo

src/praxisforge/
├── domain/
│   ├── library_item.py        # ItemKind, KindSpec, ItemName, ItemMetadata, LibraryItem (sucede skill.py)
│   ├── source_record.py       # v3
│   └── errors.py              # novas exceções
├── application/
│   ├── ports.py               # LibraryRepository, IndexWriter, ItemPublisher (sucedem Skill*/Catalog*)
│   ├── validate_library.py    # sucede validate_skills.py
│   ├── build_index.py         # sucede build_catalog.py
│   ├── publish_items.py       # sucede publish_skills.py
│   └── validate_sources.py    # regra "≥ 1 fonte válida"
├── infrastructure/
│   ├── filesystem_library_repository.py   # sucede filesystem_skill_repository.py
│   ├── filesystem_index_writer.py         # sucede filesystem_catalog_writer.py
│   └── filesystem_item_publisher.py       # sucede filesystem_skill_publisher.py (+ leitura do marcador legado)
└── presentation/cli.py        # grupo library; skills → erro de uso

scripts/publish-library         # renomeado de publish-skills
src/data/sources/**             # 2 registros convertidos para v3 (edição única)

tests/
├── unit/domain/test_library_item.py
├── unit/application/test_{validate_library,build_index,publish_items}.py
├── integration/test_cli_library_{validate,index,publish}.py
├── integration/test_library_scale.py        # 200 itens < 5 s
└── contract/test_library_templates.py       # cópia de cada template valida
```

**Structure Decision**: mantém o projeto único em camadas. Os módulos da 008 são **substituídos**
(renomeados e generalizados), sem coexistir com os novos, e os testes da 008 migram junto. A
migração de `skills/` → `library/` usa `git mv` para preservar o histórico (FR-015).

## Ordem de entrega (orienta /speckit-tasks)

1. **Governança**: emenda da constituição v4.0.0 + ADRs 0011/0012.
2. **Contratos**: schemas novos e aditivos, com testes de contrato.
3. **Domain**: `LibraryItem`/`KindSpec` e `SourceRecord` v3. Testes de falha primeiro.
4. **Migração**: `git mv skills/ library/skills/` + templates; conversão manual das 2 fontes; marca
   `rewrite_pending` na `guarda-barra-qualidade`.
5. **US1** validate → **US3** index → **US4** publish (marcador novo + legado) → remoção de `skills ...`.
6. Escala (SC-004), docs (guia, INDEX, overview, README), `scripts/publish-library`, TODO (política
   máxima em `folders show`, ver R6).

## Complexity Tracking

Sem violações a justificar (ver Constitution Check).
