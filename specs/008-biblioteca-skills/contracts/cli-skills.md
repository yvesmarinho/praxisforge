<!-- Criado em: 24/09/2026 15:12 -->
<!-- Modificado em: 24/09/2026 15:12 -->

# Contrato CLI — feature 008

| Comando | Comportamento |
|---|---|
| `skills validate <nome>` / `--all` | uma linha `<skill>: <motivo>` por violação; resumo `N ok, M com falha`; exit 0/1; nome inexistente → exit 1 |
| `skills catalog` | grava `skills/README.md`; `catálogo: N skills (M omitidas)`; omitidas listadas; exit 1 se houver omissão |
| `skills publish <nome>\|--all --target global\|<pasta> [--mode copy\|symlink] [--prune]` | por skill: `<skill> → publicada\|atualizada\|inalterada\|recusada (<motivo>)`; órfãs: `órfã: <skill>` (`removida` com `--prune`); resumo; exit 0 sem falhas, 1 com recusas, 3 falha de gravação |
| `--prune` sem `--all` | exit 2 (uso) |
| `scripts/publish-skills ARGS` | idêntico a `uv run praxisforge skills publish ARGS` |

Destino: `global` → `~/.claude/skills/`; `<pasta>` → `<pasta>/.claude/skills/` (pasta deve existir;
senão exit 2).
