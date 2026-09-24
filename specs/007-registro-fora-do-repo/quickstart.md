<!-- Criado em: 24/09/2026 11:44 -->
<!-- Modificado em: 24/09/2026 11:44 -->

# Quickstart: registro fora do repositório

Pré-requisitos: `make install-deps`; contrato em [contracts/cli-registry.md](./contracts/cli-registry.md).
Use um `XDG_CONFIG_HOME` descartável para não tocar o registro real.

1. **Local padrão**: `XDG_CONFIG_HOME=$(mktemp -d) uv run praxisforge folders list` → exit 1
   citando `<tmp>/praxisforge/folders.yaml`.
2. **Criação**: com o mesmo `XDG_CONFIG_HOME`, `folders add ...` → arquivo criado nesse local.
3. **Precedência**: `PRAXISFORGE_REGISTRY=<a>` + `--registry <b>` → usa `<b>`; só a variável → `<a>`.
4. **Dica de registro antigo**: com `src/data/folders.yaml` populado e local vazio → `folders list`
   mostra a dica de `relocate`.
5. **Relocate**: `folders relocate` → registro no local padrão, `diff` idêntico com a cópia de
   segurança, origem removida; repetir → recusa (destino existe).
6. **Repositório limpo**: `git status` não mostra `src/data/folders.yaml`; `make lint`,
   `make test`, `make validate-data` verdes com o registro pessoal populado no local padrão.

Migração real deste clone (uma vez): `cp src/data/folders.yaml <backup>` →
`uv run praxisforge folders relocate` → conferir com `folders list`.
