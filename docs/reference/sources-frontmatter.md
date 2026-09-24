<!-- Criado em: 24/09/2026 10:58 -->
<!-- Modificado em: 24/09/2026 10:58 -->

# Referência — frontmatter de fontes (`source-schema-v2`)

Cada fonte curada é um arquivo `src/data/sources/<categoria>/<slug>.md`: frontmatter YAML com a
proveniência e a política; corpo com notas e extratos. Contrato: `schemas/source-schema-v2.json`.
Decisão: [ADR 0007](../decisions/0007-politica-de-extracao-por-licenca.md).

## Campos

| Campo | Obrigatório | Valores / regra |
|---|---|---|
| `schema_version` | sim | `"2"` |
| `origin` | sim | URL ou descrição; nunca caminho absoluto |
| `author` | em `summary`/`verbatim` | não vazio |
| `date` | sim | `AAAA-MM-DD`, não futura |
| `license` | sim | SPDX (`MIT`, `Apache-2.0`…) ou `unknown` |
| `relevance` | sim | por que a fonte importa |
| `status` | sim | `active` \| `pending`; `unknown` exige `pending` |
| `extract_policy` | sim | `link` \| `summary` \| `verbatim`; ≤ máxima da licença; `pending` exige `link` |
| `extract_scope` | não | `docs` \| `code` (ausente = `code`); só muda o resultado para GPL-3.0 |
| `notice_preserved` | em `verbatim` | deve ser `true` |
| `modified` | em `verbatim` com Apache-2.0 | `true`/`false` |

## Política máxima por licença

| Licença | `docs` | `code` |
|---|---|---|
| MIT, BSD-3-Clause, Apache-2.0 | verbatim | verbatim |
| GPL-3.0 | verbatim | summary |
| Elastic-2.0 | summary | summary |
| unknown / não classificada | link | link |

## O que gravar em cada nível

- **link**: só o frontmatter e, no corpo, uma descrição curta com suas palavras.
- **summary**: síntese autoral; citações curtas entre aspas com autor e origem.
- **verbatim**: trechos copiados com o aviso de copyright e o texto (ou link fixo) da licença
  junto ao extrato; em Apache-2.0, indicar se houve alteração.

## Exemplo

```yaml
---
schema_version: "2"
origin: https://github.com/exemplo/repo
author: Fulano de Tal
date: 2026-09-24
license: MIT
relevance: padrões de orquestração de agentes
status: active
extract_policy: verbatim
notice_preserved: true
---
```

Validar: `uv run praxisforge sources validate src/data/sources/`.
