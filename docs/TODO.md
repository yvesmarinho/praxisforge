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
- [ ] `scripts/` fora do gate do ruff (`extend-exclude` em `pyproject.toml`) — refatorar e incluir no lint quando houver tempo

## ✅ Concluído

- [x] Scaffold inicial gerado (2026-09-18T18:56:11Z)
- [x] Feature 001-registro-pastas-curadoria: registro de pastas, resolução de caminho por
      ambiente, contratos JSON Schema versionados e guarda de camadas (22/09/2026)
- [x] Feature 002-varredura-pastas-curadoria: `folders scan <alias>`/`--all`, avanço de status
      "não varrida" → "varrida", isolamento de falha por item no lote e detecção de aliases
      duplicados apontando pro mesmo caminho real (22/09/2026)
