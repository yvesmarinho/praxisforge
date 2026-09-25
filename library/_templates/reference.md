---
name: nome-da-reference
description: O que este material de consulta cobre (checklist, guia, tabela).
metadata:
  version: '0.1.0'
  sources: [slug-da-fonte]
  authored: false
---
<!-- Criado em: 25/09/2026 13:10 -->
<!-- Modificado em: 25/09/2026 13:10 -->

# Nome da reference

## Como preencher este template

- Copie para `library/references/<nome>.md`; `name` **deve ser igual** ao `<nome>` do arquivo.
- References não são publicadas sozinhas: uma skill as cita em `metadata.references: [<nome>]` e
  elas vão dentro da skill publicada (`references/<nome>.md`).
- `description`: obrigatória, até 1024 caracteres — o Claude a lê para decidir quando usar o item.
- `metadata.version`: semver; **incremente** a cada mudança de conteúdo (a publicação recusa conteúdo
  alterado com a mesma versão).
- `metadata.sources`: slugs dos registros em `src/data/sources/<categoria>/<slug>.md` cujas **ideias**
  originaram o item (nunca texto copiado, traduzido ou parafraseado de perto — ADR 0012).
- `metadata.authored: true`: item autoral, sem fontes (então `sources` pode ser omitido).
- Valide com `uv run praxisforge library validate --type reference <nome>`.

Apague esta seção e escreva aqui o conteúdo de consulta.
