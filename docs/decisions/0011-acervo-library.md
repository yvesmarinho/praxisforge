<!-- Criado em: 25/09/2026 12:40 -->
<!-- Modificado em: 25/09/2026 12:40 -->

# ADR 0011: Acervo `library/` por tipo de recurso

## Status

Aceito (25/09/2026). Substitui o [ADR 0009](0009-biblioteca-de-skills.md). Origem: debate
`docs/debates/curadoria-automatizada.md` e feature `009-acervo-library`; constituição v4.0.0
(Princípio VI).

## Contexto

A curadoria do `agent_skills` mostrou que um repositório de referência traz muito mais do que skills:
commands, agents, hooks, rules, references e instruções de projeto. O acervo só aceitava skills
(`skills/`) e publicava também no escopo global do usuário. A decisão do curador é que o praxisforge
é uma base de conhecimento agnóstica e que nada vai para o escopo global.

## Decisão

- **Estrutura**: `library/` com `skills/`, `commands/`, `agents/`, `hooks/`, `rules/` e `references/`,
  mais `INDEX.md` (gerado, determinístico) e `_templates/` (um por tipo). `skills/` é migrado por
  `git mv`, preservando o histórico.
- **Formatos**: Markdown com frontmatter no formato que o Claude Code lê. Metadados do praxisforge
  sempre sob `metadata` (`version`, `sources`, `authored`, `rewrite_pending` e, só em skills,
  `references`). Hooks ficam numa pasta com `HOOK.md` (`event`, `matcher`, `run`) e os scripts.
- **Contratos**: um JSON Schema por tipo, versionado pelo nome do arquivo
  (`<tipo>-frontmatter-v1.json`). **Exceção registrada ao Princípio II**: o frontmatter dos itens não
  carrega `schema_version`, porque o formato é do Claude Code (mesmo precedente do ADR 0009).
- **Publicação**: só em pastas de projeto; skills, commands, agents e rules. Hooks e references
  não são publicáveis (references vão dentro da skill que as cita). O alvo `global` é removido.
- **Marcador**: `library-publication-v1` (`kind`, `name`, `version`, `content_sha256`, `source`); em
  skill continua `.praxisforge-skill.json`; em arquivo único vira `.<nome>.md.praxisforge.json` ao
  lado. O marcador `skill-publication-v1` continua reconhecido e é regravado sem tocar no conteúdo.
- **CLI**: `library validate|index|publish`; `skills ...` sai com erro de uso indicando o equivalente.

## Alternativas descartadas

- Manter `skills/` e criar diretórios irmãos na raiz: espalha o acervo e complica o índice.
- Converter commands/agents/hooks em skills: perde o formato nativo de cada tipo.
- Manifesto único de publicação no projeto: ponto de corrupção compartilhado.

## Consequências

- Todos os comandos e testes da 008 migram para o acervo; `scripts/publish-skills` vira
  `scripts/publish-library`.
- Publicações globais anteriores (não existiam em 25/09/2026) seriam removidas à mão.
