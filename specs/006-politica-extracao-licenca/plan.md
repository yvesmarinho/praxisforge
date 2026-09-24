<!-- Criado em: 24/09/2026 10:41 -->
<!-- Modificado em: 24/09/2026 10:41 -->

# Implementation Plan: Política de extração por licença

**Branch**: `006-politica-extracao-licenca` | **Date**: 24/09/2026 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-politica-extracao-licenca/spec.md`

## Summary

O registro de fonte troca o booleano `extract_allowed` por `extract_policy` (`link` < `summary` <
`verbatim`), com atribuição (`author`) e campos declarados de conformidade
(`notice_preserved`, `modified`, `extract_scope`). Uma tabela única no domínio
(`license_policy.py`) deriva a política máxima de cada licença; `SourceRecord` passa a aplicar a
regra "declarada ≤ máxima" com exceção semântica própria. O contrato evolui para
`source-schema-v2.json` (breaking). `praxisforge sources validate` deixa de validar só o schema e
passa por um caso de uso novo (`validate_sources`) que aplica schema + regras de domínio em lote.
`folders show`/`list` exibem a política máxima derivada da licença de cada pasta (sem campo novo
no `folders.yaml`). ADR 0007 registra a decisão.

## Technical Context

**Language/Version**: Python 3.12+ (mesmo ambiente das features 001–005)

**Primary Dependencies**: nenhuma nova (stdlib + pydantic/jsonschema/pyyaml já presentes)

**Storage**: `src/data/sources/<categoria>/<slug>.md` (frontmatter YAML); `schemas/source-schema-v2.json`
novo; `source-schema-v1.json` mantido apenas para rejeitar com mensagem de migração (FR-014)

**Testing**: pytest + pytest-cov; tabela licença × política coberta por teste parametrizado (SC-001);
teste de escala com 500 registros (SC-005)

**Target Platform**: CLI Linux

**Project Type**: CLI (single project, 4 camadas)

**Performance Goals**: validar 500 registros de fonte em < 5 s

**Constraints**: domínio só stdlib; nenhuma dependência nova; `folders.yaml` sem mudança de schema;
registros de fonte ainda não existem (sem migração automática)

**Scale/Scope**: dezenas a centenas de registros de fonte; 5 licenças classificadas + `unknown`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Camadas**: PASS. Tabela e ordenação de políticas no Domain (stdlib, `enum`); leitura de
  frontmatter e schema na Infrastructure (já existentes); novo caso de uso `validate_sources` na
  Application orquestra schema + entidade — hoje a CLI valida direto contra o schema, o que é
  corrigido (Presentation sem regra).
- **II. Contratos**: PASS. Remover `extract_allowed` e adicionar campos obrigatórios é breaking →
  `source-schema-v2.json`, `schema_version: "2"`; v1 reconhecido só para mensagem de migração.
- **III. Test-First**: PASS (tasks/implement): matriz de falhas licença × política × escopo antes
  da implementação; filesystem (arquivo ilegível/frontmatter ausente) já coberto e reaproveitado.
- **IV. Erros semânticos**: PASS. Novas exceções: `ExtractPolicyExceedsLicenseError` (cita
  licença, declarada, máxima), `IncompleteAttributionError`, `SourceSchemaMigrationRequiredError`;
  falhas agregadas por arquivo no lote.
- **V. Proveniência e Licença**: PASS — reforçado. "Sem licença → pending e sem extrato" vira
  `unknown → link`; nenhuma mudança no `folders.yaml`.
- **VI/VII**: N/A.

**Resultado**: sem violações.

## Project Structure

### Documentation (this feature)

```text
specs/006-politica-extracao-licenca/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/cli-sources.md
├── contracts/source-schema-v2.json
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
schemas/source-schema-v2.json                      # NOVO (extract_policy, author, notice_preserved,
                                                   #   modified, extract_scope; schema_version "2")
src/praxisforge/
├── domain/
│   ├── license_policy.py                          # NOVO: ExtractPolicy (ordenada), ExtractScope,
│   │                                              #   max_policy(license, scope), is_classified(license)
│   ├── source_record.py                           # extract_policy + author + campos declarados;
│   │                                              #   regra declarada ≤ máxima, atribuição, verbatim
│   └── errors.py                                  # + ExtractPolicyExceedsLicenseError,
│                                                  #   IncompleteAttributionError,
│                                                  #   SourceSchemaMigrationRequiredError
├── application/
│   ├── ports.py                                   # + SourceReader (frontmatter) se ainda não houver porta
│   ├── validate_sources.py                        # NOVO: lote, schema v2 + SourceRecord, falha por item
│   └── query_folders.py                           # expõe política máxima por pasta (derivada)
├── infrastructure/source_frontmatter.py           # adapter da porta SourceReader (sem mudança de regra)
└── presentation/cli.py                            # sources validate → caso de uso; show/list com política
docs/decisions/0007-politica-de-extracao-por-licenca.md
docs/guides/operar-cli-praxisforge.md              # seção de política de extração
docs/reference/sources-frontmatter.md              # NOVO: campos v2 e tabela
Makefile                                           # validate-data valida src/data/sources quando existir
```

**Structure Decision**: mesmas 4 camadas; um módulo de domínio novo (tabela), um caso de uso novo
(validação de fontes em lote) que tira a regra da CLI.

## Complexity Tracking

Nenhuma violação.
