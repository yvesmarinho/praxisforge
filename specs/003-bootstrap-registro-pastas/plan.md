<!-- Criado em: 22/09/2026 16:50 -->
<!-- Modificado em: 22/09/2026 16:23 -->

# Implementation Plan: Bootstrap do Registro de Pastas

**Branch**: `003-bootstrap-registro-pastas` | **Date**: 22/09/2026 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-bootstrap-registro-pastas/spec.md`

## Summary

Adicionar um novo caso de uso `bootstrap_folders()` que recebe uma pasta-raiz (argumento
explícito, nunca configuração fixa), lista suas subpastas de primeiro nível através de uma nova
porta de Infrastructure (`RootFolderProbe`), tenta extrair `description` do README e `license` do
LICENSE de cada uma (heurística de texto, sem biblioteca externa), e registra só as subpastas
**ainda não existentes** no `FolderRegistry` — nunca sobrescreve uma pasta já registrada
(idempotência, US2). Um sexto valor de `CurationStatus`, `ignore`, é adicionado ao Domain e ao
contrato (mudança aditiva, mesmo arquivo `folders-schema-v1.json`) para o curador marcar
manualmente pastas a sempre pular; a varredura (feature 002) passa a pular pastas `ignore` em vez
de tentar resolvê-las.

## Technical Context

**Language/Version**: Python 3.12+ (mesmo ambiente das features 001/002)

**Primary Dependencies**: nenhuma nova — leitura de README/LICENSE e a heurística de licença usam
só `pathlib`/`re` da stdlib, mantendo a filosofia de dependências mínimas do projeto

**Storage**: mesmo `src/data/folders.yaml`; `schemas/folders-schema-v1.json` recebe uma mudança
**aditiva** no lugar (novo valor no enum `status`, invariante relaxada) — nenhum documento
previamente válido deixa de validar, então não exige `folders-schema-v2.json` (constituição II:
"mudança aditiva não exige novo arquivo")

**Testing**: pytest + pytest-cov, mesmo padrão de fakes de porta (ABC subclassing)

**Target Platform**: CLI Linux (mesmo entry point `praxisforge`)

**Project Type**: CLI (single project, mesma estrutura de camadas)

**Performance Goals**: bootstrap de 50 subpastas (40 com README/LICENSE reconhecíveis, 10 sem)
processadas com sucesso numa única execução (SC-003), mesma ordem de grandeza das features
001/002

**Constraints**: nenhuma saída do bootstrap MUST conter caminho absoluto fora de mensagem de erro
pontual sobre a própria subpasta (FR-014); bootstrap NÃO MUST sobrescrever pasta já registrada
(FR-004) nem marcar `ignore` sozinho (FR-012)

**Scale/Scope**: mesma escala das features 001/002 — dezenas a poucas centenas de subpastas por
execução

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Arquitetura em Camadas**: PASS. Novo caso de uso `application/bootstrap_folders.py`; nova
  porta `RootFolderProbe` em `application/ports.py` (list_subfolders/read_description/
  detect_license) — toda leitura de filesystem fora do fluxo já coberto por `PathResolver`
  (varredura de raiz arbitrária, README, LICENSE) fica atrás dessa porta; adapter concreto em
  `infrastructure/filesystem_folder_probe.py`. Presentation ganha só um subcomando fino
  (`folders bootstrap <root>`).
- **II. Contratos Validados e Versionados**: PASS, com atenção redobrada (já sinalizado na
  checklist). **Critério objetivo de "mudança aditiva"** usado nesta e em futuras avaliações do
  mesmo tipo: (a) nenhum campo obrigatório novo é introduzido; (b) nenhum campo existente muda de
  tipo, formato ou é removido; (c) todo documento que validava contra a versão anterior do schema
  continua validando contra a nova, sem exceção. A mudança no enum `status` (+`ignore`) e no
  `if/then` de licença `unknown` satisfaz as três condições: só amplia o conjunto de valores
  aceitos para `status`, sem tocar em nenhum outro campo. Não há remoção nem redefinição de campo
  existente → permanece `folders-schema-v1.json`, sem novo major.
- **III. Test-First (NON-NEGOTIABLE)**: PASS (a cumprir em `/speckit-tasks` +
  `/speckit-implement`).
- **IV. Erros Semânticos nas Fronteiras**: PASS. Reaproveita `InvalidAliasError` (formato de alias
  inválido após slugificação) e `AliasAlreadyRegisteredError` (colisão de alias **dentro da mesma
  execução**, entre duas subpastas novas que slugificam para o mesmo nome — o próprio
  `FolderRegistry.add()` já levanta isso na segunda tentativa); nenhuma exceção de domínio nova é
  necessária. Falha por item (FR-008) segue o mesmo padrão `ItemFailure` das features 001/002.
- **V. Proveniência e Licença das Fontes**: PASS. O bootstrap não cria nenhum arquivo em
  `src/data/sources/` — só popula `folders.yaml`; a proveniência de fontes individuais continua
  fora de escopo (mesma nota já registrada no guia de operação da CLI). Nenhum caminho absoluto é
  exposto fora de mensagem de erro pontual (FR-014).
- **VI/VII**: N/A para este plano de código.

Nenhuma violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-bootstrap-registro-pastas/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/praxisforge/
├── domain/
│   ├── curation_status.py     # +IGNORE = "ignore" (rótulo pt-BR "ignorada")
│   └── folder.py               # invariante relaxada: unknown ⇒ status in {PENDING, IGNORE}
├── application/
│   ├── ports.py                 # +RootFolderProbe (list_subfolders/read_description/detect_license)
│   ├── bootstrap_folders.py     # NOVO — bootstrap_folders(repository, probe, root) -> BootstrapReport
│   └── scan_folders.py          # scan_all_folders() passa a pular status=IGNORE (FR-013)
├── infrastructure/
│   └── filesystem_folder_probe.py  # NOVO — adapter concreto de RootFolderProbe
└── presentation/
    └── cli.py                   # +subcomando `folders bootstrap <root>`

schemas/
└── folders-schema-v1.json       # +"ignore" no enum status; if/then relaxado (mesma versão)

tests/
├── unit/domain/
│   ├── test_curation_status.py  # +caso IGNORE
│   └── test_folder.py           # +caso licença unknown com status IGNORE aceito
├── unit/application/
│   ├── test_bootstrap_folders.py  # NOVO
│   └── test_scan_folders.py       # +caso: pasta IGNORE pulada no lote
├── integration/
│   ├── test_cli_bootstrap.py    # NOVO
│   └── test_filesystem_folder_probe.py  # NOVO
└── contract/
    └── test_folders_schema.py   # +casos: status "ignore" válido; unknown+ignore válido
```

**Structure Decision**: mesma estrutura em camadas single-project das features anteriores. O
bootstrap é um novo caso de uso Application + uma nova porta/adapter de Infrastructure (a
primeira desde a feature 001 que não é `PathResolver`/`FolderRegistryRepository`/
`ContractValidator`) + um subcomando CLI fino. A mudança de Domain é mínima (um valor de enum + um
relaxamento de invariante já existente).

## Complexity Tracking

*Nenhuma violação de constituição — seção não aplicável.*
