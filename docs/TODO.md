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
- [ ] `scripts/` fora do gate do ruff (`extend-exclude` em `pyproject.toml`) — refatorar e incluir no lint quando houver tempo

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
- [ ] Limitação conhecida (feature 007): a CLI resolve `schemas/` e o registro antigo
      (`src/data/folders.yaml`) a partir do diretório atual — só funciona na raiz do projeto
- [ ] Dívida: `scripts/` com violações de ruff e fora do gate; `ruff format --check` fora do
      `make lint` (ex.: `src/praxisforge/infrastructure/filesystem_folder_probe.py`)

