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

---

*Gerado por scaffold.py em 2026-09-18T18:56:11Z*
