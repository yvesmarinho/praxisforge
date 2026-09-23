<!-- Criado em: 23/09/2026 11:35 -->
<!-- Modificado em: 23/09/2026 11:35 -->

# Implementation Plan: Detecção de mudança de conteúdo pós-curadoria

**Branch**: `004-deteccao-mudanca-conteudo` | **Date**: 23/09/2026 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-deteccao-mudanca-conteudo/spec.md`

## Summary

Adicionar à entidade `Folder` um campo opcional `last_curated_commit` (hash do commit revisado na
última curadoria). `update_folder()` passa a gravá-lo quando o status muda para `curated` em
pasta git (resolvendo o caminho real pelo `PathResolver` existente). `scan_folder()`/
`scan_all_folders()` passam a verificar pastas `curated`: sem referência → grava o HEAD atual
(baseline, US3); com referência → pergunta a uma nova porta `GitContentInspector` se algum arquivo
**dentro da própria pasta** mudou entre o commit gravado e o HEAD; se sim, reverte para
`in_curation` (US2). O campo é mantido como histórico quando a pasta sai de `curated` (FR-010).
Integração com git via adapter de Infrastructure que chama o executável `git` (sem dependência nova).
Contrato evolui **aditivamente** em `folders-schema-v1.json` (propriedade opcional nova).

## Technical Context

**Language/Version**: Python 3.12+ (mesmo ambiente das features 001–003)

**Primary Dependencies**: nenhuma nova — o adapter usa `subprocess` da stdlib para chamar o
executável `git` (≥ 2.x, já pré-requisito do ambiente); ver research.md §R1

**Storage**: `src/data/folders.yaml`; `schemas/folders-schema-v1.json` ganha a propriedade
opcional `last_curated_commit` (mudança aditiva, ver research.md §R2)

**Testing**: pytest + pytest-cov; fake da porta `GitContentInspector` nos testes unitários;
testes de integração do adapter com repositórios git reais criados em `tmp_path`

**Target Platform**: CLI Linux (entry point `praxisforge`)

**Project Type**: CLI (single project, mesma estrutura de camadas)

**Performance Goals**: verificação de conteúdo acrescenta no máximo ~3 chamadas `git` por pasta
curada; lote de 100 pastas curadas em < 30 s em disco local

**Constraints**: nenhum caminho absoluto na saída (FR-013); falha do git numa pasta não reverte
status nem interrompe o lote (FR-009); timeout por chamada `git` (10 s) para não travar a varredura

**Scale/Scope**: dezenas a poucas centenas de pastas, mesma escala das features anteriores

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Arquitetura em Camadas**: PASS. Nova porta `GitContentInspector` em
  `application/ports.py`; adapter `infrastructure/git_cli_inspector.py`. Regra "reverter só se
  curada e mudou" fica em Application (`scan_folders.py`); invariante de formato do hash no
  Domain (`Folder`), só stdlib. Presentation só exibe o resultado e injeta o adapter.
- **II. Contratos Validados e Versionados**: PASS. Critério objetivo de mudança aditiva (definido
  na 003): (a) nenhum campo obrigatório novo — `last_curated_commit` é opcional; (b) nenhum campo
  existente muda; (c) todo documento válido na v1 continua válido. Permanece `folders-schema-v1.json`.
- **III. Test-First (NON-NEGOTIABLE)**: PASS (a cumprir em tasks/implement). Dependência externa
  nova (git) terá teste de indisponibilidade: executável ausente, timeout, repositório corrompido.
- **IV. Erros Semânticos nas Fronteiras**: PASS. Nova exceção `ContentInspectionError` (Domain
  errors, reexportada em `application/errors.py`); adapter converte `subprocess.TimeoutExpired`,
  `FileNotFoundError` e código de saída inesperado nela. Lote registra `ItemFailure` por item.
- **V. Proveniência e Licença**: PASS. Nenhum caminho absoluto no YAML (só hash) nem na saída.
- **VI/VII**: N/A para este plano de código.

**Resultado**: sem violações; Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/004-deteccao-mudanca-conteudo/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli-content-check.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
schemas/folders-schema-v1.json                  # + propriedade opcional last_curated_commit
src/praxisforge/
├── domain/
│   ├── folder.py                               # + campo last_curated_commit (validação de formato)
│   ├── folder_registry.py                      # update() aceita last_curated_commit
│   └── errors.py                               # + ContentInspectionError, InvalidCommitHashError
├── application/
│   ├── ports.py                                # + GitContentInspector
│   ├── errors.py                               # reexporta as novas exceções
│   ├── update_folder.py                        # grava hash ao marcar curated
│   └── scan_folders.py                         # verificação de conteúdo + ContentCheck no resultado
├── infrastructure/
│   ├── git_cli_inspector.py                    # NOVO adapter (subprocess git)
│   └── yaml_folder_registry.py                 # (de)serializa o campo novo
└── presentation/cli.py                         # injeta inspector; exibe resultado da verificação
tests/
├── unit/domain/ (folder, folder_registry)
├── unit/application/ (update_folder, scan_folders)
├── integration/ (git_cli_inspector com repos reais em tmp_path, cli)
└── contract/ (schema v1 com/sem campo, documentos antigos)
docs/decisions/0005-deteccao-mudanca-por-git-cli.md
docs/reference/folders-yaml.md                  # remove "Limitação conhecida", documenta o campo
```

**Structure Decision**: mesma estrutura em camadas; apenas 1 porta + 1 adapter novos.

## Complexity Tracking

Nenhuma violação da constituição a justificar.
