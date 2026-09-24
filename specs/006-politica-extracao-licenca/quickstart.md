<!-- Criado em: 24/09/2026 10:41 -->
<!-- Modificado em: 24/09/2026 10:42 -->

# Quickstart: validar a política de extração

Pré-requisito: `make install-deps`; contrato em [contracts/](./contracts/), campos em
[data-model.md](./data-model.md).

## 1. Fonte válida (MIT, verbatim)

Criar `src/data/sources/exemplo/mit-ok.md` com frontmatter `schema_version: "2"`, `license: MIT`,
`extract_policy: verbatim`, `author`, `notice_preserved: true` e demais campos obrigatórios.

```bash
uv run praxisforge sources validate src/data/sources/exemplo/
```

Esperado: `1 ok, 0 com falha`, exit 0.

## 2. Política acima da máxima

Mesma fonte com `license: Elastic-2.0` → falha citando máxima `summary`, exit 1.

## 3. Licença desconhecida

`license: unknown`, `status: pending`, `extract_policy: summary` → falha (pending exige `link`).

## 4. GPL por escopo

`license: GPL-3.0`, `extract_policy: verbatim`: com `extract_scope: docs` passa; sem escopo falha
(máxima `summary` para código).

## 5. Registro antigo

Frontmatter com `schema_version: "1"`/`extract_allowed` → falha pedindo `extract_policy`.

## 6. Política máxima das pastas

```bash
uv run praxisforge folders show <alias>   # linha "política máxima: ..."
uv run praxisforge folders list           # coluna após o status
```

## 7. Gates

```bash
make lint && make test && make validate-data
```

Os exemplos de `exemplo/` são descartáveis — não versionar.
