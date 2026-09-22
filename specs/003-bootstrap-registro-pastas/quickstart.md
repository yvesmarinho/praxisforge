<!-- Criado em: 22/09/2026 16:59 -->
<!-- Modificado em: 22/09/2026 14:58 -->

# Quickstart: Bootstrap do Registro de Pastas

Guia de validação manual end-to-end da feature 003, após a implementação (`/speckit-implement`).

## Pré-requisitos

- Features 001 e 002 implementadas e mergeadas.
- Ambiente instalado: `make install-deps` (ou `uv sync`).

## Cenário 1 — Bootstrap inicial a partir de uma raiz de teste (US1)

```bash
mkdir -p /tmp/praxisforge-raiz/{repo-com-mit,repo-sem-license,solto.txt}
cat > /tmp/praxisforge-raiz/repo-com-mit/README.md << 'EOF'
# Repo com MIT

Este repositório contém exemplos de uso da API.
EOF
cat > /tmp/praxisforge-raiz/repo-com-mit/LICENSE << 'EOF'
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy...
EOF
mkdir -p /tmp/praxisforge-raiz/repo-sem-license
echo "# Repo sem license" > /tmp/praxisforge-raiz/repo-sem-license/README.md

REG=$(mktemp -d)/folders.yaml
uv run praxisforge --registry "$REG" folders bootstrap /tmp/praxisforge-raiz
uv run praxisforge --registry "$REG" folders list
```

**Esperado**: `repo-com-mit` registrado com `license: MIT`, `status: not_scanned`,
`description` extraída do README; `repo-sem-license` registrado com `license: unknown`,
`status: pending`; `solto.txt` (arquivo, não diretório) não aparece no registro. Ver spec.md
cenários 1-3.

## Cenário 2 — Idempotência (US2)

```bash
uv run praxisforge --registry "$REG" folders update repo-com-mit --status curated
uv run praxisforge --registry "$REG" folders bootstrap /tmp/praxisforge-raiz
uv run praxisforge --registry "$REG" folders show repo-com-mit
```

**Esperado**: `repo-com-mit` continua `status: curated` (a segunda execução do bootstrap não
reverteu para `not_scanned` nem tocou em nenhum campo). Ver spec.md cenário 5.

## Cenário 3 — Marcar e respeitar `status: ignore` (US3)

```bash
mkdir -p /tmp/praxisforge-raiz/pasta-tecnica
uv run praxisforge --registry "$REG" folders bootstrap /tmp/praxisforge-raiz
uv run praxisforge --registry "$REG" folders update pasta-tecnica --status ignore

export PRAXISFORGE_FOLDER_REPO_COM_MIT=/tmp/praxisforge-raiz/repo-com-mit
export PRAXISFORGE_FOLDER_REPO_SEM_LICENSE=/tmp/praxisforge-raiz/repo-sem-license
uv run praxisforge --registry "$REG" folders scan --all
```

**Esperado**: o resumo de `folders scan --all` mostra `pasta-tecnica` contada como "ignorada",
sem tentar resolver caminho para ela e sem exigir `PRAXISFORGE_FOLDER_PASTA_TECNICA`. Rodar o
bootstrap de novo → `pasta-tecnica` continua pulada (aparece em "ignoradas", não é
reprocessada). Ver spec.md cenário 6.

## Verificação de segurança (FR-014)

```bash
uv run praxisforge --registry "$REG" folders bootstrap /tmp/praxisforge-raiz | grep -F "/tmp/praxisforge-raiz"
```

**Esperado**: nenhuma linha da saída normal contém o caminho absoluto da raiz ou das subpastas.

## Limpeza

```bash
rm -rf /tmp/praxisforge-raiz
unset PRAXISFORGE_FOLDER_REPO_COM_MIT PRAXISFORGE_FOLDER_REPO_SEM_LICENSE
```

## Referências

- Contrato de CLI: [contracts/cli-bootstrap.md](./contracts/cli-bootstrap.md)
- Modelo de dados: [data-model.md](./data-model.md)
- Decisões técnicas: [research.md](./research.md)
- Estrutura de `folders.yaml`: [docs/reference/folders-yaml.md](../../docs/reference/folders-yaml.md)
