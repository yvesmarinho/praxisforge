# 📝 TODO — Praxisforge

**Last Updated**: 2026-09-18T18:56:11Z
**Status**: 🟢 Em andamento

---

## 🟠 Em Progresso

*(nenhum)*

## 🔵 Pendente

- [ ] Configurar estrutura inicial do projeto
- [ ] Adicionar testes unitários
- [ ] Documentar APIs
- [ ] Feature futura: catálogo de skills (fora do escopo da 001)
- [x] Feature futura: detectar deriva de curadoria (concluída na feature 004 — campo final `last_curated_commit`, schema v1 aditivo) — quando o conteúdo de uma pasta `curated`
      (git) mudar em relação ao commit HEAD registrado na última curadoria, reverter status
      automaticamente para `in_curation`; exige novo campo na entidade (ex.:
      `last_curated_commit_hash`) e nova versão do schema. Ver
      `docs/reference/folders-yaml.md` ("Limitação conhecida"). Ainda sem número/spec formal —
      candidata a próxima feature depois da 003 (bootstrap, já concluída).
- [x] `scripts/` fora do gate do ruff (`extend-exclude` em `pyproject.toml`) — refatorar e incluir no lint quando houver tempo → incluído; só `T201` liberado em `scripts/` (25/09/2026)

- [ ] Detecção de aliases duplicados em `folders scan --all` (feature 002) ficou inalcançável com a
      unicidade de caminho da feature 005 — avaliar remoção do código morto

## ✅ Concluído

- [x] Scaffold inicial gerado (2026-09-18T18:56:11Z)
- [x] Feature 001-registro-pastas-curadoria: registro de pastas, resolução de caminho por
      ambiente, contratos JSON Schema versionados e guarda de camadas (22/09/2026)
- [x] Feature 002-varredura-pastas-curadoria: `folders scan <alias>`/`--all`, avanço de status
      "não varrida" → "varrida", isolamento de falha por item no lote e detecção de aliases
      duplicados apontando pro mesmo caminho real (22/09/2026)
- [x] Feature 003-bootstrap-registro-pastas: `folders bootstrap <root>` gera o registro inicial a
      partir de uma pasta-raiz (heurística de README/LICENSE), idempotente (nunca sobrescreve
      pasta já registrada), novo status `ignore` (aplicado só manualmente) respeitado por
      `folders scan --all` (22/09/2026)
- [x] Feature 004-deteccao-mudanca-conteudo: `last_curated_commit` gravado ao marcar `curated`,
      varredura reverte para `in_curation` quando os arquivos da pasta mudam (via `git`), legado
      recebe referência na primeira varredura (23/09/2026)
- [x] Feature 005-caminho-absoluto-registro: caminho absoluto obrigatório no registro (schema v2),
      bootstrap `<raiz>__<sub>` sem colisão, `update --path`, `folders migrate` (23/09/2026)
- [x] Feature 006-politica-extracao-licenca: `extract_policy` por licença (link/summary/verbatim),
      `source-schema-v2`, `validate_sources`, política máxima em `folders show/list` (24/09/2026)
- [x] Feature 007-registro-fora-do-repo: registro de pastas fora do repositório (XDG/`~/.config`,
      `--registry`, `PRAXISFORGE_REGISTRY`), exemplo versionado, `folders relocate` (24/09/2026)
- [x] Limitação conhecida (feature 007): a CLI resolve `schemas/` e o registro antigo
      (`src/data/folders.yaml`) a partir do diretório atual — só funciona na raiz do projeto
      → raiz por marcador `pyproject.toml` + `PRAXISFORGE_ROOT`, ADR 0010 (25/09/2026)
- [x] Dívida: `scripts/` com violações de ruff e fora do gate; `ruff format --check` fora do
      `make lint` (ex.: `src/praxisforge/infrastructure/filesystem_folder_probe.py`) → corrigido (25/09/2026)
- [x] Feature 008-biblioteca-skills: `skills/` versionado com template, `skills validate`,
      `skills catalog` (`skills/README.md` determinístico), `skills publish` (cópia/symlink,
      marcador `.praxisforge-skill.json`, regra de versão, órfãs/`--prune`) e
      `scripts/publish-skills` (24/09/2026)
- [x] Limitação conhecida (feature 008): `skills` resolve `skills/` e `src/data/sources/` a partir
      do diretório atual (mesma da feature 007); `scripts/publish-skills` contorna → ADR 0010 (25/09/2026)
- [ ] Criar as primeiras skills reais (depende de registros em `src/data/sources/`)
- [x] Primeira curadoria real: fonte `praticas-agentes/karpathy-guidelines` (MIT declarada no README, `summary`) e skill `diretrizes-codificacao` 1.0.0; pasta `github_forks__andrej_karpathy_skills` reclassificada para MIT e marcada `curated` (24/09/2026)
- [x] Registro de pastas: descrição de `github_forks__andrej_karpathy_skills` veio errada do bootstrap; `folders update` não tem `--description` → `--description` adicionado (25/09/2026)
- [x] Decisão: skill `diretrizes-codificacao` **não** publicada no `~/.claude/skills` global — duplicaria o CLAUDE.md global (25/09/2026)
- [x] Curadoria `agent_skills`: fonte `praticas-agentes/agent-skills-constraints` (MIT, `summary`) e skill `guarda-barra-qualidade` 1.0.0; pasta `github_forks__agent_skills` marcada `curated` (25/09/2026)
- [ ] Curadoria automatizada — debate em `docs/debates/curadoria-automatizada.md` (25/09/2026), dividida em 4 features:
      009-acervo-library → 010-inventario-curadoria → 011-triagem-llm → 012-revisao-promocao
- [ ] Reescrever `guarda-barra-qualidade` só pelas ideias (hoje é derivada, MIT com aviso) — na refação da 012
- [ ] `scripts/session-manager.py` quebrado: `lib/session_docs.py` importa `lib.session`, que não existe (pré-existente)
- [ ] Scripts de `scripts/` (scaffold) sem o cabeçalho padrão (`NOME`/`MODIFICADO`...)
- [x] Feature 009-acervo-library: acervo `library/` (6 tipos), `library validate|index|publish`, publicação só em projetos, fontes v3 "só ideias", migração de `skills/`, constituição v4.0.0 (25/09/2026)
- [ ] Revisar a "política máxima" exibida por `folders show/list` (feature 006): perdeu sentido com "só ideias" (ADR 0012); decidir remover ou trocar o rótulo, e o uso de `domain/license_policy.py`
- [ ] Exceções `ExtractPolicyExceedsLicenseError` e `IncompleteAttributionError` ficaram sem uso após o `source-schema-v3` — remover junto da revisão acima
- [ ] Nomes `ForeignSkillDestinationError`, `SkillVersionNotBumpedError` e `SkillPublicationError` servem a todos os tipos do acervo — avaliar renomear
- [ ] Features seguintes da curadoria automatizada: 010-inventario-curadoria → 011-triagem-llm → 012-revisao-promocao
- [x] Feature 010-inventario-curadoria: `curation inventory|status`, convenções em `~/.config/praxisforge/curation-conventions.yaml`, manifesto/estado por alias (25/09/2026)
- [x] Rodar `curation inventory --all` nas 55 pastas reais e revisar os `unknown` para ampliar as convenções (28/09/2026: unknown 64% → 29%)
- [ ] `ruff format .` reformata blocos de código dentro de `.md` (ex.: `SESSION_DOCS_STYLE_GUIDE.md`) — avaliar `extend-exclude` para docs
- [x] Cabeçalhos da feature 010 com horário adiantado corrigidos (28/09/2026) — ver `docs/bugs/2026-09-28-cabecalhos-horario-adiantado-010.md`
- [ ] Mesmo problema de horário adiantado em `specs/002-*`, `specs/003-*` e `docs/bugs/2026-09-24-ci-scan-escala-quadratica.md`
- [ ] Convenções não têm lista de exclusão: traduções (`ja/`, `zh/`, `uk/`, `vi/`) e docs de site seguem como `unknown` — avaliar exclusões configuráveis ou deixar para a triagem (011)
- [ ] Não existe `folders remove` (entradas espúrias exigiram edição manual do registro)
- [x] Feature 011-triagem-llm: `curation triage`, rascunhos em `~/.config/praxisforge/curation/_drafts/`, estado v2, prompts em `prompts/curation/` (28/09/2026)
- [ ] Triagem: paralelismo das chamadas, se a escala pedir (hoje serial; ~6 s por chamada)
- [ ] Triagem: impressão digital por prompt (mudar só `draft.md` não precisaria refazer a triagem)
- [ ] 012: amostrar vereditos `covered`/`out_of_scope` na revisão (risco residual de injeção que distorce veredito — ADR 0014)
- [ ] Juiz de similaridade não determinístico (5/6 na calibração com Haiku): avaliar votação ou modelo maior para o juiz
- [ ] Spec 011, FR-035: acrescentar o exit 130 (interrupção), já previsto no contrato da CLI (achado I1 da análise)
