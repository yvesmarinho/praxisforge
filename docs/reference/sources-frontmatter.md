<!-- Criado em: 24/09/2026 10:58 -->
<!-- Modificado em: 25/09/2026 13:08 -->

# Referência — frontmatter de fontes (`source-schema-v3`)

Cada fonte curada é um arquivo `src/data/sources/<categoria>/<slug>.md`: frontmatter YAML com a
proveniência; corpo com a **síntese das ideias** (nenhum trecho literal, tradução ou paráfrase
próxima). Contrato: `schemas/source-schema-v3.json`.
Decisão: [ADR 0012](../decisions/0012-fontes-so-ideias.md) (substitui a graduação do
[ADR 0007](../decisions/0007-politica-de-extracao-por-licenca.md)).

## Campos

| Campo | Obrigatório | Valores / regra |
|---|---|---|
| `schema_version` | sim | `"3"` |
| `origin` | sim | URL ou descrição; nunca caminho absoluto |
| `author` | não | não vazio |
| `date` | sim | `AAAA-MM-DD`, não futura |
| `license` | sim | SPDX (`MIT`, `Apache-2.0`…) ou `unknown` — só informativa, não gradua nada |
| `relevance` | sim | por que a fonte importa |
| `status` | sim | `active` \| `pending`; `unknown` exige `pending` |

## Converter um registro v2

Registros `schema_version: "2"` (ou `"1"`) são recusados. Para converter à mão:

1. troque `schema_version` para `"3"`;
2. apague `extract_policy`, `extract_scope`, `notice_preserved` e `modified`;
3. confira que `origin`, `author`, `date`, `license`, `relevance` e `status` não mudaram;
4. se o corpo tiver trecho copiado ou traduzido, reescreva como síntese.

## Exemplo

```yaml
---
schema_version: "3"
origin: https://github.com/exemplo/repo
author: Fulano de Tal
date: 2026-09-24
license: MIT
relevance: padrões de orquestração de agentes
status: active
---
```

Validar: `uv run praxisforge sources validate src/data/sources/`.
