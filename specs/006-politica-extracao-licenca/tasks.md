<!-- Criado em: 24/09/2026 10:50 -->
<!-- Modificado em: 24/09/2026 10:44 -->

# Tasks: Política de extração por licença

**Input**: Design documents from `/specs/006-politica-extracao-licenca/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-sources.md,
contracts/source-schema-v2.json, quickstart.md

**Tests**: OBRIGATÓRIOS (constituição III). Em cada grupo: testes de falha → confirmar vermelho →
implementar → verde.

**Organization**: US1 (P1) validar política × licença; US2 (P2) política máxima em
`folders show/list`; US3 (P3) escopo docs/código para GPL-3.0.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Confirmar baseline verde na branch `006-politica-extracao-licenca` com `src/data/folders.yaml` na versão do HEAD (`git stash` do registro local → `make lint`, `make test`, `make validate-data` → restaurar); nunca incluir `src/data/folders.yaml` em commit (repositório público)

---

## Phase 2: Foundational (bloqueia todas as stories)

### Testes (vermelho primeiro)

- [X] T002 [P] Testes em tests/unit/domain/test_license_policy.py: `ExtractPolicy` ordenada (`LINK < SUMMARY < VERBATIM`), construída a partir de `"link"|"summary"|"verbatim"` e rejeitando outro valor; `ExtractScope` (`docs`/`code`); `max_policy(license, scope)` parametrizado para MIT, BSD-3-Clause, Apache-2.0 → verbatim; Elastic-2.0 → summary; GPL-3.0 → summary (ambos os escopos até a US3); unknown → link; licença não classificada (MPL-2.0, CC-BY-4.0, "") → link; comparação sem caixa (`mit`, `APACHE-2.0`); `is_classified` true só para as 5 licenças + unknown (FR-002, FR-003, FR-011, SC-001)
- [X] T003 [P] Testes em tests/unit/domain/test_errors.py: `ExtractPolicyExceedsLicenseError` ⊂ `PraxisForgeError` com atributos `license`, `scope`, `declared`, `maximum` e mensagem citando os quatro; `IncompleteAttributionError` ⊂ `PraxisForgeError` com atributo `field`; `SourceSchemaMigrationRequiredError` ⊂ `ContractValidationError` com mensagem citando `extract_policy` e `source-schema-v2`
- [X] T004 [P] Testes de contrato em tests/contract/test_source_schema_v2.py: `schemas/source-schema-v2.json` é Draft 2020-12 válido; exige `schema_version: "2"` e `extract_policy`; rejeita `extract_allowed` (additionalProperties), política fora do enum, `extract_scope` fora de `docs|code`; `unknown` ⇒ `pending`; `pending` ⇒ `link`; documento v1 rejeitado (FR-001, FR-014)
- [X] T005 [P] Ajustar tests/contract/test_schemas_match_contracts.py: `source-schema-v2.json` idêntico (sem `_meta`) a specs/006-politica-extracao-licenca/contracts/source-schema-v2.json
- [X] T006 Rodar T002–T005 e **confirmar vermelho**

### Implementação

- [X] T007 Criar schemas/source-schema-v2.json copiando specs/006-politica-extracao-licenca/contracts/source-schema-v2.json (com `_meta` atualizado); manter schemas/source-schema-v1.json
- [X] T008 [P] Criar src/praxisforge/domain/license_policy.py (stdlib: `ExtractPolicy` com ordem, `ExtractScope`, tabela imutável em casefold, `max_policy`, `is_classified`), com cabeçalho padrão e docstrings reST + doctest
- [X] T009 [P] Adicionar as 3 exceções em src/praxisforge/domain/errors.py e reexportar em src/praxisforge/application/errors.py
- [X] T010 Rodar T002–T005 e **confirmar verde**; `make lint`

**Checkpoint**: tabela e contrato prontos.

---

## Phase 3: User Story 1 — Validar política declarada × licença (P1) 🎯 MVP

**Goal**: `sources validate` rejeita política acima da máxima e extrato sem atribuição, em lote.

**Independent Test**: registros `.md` em `tmp_path` com combinações licença × política; `sources validate` lista falhas por arquivo com licença/declarada/máxima e sai com 1.

### Testes (vermelho primeiro)

- [X] T011 [P] [US1] Reescrever tests/unit/domain/test_source_record.py para v2: campos `extract_policy`, `author`, `extract_scope`, `notice_preserved`, `modified`; ordem de verificação do data-model; falhas: `unknown` com `active`; `pending` com política ≠ `link`; política > máxima (matriz parametrizada licença × política, escopo `code`) → `ExtractPolicyExceedsLicenseError` com atributos corretos; `summary`/`verbatim` sem `author` → `IncompleteAttributionError(field="author")`; `link` sem `author` aceito; `verbatim` sem `notice_preserved` ou com `false` → `IncompleteAttributionError`; Apache-2.0 `verbatim` sem `modified` → `IncompleteAttributionError(field="modified")`; política mais restritiva que a máxima aceita (FR-004–FR-009, SC-001)
- [X] T012 [P] [US1] Testes em tests/unit/application/test_validate_sources.py com fakes de `SourceReader` e `ContractValidator`: lote com válidos e inválidos avalia todos e agrega `ItemFailure` por arquivo (FR-012); falha de schema e falha de domínio no mesmo lote; `schema_version: "1"` ou `extract_allowed` presente → falha `SourceSchemaMigrationRequiredError` (FR-014); arquivo ilegível/sem frontmatter (reader levanta `RegistryUnavailableError`) vira falha do item; lista vazia → relatório vazio sem erro; licença não classificada com `link` passa sem aviso (Q3)
- [X] T013 [P] [US1] Testes em tests/integration/test_source_frontmatter.py: adapter `FrontmatterSourceReader` implementa a porta `SourceReader` (mantendo `read_frontmatter` como está); arquivo inexistente, sem frontmatter e YAML inválido → `RegistryUnavailableError`
- [X] T014 [P] [US1] Atualizar tests/integration/test_cli_validate.py para v2: fonte MIT `verbatim` completa → `1 ok, 0 com falha`, exit 0; Elastic-2.0 `verbatim` → linha `política 'verbatim' excede a máxima 'summary' para a licença Elastic-2.0 (escopo: code)`, exit 1; registro v1 → mensagem pedindo `extract_policy`, exit 1; diretório vazio → `0 ok, 0 com falha`, exit 0 (contracts/cli-sources.md)
- [X] T015 [P] [US1] Teste de escala em tests/integration/test_validate_sources_scale.py: 500 registros válidos em `tmp_path` validados em < 5 s (SC-005)
- [X] T016 [US1] Rodar T011–T015 e **confirmar vermelho**

### Implementação

- [X] T017 [US1] Evoluir src/praxisforge/domain/source_record.py para v2 (remove `extract_allowed`; aplica regras via `license_policy`; exceções semânticas) — atualizar cabeçalho/histórico
- [X] T018 [US1] Adicionar porta `SourceReader` em src/praxisforge/application/ports.py e adapter `FrontmatterSourceReader` em src/praxisforge/infrastructure/source_frontmatter.py
- [X] T019 [US1] Criar caso de uso src/praxisforge/application/validate_sources.py (`validate_sources(reader, validator, paths) -> SourceValidationReport`): detecta v1 → `SourceSchemaMigrationRequiredError`; schema `source-schema-v2`; constrói `SourceRecord`; falha por item; log estruturado via `log_event`
- [X] T020 [US1] Refatorar `_cmd_sources_validate` em src/praxisforge/presentation/cli.py para usar `validate_sources` (CLI só expande diretórios e formata); remover import órfão de `read_frontmatter` se sobrar
- [X] T021 [US1] Rodar T011–T015 e **confirmar verde**; `make lint`; verificar tests/architecture (camadas)

**Checkpoint**: US1 entregável sozinha (MVP).

---

## Phase 4: User Story 2 — Política máxima em `folders show`/`list` (P2)

**Goal**: curador vê a política máxima derivada da licença de cada pasta.

**Independent Test**: registrar pastas MIT, unknown e MPL-2.0; `show` exibe a linha de política; `list` exibe a coluna após o status.

### Testes (vermelho primeiro)

- [X] T022 [P] [US2] Testes em tests/unit/application/test_query_folders.py: `folder_policy(folder)` (ou campo no resultado de `show_folder`/`list_folders`) retorna máxima e `classified` — MIT → verbatim/True; unknown → link/True; MPL-2.0 → link/False (FR-013)
- [X] T023 [P] [US2] Testes em tests/integration/test_cli_folders.py: `folders show` imprime `política máxima: verbatim`; pasta MPL-2.0 imprime `política máxima: link (licença não classificada)`; `folders list` tem a política como coluna imediatamente após o status e o caminho continua a última coluna (contracts/cli-sources.md)
- [X] T024 [US2] Rodar T022–T023 e **confirmar vermelho**

### Implementação

- [X] T025 [US2] Expor a política máxima em src/praxisforge/application/query_folders.py (derivada via `license_policy`, sem persistir)
- [X] T026 [US2] Exibir a política em `_cmd_folders_show` e `_cmd_folders_list` em src/praxisforge/presentation/cli.py
- [X] T027 [US2] Rodar T022–T023 e **confirmar verde**; `make lint`

**Checkpoint**: US1 + US2 funcionando de forma independente.

---

## Phase 5: User Story 3 — Escopo docs/código para GPL-3.0 (P3)

**Goal**: GPL-3.0 permite `verbatim` só com `extract_scope: docs`.

**Independent Test**: GPL-3.0 `verbatim` com `docs` passa; com `code` ou sem escopo falha com máxima `summary`.

### Testes (vermelho primeiro)

- [X] T028 [P] [US3] Acrescentar em tests/unit/domain/test_license_policy.py: GPL-3.0 → verbatim para `docs`, summary para `code`; escopo não altera o resultado das demais licenças (FR-010)
- [X] T029 [P] [US3] Acrescentar em tests/unit/domain/test_source_record.py: GPL-3.0 `verbatim` + `docs` aceito; `code` → `ExtractPolicyExceedsLicenseError(scope=code, maximum=summary)`; sem escopo tratado como `code`
- [X] T030 [P] [US3] Acrescentar em tests/integration/test_cli_validate.py: GPL-3.0 `verbatim` sem escopo → linha com `(escopo: code)`, exit 1; com `extract_scope: docs` → exit 0
- [X] T031 [US3] Rodar T028–T030 e **confirmar vermelho**

### Implementação

- [X] T032 [US3] Incluir GPL-3.0 com variação por escopo na tabela de src/praxisforge/domain/license_policy.py e considerar `extract_scope` em src/praxisforge/domain/source_record.py
- [X] T033 [US3] Rodar T028–T030 e **confirmar verde**; `make lint`

**Checkpoint**: todas as stories funcionais.

---

## Phase 6: Polish & Cross-Cutting

- [X] T034 [P] ADR docs/decisions/0007-politica-de-extracao-por-licenca.md (níveis, tabela, amparo da citação curta — Lei 9.610/98 art. 46 III, licença não classificada → link, GPL por escopo, não é aconselhamento jurídico) e índice em docs/decisions/README.md (FR-015)
- [X] T035 [P] Criar docs/reference/sources-frontmatter.md (campos v2, tabela, exemplos por nível) e atualizar a seção `sources validate` + `folders show/list` em docs/guides/operar-cli-praxisforge.md (FR-016)
- [X] T036 [P] Atualizar docs/architecture/overview.md (novo módulo `license_policy`, caso de uso `validate_sources`, porta `SourceReader`)
- [X] T037 Atualizar alvo `validate-data` no Makefile: rodar `uv run praxisforge sources validate src/data/sources` somente se o diretório existir (SC-002)
- [X] T038 Executar os cenários de specs/006-politica-extracao-licenca/quickstart.md com arquivos descartáveis fora do versionamento
- [X] T039 Gates finais com `src/data/folders.yaml` na versão do HEAD: `make lint`, `ruff format --check` nos arquivos alterados, `make test` (cobertura ≥ 90%), `make validate-data`, `make security`; `graphify update .`
- [X] T040 Relatório em docs/bugs/ apenas se surgir bug durante a implementação; registrar a sessão no vault `claude_memory` (projects/praxisforge.md)

---

## Dependencies & Execution Order

- Setup (T001) → Foundational (T002–T010) → US1 (T011–T021) → US2 (T022–T027) e US3 (T028–T033) → Polish (T034–T040).
- US2 depende só de `license_policy` (Foundational); pode rodar em paralelo com US1.
- US3 depende de US1 (T017, `SourceRecord` v2) e de `license_policy`.
- Dentro de cada fase: testes [P] juntos → confirmar vermelho → implementação → confirmar verde.

## Parallel Examples

- Foundational: T002, T003, T004 e T005 (arquivos distintos); depois T008 e T009.
- US1: T011, T012, T013, T014 e T015 juntos.
- US2: T022 e T023 juntos; a fase inteira pode andar em paralelo com US1.
- Polish: T034, T035 e T036 juntos.

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1 (T001–T021) — já bloqueia extratos acima do permitido.
2. US2: visibilidade da política no registro de pastas.
3. US3: refinamento GPL (sem ela, GPL fica em `summary` para tudo — seguro).
4. Polish: ADR, docs, gate do CI.
