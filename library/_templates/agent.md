---
name: nome-do-agente
description: Quando delegar a este agente e o que ele entrega (até 1024 caracteres).
tools: Read, Grep, Glob
metadata:
  version: '0.1.0'
  sources: [slug-da-fonte]
  authored: false
---
<!-- Criado em: 25/09/2026 13:10 -->
<!-- Modificado em: 25/09/2026 13:10 -->

# Nome do agente

## Como preencher este template

- Copie para `library/agents/<nome>.md`; `name` **deve ser igual** ao `<nome>` do arquivo.
- `tools`: ferramentas liberadas ao agente (omita para herdar todas).
- `description`: obrigatória, até 1024 caracteres — o Claude a lê para decidir quando usar o item.
- `metadata.version`: semver; **incremente** a cada mudança de conteúdo (a publicação recusa conteúdo
  alterado com a mesma versão).
- `metadata.sources`: slugs dos registros em `src/data/sources/<categoria>/<slug>.md` cujas **ideias**
  originaram o item (nunca texto copiado, traduzido ou parafraseado de perto — ADR 0012).
- `metadata.authored: true`: item autoral, sem fontes (então `sources` pode ser omitido).
- Valide com `uv run praxisforge library validate --type agent <nome>`.
- Agent é arquivo único: não cite arquivos locais por link relativo.

Apague esta seção e escreva aqui o prompt de sistema do agente.
