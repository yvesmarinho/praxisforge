<!-- Criado em: 24/09/2026 11:44 -->
<!-- Modificado em: 24/09/2026 11:44 -->

# Implementation Plan: Registro de pastas fora do repositório

**Branch**: `007-registro-fora-do-repo` | **Date**: 24/09/2026 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-registro-fora-do-repo/spec.md`

## Summary

O padrão de `--registry` deixa de ser `src/data/folders.yaml` e passa a ser resolvido por uma
função de infraestrutura (`registry_location.resolve_registry_path`) com a precedência
`--registry` > `PRAXISFORGE_REGISTRY` > `$XDG_CONFIG_HOME/praxisforge/folders.yaml` >
`~/.config/praxisforge/folders.yaml`. `RegistryFileNotFoundError` passa a citar o local
resolvido; a CLI acrescenta a dica de migração quando existe um registro antigo não vazio em
`src/data/folders.yaml`. Novo comando `folders relocate [--from ARQ]` (caso de uso
`relocate_registry` + porta `RegistryFileMover`) valida e move o registro antigo sem
sobrescrever o destino. O repositório passa a versionar `src/data/folders.example.yaml`
(validado em `make validate-data`) e ignora `src/data/folders.yaml`. Testes isolam o ambiente
de configuração do usuário por fixture autouse.

## Technical Context

**Language/Version**: Python 3.12+ (mesmo ambiente das features 001–006)

**Primary Dependencies**: nenhuma nova (stdlib: `pathlib`, `os`, `shutil`)

**Storage**: registro YAML v2 fora do repo (local resolvido); `src/data/folders.example.yaml`
versionado; schema inalterado (`folders-schema-v2.json`)

**Testing**: pytest + pytest-cov; fixture autouse em `tests/conftest.py` apontando
`XDG_CONFIG_HOME` para `tmp_path` e removendo `PRAXISFORGE_REGISTRY` (nenhum teste toca o
`~/.config` real)

**Target Platform**: CLI Linux

**Project Type**: CLI (single project, 4 camadas)

**Performance Goals**: `relocate` de registro com 50+ pastas em < 1 s

**Constraints**: nenhum caminho fixo de máquina no código (FR-012); local derivado do ambiente;
`relocate` nunca sobrescreve destino; conteúdo movido byte a byte

**Scale/Scope**: um registro por usuário; registro local atual com 53 pastas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Camadas**: PASS. Resolução do local lê variáveis de ambiente → Infrastructure
  (`registry_location.py`), composta só na CLI; mover arquivo fica atrás da porta
  `RegistryFileMover` (adapter de filesystem); caso de uso `relocate_registry` na Application.
- **II. Contratos**: PASS. Schema inalterado; o exemplo versionado é validado no CI.
- **III. Test-First**: PASS (tasks/implement); filesystem com testes de permissão negada, destino
  existente, origem ausente/inválida.
- **IV. Erros semânticos**: PASS. `RegistryFileNotFoundError(location)` (existente, ganha o local);
  novas `RegistryAlreadyExistsError` e `RegistryRelocationError`.
- **V (v3.0.0)**: PASS — objetivo desta feature: registro fora do repo, exemplo sem caminho
  pessoal, precedência `--registry`/`PRAXISFORGE_REGISTRY`.
- **VI/VII**: N/A.

**Resultado**: sem violações.

## Project Structure

### Documentation (this feature)

```text
specs/007-registro-fora-do-repo/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/cli-registry.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
.gitignore                                         # + src/data/folders.yaml
src/data/folders.yaml                              # REMOVIDO do versionamento (git rm --cached)
src/data/folders.example.yaml                      # NOVO: exemplo v2 com caminhos /srv/praxisforge/...
src/praxisforge/
├── domain/errors.py                               # RegistryFileNotFoundError(location);
│                                                  #   + RegistryAlreadyExistsError, RegistryRelocationError
├── application/
│   ├── ports.py                                   # + RegistryFileMover
│   ├── errors.py                                  # reexporta as novas exceções
│   └── relocate_registry.py                       # NOVO caso de uso
├── infrastructure/
│   ├── registry_location.py                       # NOVO: resolve_registry_path, find_legacy_registry
│   ├── filesystem_registry_mover.py               # NOVO adapter de RegistryFileMover
│   └── yaml_folder_registry.py                    # erro de ausência com o local
└── presentation/cli.py                            # --registry sem default fixo; folders relocate;
                                                   #   dica de registro antigo
tests/conftest.py                                  # fixture autouse isolando XDG_CONFIG_HOME/PRAXISFORGE_REGISTRY
Makefile                                           # validate-data usa folders.example.yaml
docs/decisions/0008-registro-fora-do-repositorio.md
docs/reference/folders-yaml.md, docs/guides/operar-cli-praxisforge.md, README.md (append)
```

**Structure Decision**: mesmas 4 camadas; um módulo de infraestrutura (local), uma porta +
adapter (mover arquivo) e um caso de uso (relocate).

## Complexity Tracking

Nenhuma violação.
