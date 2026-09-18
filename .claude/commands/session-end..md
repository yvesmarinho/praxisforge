---
mode: agent
description: Ritual de encerramento de sessão. Execute ao finalizar o trabalho do dia.
---

# 🏁 Session End — Ritual de Encerramento de Sessão

> Use este ritual ao final da sessão.

## Execução

1. Rode o encerramento automático:

```bash
python scripts/session-manager.py --json end
```

2. Interprete o retorno:
   - `workspace_security.clean`
   - `session_docs_security.clean`
   - `daily_validation.valid`
   - `doc_updates`
   - `git`

3. Se o usuário quiser publicar o encerramento no repositório, execute:

```bash
python scripts/session-manager.py --json end --commit --push
```

4. Se `workspace_security.clean == false` ou `session_docs_security.clean == false`, pare antes de commitar.

5. Continue usando os validadores normais de código/infra quando houver mudanças fora da documentação.

## Referências

- Scan isolado: `python scripts/session-manager.py --json security-scan`
- Status rápido: `python scripts/session-manager.py --json status`
- Guia canônico: `docs/guides/SESSION_DOCS_STYLE_GUIDE.md`
