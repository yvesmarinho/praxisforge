<!-- Criado em: 24/09/2026 15:12 -->
<!-- Modificado em: 24/09/2026 15:12 -->

# Quickstart: biblioteca de skills

Pré-requisitos: `make install-deps`; contratos em [contracts/](./contracts/). Use `HOME`
temporário para não tocar o `~/.claude` real.

1. **Criar**: `cp -r skills/_template skills/exemplo-skill`, ajustar `name`, `description`,
   `metadata.version` e `metadata.authored: true`.
2. **Validar**: `uv run praxisforge skills validate exemplo-skill` → exit 0; mudar `name` → exit 1
   citando a divergência; remover `authored` → exit 1 pedindo fontes.
3. **Catálogo**: `uv run praxisforge skills catalog` duas vezes → `git diff skills/README.md` vazio
   na segunda.
4. **Publicar**: `HOME=$(mktemp -d) uv run praxisforge skills publish exemplo-skill --target global`
   → `publicada`; repetir → `inalterada`; editar o SKILL.md sem mudar a versão → `recusada`.
5. **Terceiros**: criar `$HOME/.claude/skills/exemplo-skill/` à mão → publicação recusada, pasta
   intacta.
6. **Órfãs**: publicar, remover a skill do repo, `skills publish --all --target global` → lista órfã;
   `--prune` → removida.
7. **Atalho**: `scripts/publish-skills exemplo-skill --target global` → mesmo resultado.
8. **Gates**: `make lint && make test && make validate-data`.

Skills de exemplo criadas aqui são descartáveis — não versionar.
