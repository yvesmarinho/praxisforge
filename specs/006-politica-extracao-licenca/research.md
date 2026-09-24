<!-- Criado em: 24/09/2026 10:41 -->
<!-- Modificado em: 24/09/2026 10:42 -->

# Research: Política de extração por licença

## R1 — Representação dos níveis

- **Decision**: `ExtractPolicy` como `enum` com ordem explícita (`LINK=0 < SUMMARY=1 < VERBATIM=2`),
  comparável; valores serializados em minúsculas.
- **Rationale**: a regra central é uma comparação de ordem ("declarada ≤ máxima"); enum ordenado
  deixa isso trivial e testável, sem dependência externa (domínio só stdlib).
- **Alternatives**: strings + dicionário de pesos (espalha a ordem); booleanos múltiplos
  (`can_summarize`, `can_copy`) — permitem combinações inválidas.

## R2 — Tabela licença → máxima

- **Decision**: dicionário imutável no domínio, chave = licença em `casefold`:

  | Licença | Escopo `docs` | Escopo `code` (ou ausente) |
  |---|---|---|
  | MIT, BSD-3-Clause, Apache-2.0 | verbatim | verbatim |
  | GPL-3.0 | verbatim | summary |
  | Elastic-2.0 | summary | summary |
  | unknown | link | link |
  | não classificada | link | link |

- **Rationale**: fonte única da regra (FR-002); o escopo só altera o resultado para GPL-3.0
  (copyleft); comparação sem caixa (FR-011).
- **Alternatives**: tabela em YAML/JSON versionado — flexível, mas tira a regra do domínio e exige
  validação própria; adiado até haver demanda (ampliar via ADR).

## R3 — Onde aplicar a regra

- **Decision**: schema v2 garante forma (enum de política, tipos, campos obrigatórios); a regra de
  licença e as exigências condicionais (atribuição, `notice_preserved`, `modified`) ficam na
  entidade `SourceRecord`. Validação em 2 etapas, como no registro de pastas (feature 001).
- **Rationale**: o schema não deveria duplicar a tabela (duas fontes de verdade); mensagens de
  erro de domínio citam licença/declarada/máxima (SC-003), o que o JSON Schema não faz bem.
- **Alternatives**: tabela codificada em `if/then` no schema — duplicação e mensagens ruins.

## R4 — Campos declarados de conformidade (Clarificação Q2)

- **Decision**: `author` (string, obrigatório quando política ≥ `summary`); `notice_preserved`
  (bool, obrigatório `true` quando `verbatim`); `modified` (bool, obrigatório quando `verbatim` e
  licença Apache-2.0); `extract_scope` (`docs` | `code`, opcional, ausência = `code`).
- **Rationale**: a validação confere o que o curador declara, não o corpo (fora de escopo detectar
  trechos copiados).
- **Alternatives**: exigir texto da licença no corpo (Q2 opção C, rejeitada); pasta própria com
  LICENSE (Q2 opção B, rejeitada).

## R5 — Versão do contrato

- **Decision**: `source-schema-v2.json` com `schema_version: "2"`; registro com
  `schema_version: "1"` (ou com `extract_allowed`) → `SourceSchemaMigrationRequiredError` com
  mensagem citando `extract_policy`. Sem comando de migração (não há registros versionados).
- **Rationale**: constituição II (breaking → novo major); custo zero de migração hoje.
- **Alternatives**: aceitar v1 convertendo `extract_allowed=true` → `verbatim` — inferência
  insegura (seria a política mais permissiva).

## R6 — Validação de fontes via caso de uso

- **Decision**: novo `validate_sources(reader, validator, paths)` na Application, retornando
  relatório `ok`/`failures` por arquivo (padrão `ItemFailure` já existente); a CLI só formata.
- **Rationale**: hoje `_cmd_sources_validate` valida o schema direto na Presentation, violando
  "Presentation sem regra"; a nova regra de domínio torna a correção necessária.
- **Alternatives**: aplicar `SourceRecord` dentro da CLI — manteria a violação de camada.

## R7 — Exibição em `folders show`/`list`

- **Decision**: `show` ganha linha `política máxima: <nível>` (+ `(licença não classificada)` quando
  aplicável); `list` ganha coluna com o nível logo após o status, para não quebrar consumidores que leem o caminho como última coluna (contrato 005).
- **Rationale**: FR-013; a política é derivada, sem campo persistido.
- **Alternatives**: comando novo `folders policy` — mais superfície sem ganho.

## R8 — Gate de CI (SC-002)

- **Decision**: `make validate-data` passa a rodar `praxisforge sources validate src/data/sources`
  quando o diretório existir (a CLI aplica schema + domínio; `check-jsonschema` sozinho não
  aplicaria a tabela).
- **Rationale**: o workflow `quality-gates.yml` já chama `make validate-data`.
- **Alternatives**: step separado no workflow — duplica a lógica do Makefile.
