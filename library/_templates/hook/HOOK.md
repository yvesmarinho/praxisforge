---
name: nome-do-hook
description: O que o hook faz e por que (até 1024 caracteres).
event: PostToolUse
matcher: "Edit|Write"
run:
  - run.sh
metadata:
  version: '0.1.0'
  sources: [slug-da-fonte]
  authored: false
---
<!-- Criado em: 25/09/2026 13:10 -->
<!-- Modificado em: 25/09/2026 13:10 -->

# Nome do hook

## Como preencher este template

- Copie a pasta para `library/hooks/<nome>/`; `name` **deve ser igual** a `<nome>`.
- `event`: um de PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop, SessionStart,
  SessionEnd, Notification ou PreCompact.
- `matcher`: ferramentas que disparam o hook (opcional; vale para eventos de ferramenta).
- `run`: arquivos da pasta que o hook executa; todos precisam existir (versionados com `+x`).
- `description`: obrigatória, até 1024 caracteres — o Claude a lê para decidir quando usar o item.
- `metadata.version`: semver; **incremente** a cada mudança de conteúdo (a publicação recusa conteúdo
  alterado com a mesma versão).
- `metadata.sources`: slugs dos registros em `src/data/sources/<categoria>/<slug>.md` cujas **ideias**
  originaram o item (nunca texto copiado, traduzido ou parafraseado de perto — ADR 0012).
- `metadata.authored: true`: item autoral, sem fontes (então `sources` pode ser omitido).
- Valide com `uv run praxisforge library validate --type hook <nome>`.
- Hooks **não** são publicados: para usar num projeto, copie o script para `.claude/hooks/` e
  registre-o em `.claude/settings.json` (evento, matcher e comando), como descrito abaixo.

Apague esta seção e explique aqui o que o hook faz e como ligá-lo.
