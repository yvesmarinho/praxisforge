<!-- Criado em: 21/09/2026 15:59 -->
<!-- Modificado em: 21/09/2026 15:59 -->

# Implementation Plan: Registro de Pastas a Curar e Contratos Versionados

**Branch**: `001-registro-pastas-curadoria` | **Date**: 21/09/2026 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-registro-pastas-curadoria/spec.md`

## Summary

Entregar o registro versionado das pastas a curar (`src/data/folders.yaml`, primeiro alias
`github_forks`), a resolução do caminho real por variável de ambiente, os contratos JSON Schema
versionados de pasta e de fonte (`schemas/folders-schema-v1.json`, `schemas/source-schema-v1.json`)
e a estrutura em quatro camadas com regras de dependência verificadas por teste.

Abordagem: Domain em Python puro (dataclasses + enum, exceções semânticas, sem libs externas);
Application com casos de uso e portas (`FolderRegistryRepository`, `PathResolver`); Infrastructure
com adapters (repositório YAML com escrita atômica, resolvedor por ambiente, validador
`jsonschema`, log estruturado); Presentation com CLI `argparse` (`praxisforge folders …`,
`praxisforge sources validate`). Entrada validada em duas etapas na fronteira: JSON Schema
(todas as violações de uma vez) e construção das entidades de domínio (invariantes). Detalhes e
alternativas descartadas em [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12+ (`requires-python >=3.12`), gerenciado por `uv`

**Primary Dependencies**: `pyyaml` (registro), `jsonschema[format]` (validação por contrato, com `date-time` efetivo), `pydantic`
(DTOs de entrada da Application/CLI); CLI com `argparse` da stdlib (sem dependência nova)

**Storage**: arquivo YAML versionado em `src/data/folders.yaml`; fontes em
`src/data/sources/<categoria>/<slug>.md` (frontmatter YAML)

**Testing**: `pytest` + `pytest-cov` (mínimo 90%); testes por camada em `tests/unit`,
`tests/integration`, `tests/contract` e `tests/architecture`

**Target Platform**: Linux/macOS local (CLI de desenvolvedor); sem servidor

**Project Type**: biblioteca + CLI (projeto único)

**Performance Goals**: listar e validar 200 pastas em < 5 s (SC-003); lote de 100 pastas com 1
falha processa as 99 restantes (SC-004)

**Constraints**: nenhum caminho absoluto no repo, no YAML, em logs ou em mensagens de erro de
outras pastas (FR-004, FR-016); escrita idempotente e atômica (FR-015); Domain sem imports
externos e sem `logging` (constituição I)

**Scale/Scope**: dezenas a centenas de pastas; único curador; uma feature = registro + contratos
+ estrutura (varredura fica para a feature 002)

## Constitution Check

*GATE: aprovado antes da Fase 0; reavaliado após a Fase 1 (aprovado).*

| Princípio | Verificação neste plano | Resultado |
|-----------|-------------------------|-----------|
| I. Arquitetura em Camadas | 4 camadas; portas só para repositório e resolvedor de caminho (integrações reais: FS e ambiente); Domain sem libs externas nem logging; teste de arquitetura automatizado (FR-013) | ✅ |
| II. Contratos Validados e Versionados | JSON Schema `folders-schema-v1` e `source-schema-v1` com `schema_version`; `schema_version` obrigatório no YAML e no frontmatter; validação antes do Domain | ✅ |
| III. Test-First | Ordem nas tasks: contrato → exceções → testes de falha (vermelho) → implementação; teste de indisponibilidade para FS e ambiente (FR-017) | ✅ |
| IV. Erros Semânticos | Hierarquia `PraxisForgeError` com exceções nomeadas; `try/except` só em CLI, I/O e serialização; lote agrega falhas por item | ✅ |
| V. Proveniência e Licença | Contrato de fonte exige `license`; sem licença ⇒ `pending` e `extract_allowed=false`; sem caminho absoluto no YAML | ✅ |
| VI. Skills no Repositório | Não afetado (fora do escopo) | ✅ N/A |
| VII. Memória no Vault | Registro da sessão e da feature no vault ao concluir; sem segredos | ✅ |

Sem violações — **Complexity Tracking** não se aplica.

## Project Structure

### Documentation (this feature)

```text
specs/001-registro-pastas-curadoria/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/           # Fase 1 (schemas-rascunho e contrato da CLI)
│   ├── folders-schema-v1.json
│   ├── source-schema-v1.json
│   └── cli-contract.md
├── checklists/requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks — não criado aqui)
```

### Source Code (repository root)

```text
src/
├── praxisforge/
│   ├── __init__.py                     # __version__ (existente)
│   ├── domain/                         # Python puro: sem libs externas, sem logging
│   │   ├── errors.py                   # PraxisForgeError e derivadas
│   │   ├── alias.py                    # value object Alias
│   │   ├── curation_status.py          # enum CurationStatus
│   │   ├── folder.py                   # entidade Folder
│   │   ├── folder_registry.py          # agregado FolderRegistry (invariantes, aliases únicos)
│   │   └── source_record.py            # entidade SourceRecord (proveniência)
│   ├── application/
│   │   ├── ports.py                    # FolderRegistryRepository, PathResolver, ContractValidator
│   │   ├── dto.py                      # DTOs pydantic de entrada dos casos de uso
│   │   ├── register_folder.py          # registrar (idempotente)
│   │   ├── query_folders.py            # listar / consultar
│   │   ├── update_folder.py            # atualizar status e última varredura
│   │   ├── resolve_folder_path.py      # resolver alias → caminho real
│   │   └── validate_registry.py        # validar registro/fontes em lote (agrega falhas)
│   ├── infrastructure/
│   │   ├── yaml_folder_registry.py     # adapter do repositório (escrita atômica)
│   │   ├── env_path_resolver.py        # adapter: PRAXISFORGE_FOLDER_<ALIAS>
│   │   ├── jsonschema_validator.py     # adapter do ContractValidator (todas as violações)
│   │   ├── source_frontmatter.py       # leitura de frontmatter de fontes
│   │   └── logging_setup.py            # logs estruturados
│   └── presentation/
│       └── cli.py                      # argparse; converte exceções em mensagens amigáveis
└── data/
    └── folders.yaml                    # registro inicial (github_forks)

schemas/
├── folders-schema-v1.json
└── source-schema-v1.json

tests/
├── unit/                               # domain e application (com fakes das portas)
├── integration/                        # adapters reais em tmp_path (FS, ambiente)
├── contract/                           # schemas × exemplos válidos/inválidos
└── architecture/                       # regras de dependência entre camadas (AST)

docs/
├── architecture/overview.md            # camadas, fluxo, decisões (exigido pela constituição)
└── decisions/                          # ADRs desta feature (MADR simplificado)
```

**Structure Decision**: projeto único em `src/praxisforge/` com as quatro camadas como
subpacotes; dados versionados em `src/data/` e contratos em `schemas/` (raiz), conforme a
constituição (II) e o objetivo-init. Nenhuma abstração além das duas portas de integração real
e do validador de contrato.

## Complexity Tracking

Sem violações da constituição a justificar.
