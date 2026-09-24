# 📚 Índice — Praxisforge

**Projeto**: `praxisforge`
**Criado em**: 2026-09-18T18:56:11Z
**Last Updated**: 2026-09-18T18:56:11Z
**Last Session**: N/A

---

## Documentação Principal

| Arquivo | Descrição |
|---------|-----------|
| [README.md](../README.md) | Documentação pública |
| [TODO.md](TODO.md) | Tarefas pendentes |
| [TODAY_ACTIVITIES.md](TODAY_ACTIVITIES.md) | Atividades do dia |

## Sessões de Trabalho

```
SESSIONS/
└── YYYY-MM-DD/
    ├── SESSION_RECOVERY_YYYY-MM-DD.md
    ├── DAILY_ACTIVITIES_YYYY-MM-DD.md
    ├── SESSION_REPORT_YYYY-MM-DD.md
    └── FINAL_STATUS_YYYY-MM-DD.md
```

Nota (21/09/2026): o log diário de sessão foi migrado para o vault Obsidian
`claude_memory` (`daily/`); não é mais criado em `docs/SESSIONS/` neste projeto.

## Features Entregues

| Feature | Descrição | Docs |
|---------|-----------|------|
| 001-registro-pastas-curadoria | Registro versionado de pastas a curar (`src/data/folders.yaml`), resolução de caminho por variável de ambiente, contratos JSON Schema versionados (`schemas/`) e arquitetura em 4 camadas com guarda de dependências automatizado | [spec](../specs/001-registro-pastas-curadoria/spec.md) · [plan](../specs/001-registro-pastas-curadoria/plan.md) · [arquitetura](architecture/overview.md) · [ADRs](decisions/) |
| 002-varredura-pastas-curadoria | Varredura (`folders scan <alias>`/`--all`) que atualiza `status`/`last_scanned` das pastas registradas, isola falha por item no lote e detecta aliases duplicados apontando pro mesmo caminho real — sem nenhuma camada/porta nova (reaproveita 100% a feature 001) | [spec](../specs/002-varredura-pastas-curadoria/spec.md) · [plan](../specs/002-varredura-pastas-curadoria/plan.md) · [arquitetura](architecture/overview.md) |
| 003-bootstrap-registro-pastas | Bootstrap (`folders bootstrap <root>`) que gera o registro inicial a partir de uma pasta-raiz (heurística de README/LICENSE), idempotente, com novo status `ignore` (só manual) respeitado por `folders scan --all` — mudança de contrato aditiva (mesmo `folders-schema-v1.json`) | [spec](../specs/003-bootstrap-registro-pastas/spec.md) · [plan](../specs/003-bootstrap-registro-pastas/plan.md) · [arquitetura](architecture/overview.md) |
| 004-deteccao-mudanca-conteudo | Versão curada (`last_curated_commit`) gravada ao marcar `curated` e verificação na varredura: pasta curada cujos arquivos mudaram (diff restrito à pasta, via executável `git`) volta para `in_curation`; legado recebe referência — mudança de contrato aditiva | [spec](../specs/004-deteccao-mudanca-conteudo/spec.md) · [plan](../specs/004-deteccao-mudanca-conteudo/plan.md) · [ADR 0005](decisions/0005-deteccao-mudanca-por-git-cli.md) |
| 005-caminho-absoluto-registro | Caminho absoluto obrigatório por pasta no registro (`folders-schema-v2`, constituição v2.0.0): unicidade sem aninhamento, bootstrap com alias `<raiz>__<sub>` sem colisão, `update --path`, fim das variáveis `PRAXISFORGE_FOLDER_*` e comando `folders migrate` (v1 → v2) | [spec](../specs/005-caminho-absoluto-registro/spec.md) · [plan](../specs/005-caminho-absoluto-registro/plan.md) · [ADR 0006](decisions/0006-caminho-absoluto-no-registro.md) · [bug](bugs/2026-09-23-update-regravava-versao-curada.md) |
| 008-biblioteca-skills | Biblioteca de skills versionada: template, `skills validate` (forma + proveniência), `skills catalog` determinístico e `skills publish` idempotente (cópia/symlink, marcador, regra de versão, órfãs), com `scripts/publish-skills` | [spec](../specs/008-biblioteca-skills/spec.md) · [plan](../specs/008-biblioteca-skills/plan.md) · [ADR 0009](decisions/0009-biblioteca-de-skills.md) · [guia](guides/criar-publicar-skills.md) |

---

*Gerado por scaffold.py em 2026-09-18T18:56:11Z*
