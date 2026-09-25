<!-- Criado em: 25/09/2026 14:35 -->
<!-- Modificado em: 25/09/2026 14:40 -->

# Quickstart: validar o inventário de curadoria

Pré-requisitos: `uv sync`; registro de pastas válido (`uv run praxisforge folders validate`).

## 1. Suíte

```bash
uv run pytest tests -k curation --cov=praxisforge --cov-fail-under=90
```

## 2. Registro isolado (sem tocar no seu `~/.config`)

```bash
export PRAXISFORGE_REGISTRY="$(mktemp -d)/folders.yaml"
uv run praxisforge folders add --alias demo --description "demo" --content-type skills \
  --license MIT --path "$(mktemp -d)"
```

Copie as convenções para junto do registro isolado:

```bash
cp src/data/curation-conventions.example.yaml "$(dirname "$PRAXISFORGE_REGISTRY")/curation-conventions.yaml"
```

Popule a pasta com `skills/x/SKILL.md`, `.claude/commands/c.md`, `CLAUDE.md`, `README.md`,
`app.py`, `node_modules/a.js` e um binário.

## 3. Cenários

| Passo | Comando | Esperado |
|---|---|---|
| Inventário (US1) | `praxisforge curation inventory demo` | exit 0; manifesto com skill, command, project_instruction, unknown (README); excluídos: `app.py` uncurated, `node_modules` fixed_dir, binário |
| Determinismo (SC-003) | rodar de novo e `cmp` do manifest.json | idêntico |
| Status (US2) | `praxisforge curation status demo` | `incompleta`, 4 pendentes |
| Incremental (US3) | editar `SKILL.md`, apagar `README.md`, rodar inventory | skill `pending`, README `removed`, demais inalterados |
| Lote (US4) | registrar pasta inexistente; `curation inventory --all` | demo ok, outra FALHA; exit 1 |
| Sem convenções (FR-004) | apagar `curation-conventions.yaml` e rodar inventory | exit 3 com instrução de cópia |
| Lock (FR-014) | duas execuções simultâneas | a segunda: exit 3 |
| Somente leitura (SC-006) | `git status` no repo e `find <pasta> -newer` | nada alterado |

Artefatos em `$(dirname $PRAXISFORGE_REGISTRY)/curation/demo/`. Contratos em
[contracts/](contracts/), modelo em [data-model.md](data-model.md).
