<!-- Criado em: 25/09/2026 14:59 -->
<!-- Modificado em: 25/09/2026 14:59 -->

# Guia: inventariar a curadoria de uma pasta

O inventário lista tudo o que existe numa pasta registrada, classifica por convenção de caminho e
registra o que ficou de fora e por quê. Nada é escrito na pasta nem no repositório.

## 1. Convenções (uma vez por máquina)

```bash
cp src/data/curation-conventions.example.yaml ~/.config/praxisforge/curation-conventions.yaml
```

O arquivo fica ao lado do `folders.yaml` (se usar `--registry` ou `PRAXISFORGE_REGISTRY`, copie
para o mesmo diretório). Para reconhecer uma estrutura nova, acrescente uma regra:

```yaml
- {kind: agent, pattern: "**/prompts/*.md", unit: file}
- {kind: skill, pattern: "**/playbooks/*", unit: directory, marker: PLAYBOOK.md}
```

Mudar as regras muda a versão das convenções: artefatos reclassificados voltam para pendente.

## 2. Inventariar

```bash
uv run praxisforge curation inventory github_forks__agent_skills
uv run praxisforge curation inventory --all
```

Resultado em `~/.config/praxisforge/curation/<alias>/manifest.json` e `state.json`.

| Tipo | Convenção (exemplo) |
|---|---|
| skill | diretório `**/skills/*` com `SKILL.md` (apoio incluído) |
| hook | diretório `**/hooks` |
| command / agent / rule / reference | `commands/**/*.md`, `agents/*.md`, `rules/*.md`, `references/*.md` |
| project_instruction | `CLAUDE.md`, `AGENTS.md` em qualquer nível |
| unknown | qualquer outro `.md` (README, docs) |

Excluídos com motivo: `fixed_dir` (`.git`, `node_modules`…), `gitignore`, `too_large` (> 256 KiB),
`binary`, `symlink_outside`, `symlink_dir`, `unreadable`, `uncurated` (código/configuração).

## 3. Acompanhar

```bash
uv run praxisforge curation status            # todas as pastas
uv run praxisforge curation status <alias>    # com as falhas
uv run praxisforge curation status --json
```

Situações: **completa** (todo artefato em etapa final), **incompleta**, **sem inventário** (inclui
pastas `curated` da curadoria manual antiga, a refazer).

## 4. Reinventariar

Rode `inventory` de novo após o fork mudar: só artefatos novos ou alterados voltam a `pending`;
os sumidos viram `removed`; o resto mantém a etapa.

## Códigos de saída

0 ok · 1 alias inexistente, convenções inválidas, estado corrompido, falha no lote · 2 uso ·
3 ambiente (convenções ausentes, pasta inacessível, outra execução em andamento).

Decisões: [ADR 0013](../decisions/0013-inventario-de-curadoria.md).
