<!-- Criado em: 28/09/2026 15:32 -->
<!-- Modificado em: 28/09/2026 15:40 -->

# Implementation Plan: Triagem de curadoria com LLM

**Branch**: `011-triagem-llm` | **Date**: 28/09/2026 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/011-triagem-llm/spec.md`

## Summary

Nova etapa `curation triage`. Para cada artefato elegível (estado da 010), o praxisforge monta um
prompt com o índice do acervo, os rascunhos pendentes, até 3 itens parecidos do mesmo tipo e os
critérios versionados, e chama o `claude` CLI **sem ferramentas**. O CLI roda com
`--tools ""`, sem MCP, sem settings e com system prompt próprio; a saída é JSON validado por
schema. O isolamento foi comprovado com uma chamada real (research R1).

- **Lacunas** recebem rascunho do modelo de rascunho, verificado por similaridade estrutural
  (esqueleto independente de idioma) e por um juiz, com uma regeneração.
- **Gravação**: vereditos vão para o `state.json` v2 após cada artefato; rascunhos, para
  `curation/_drafts/`, uma área global, porque uma fusão pode atingir o rascunho de outra pasta.
- **Teto**: por chamadas e/ou US$ (o CLI informa o custo), reservando o pior caso de um artefato.
  A retomada é rodar de novo o mesmo comando.
- **Testes**: o modelo real nunca é chamado; usam uma porta falsa e um executável `claude` falso.

## Technical Context

**Language/Version**: Python 3.12+ (uv)

**Primary Dependencies**: existentes (pyyaml, pydantic, jsonschema, pathspec); nenhuma nova. O
`subprocess`, o `difflib` e o `hashlib` vêm da stdlib. O `claude` CLI é dependência de ambiente,
não de pacote.

**Storage**: JSON fora do repositório: `<dir do registro>/curation/<alias>/state.json` (v2) e
`<dir do registro>/curation/_drafts/<id>.json`. No repositório ficam os prompts em
`prompts/curation/` e os schemas em `schemas/`.

**Testing**: pytest (unit, integration, contract, architecture), cobertura ≥ 90%; marcador novo
`live` (CLI real), fora do `make test`.

**Target Platform**: Linux, CLI local, `claude` 2.1.x autenticado por assinatura.

**Project Type**: CLI em camadas (Presentation → Application → Domain ← Infrastructure).

**Performance Goals**: não há meta de latência (limitada pelo modelo, ~6 s por chamada); o
overhead do praxisforge por artefato é < 100 ms, sem contar a chamada.

**Constraints**: K4 (sem ferramentas) inegociável e falha fechada (versão do CLI fora da faixa
testada ou flag recusado → nenhuma chamada); ambiente e cwd do processo isolados (FR-039); nenhuma escrita fora de `curation/`; nenhum
texto de terceiros no repositório, inclusive em fixtures; teto nunca ultrapassado; caminho
absoluto fora da saída e dos logs.

**Scale/Scope**: 18 pastas inventariadas e 5.658 artefatos elegíveis hoje; execuções de dezenas
a centenas de chamadas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Camadas | Domain: `curation_triage` (veredito, elegibilidade, transições), `curation_draft` (proposta, rascunho, origens), `structure_similarity` (esqueleto, pontuação), `prompt_set`. Application: `triage_folders` e o orçamento. Infra: `claude_cli_model`, `filesystem_prompt_source`, `library_catalog`, `filesystem_artifact_reader`, `json_draft_store`. O domínio não importa `subprocess` nem `jsonschema` | ✅ |
| II. Contratos | 5 schemas novos (3 de resposta do modelo, rascunho, estado v2) com `schema_version` nos documentos persistidos; toda resposta do modelo é validada antes de virar domínio | ✅ |
| III. Test-first | Primeiro os testes de falha: resposta inválida, timeout, CLI ausente, falhas consecutivas, teto, item citado inexistente, injeção, estado v1, lock, tamanho e flags de segurança | ✅ |
| IV. Erros semânticos | `LanguageModel{NotInstalled,Unavailable,Timeout,ResponseInvalid}Error`, `LanguageModelUntestedVersionError`, `CurationPathUnsafeError`, `PromptSetError`, `InvalidTriageError`, `ArtifactTooLargeError`, `DraftStoreCorruptError`, `TriageBudgetExhausted`; o lote agrega por artefato e por pasta | ✅ |
| V. Fontes/licença/local | Só ideias: rascunho autoral + dupla verificação; licença `link`/`unknown` → só o resumo; staging fora do repo; fixture de calibração guarda só o esqueleto numérico (R7) | ✅ |
| VI. Acervo | Só lê `library/` (índice e itens); a escrita no acervo é da 012 | ✅ |
| VII. Vault | Registro da sessão no vault ao fim | ✅ |

Nenhuma violação: Complexity Tracking vazio.

**Pós-design**: reavaliado após o data-model e os contratos, e continua ✅. Duas decisões que
tocam princípios: a área global `_drafts/` (R8) fica fora do repo, como exige o V; o estado v2
com leitura de v1 (R9) mantém o II, porque as duas versões são validadas.

## Project Structure

### Documentation (this feature)

```text
specs/011-triagem-llm/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli-curation-triage.md
│   ├── curation-triage-response-v1.json
│   ├── curation-draft-response-v1.json
│   ├── curation-judge-response-v1.json
│   ├── curation-draft-schema-v1.json
│   └── curation-state-schema-v2.json
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
prompts/curation/
├── triage.md        # system prompt da triagem
├── draft.md         # system prompt do rascunho (só ideias, estrutura própria, pt-BR)
├── judge.md         # system prompt do juiz
└── criteria.md      # covered / gap / out_of_scope (vai no contexto da triagem)
schemas/             # cópia dos 5 contratos JSON
src/praxisforge/
├── domain/
│   ├── curation_triage.py        # TriageVerdict, Triage, MergeTarget, is_eligible, transições
│   ├── curation_draft.py         # DraftProposal, DraftOrigin, Draft, draft_id
│   ├── structure_similarity.py   # skeleton_of, structural_score, SimilarityCheck
│   ├── prompt_set.py             # PromptSet, fingerprint
│   ├── curation_state.py         # + ArtifactState.triage; reconcile preserva/zera triage
│   └── errors.py                 # + erros novos
├── application/
│   ├── ports.py                  # + LanguageModel, PromptSource, LibraryCatalog, ArtifactReader, DraftStore
│   ├── triage_budget.py          # TriageBudget
│   ├── triage_context.py         # seleção dos 3 itens parecidos (Jaccard), montagem do prompt com nonce
│   ├── triage_folders.py         # caso de uso: lote tolerante, ordem, teto, falhas consecutivas
│   └── query_curation.py         # + contagem por veredito e alertas
├── infrastructure/
│   ├── claude_cli_model.py       # subprocess, flags de isolamento, stdin, timeout/killpg, parse
│   ├── filesystem_prompt_source.py
│   ├── library_catalog.py        # sobre o LibraryRepository (009)
│   ├── filesystem_artifact_reader.py
│   ├── json_draft_store.py       # _drafts/, flock, gravação atômica, validação
│   └── json_curation_store.py    # + v2, leitura de v1, save_state
└── presentation/cli.py           # + curation triage, colunas novas do status, exit 4
tests/
├── unit/domain/test_curation_triage.py
├── unit/domain/test_curation_draft.py
├── unit/domain/test_structure_similarity.py   # + calibração (fixture de esqueleto numérico)
├── unit/domain/test_prompt_set.py
├── unit/application/test_triage_budget.py
├── unit/application/test_triage_context.py
├── integration/test_triage_folders.py          # FakeLanguageModel
├── integration/test_claude_cli_model.py        # `claude` falso: flags, stdin, env filtrado, cwd removido, versão, timeout
├── integration/test_json_draft_store.py        # + permissões, link simbólico, rascunho corrompido
├── integration/test_json_curation_store_v2.py
├── integration/test_cli_curation_triage.py
├── contract/test_curation_triage_schemas.py
├── architecture/                               # guarda: domínio sem subprocess/jsonschema
├── fixtures/similarity/constraint-driven-development.skeleton.json
└── live/test_claude_cli_isolation.py           # marcador `live`
docs/decisions/0014-triagem-com-llm.md
docs/guides/triar-curadoria.md
```

**Structure Decision**: mantém a estrutura única de `src/praxisforge` em quatro camadas. Os
prompts ficam em `prompts/curation/` (C6), fora de `src/`, porque são conteúdo editável pelo
curador e fazem parte do processo, mas não são código Python.

## Complexity Tracking

Sem violações da constituição.
