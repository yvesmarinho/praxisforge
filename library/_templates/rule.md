---
description: Quando esta regra vale e o que ela exige (até 1024 caracteres).
paths:
  - "src/**"
metadata:
  version: '0.1.0'
  sources: [slug-da-fonte]
  authored: false
---
<!-- Criado em: 25/09/2026 13:10 -->
<!-- Modificado em: 25/09/2026 13:10 -->

# Nome da regra

## Como preencher este template

- Copie para `library/rules/<nome>.md`; a rule **não** declara `name` (vale o nome do arquivo).
- `paths`: globs dos arquivos em que a regra se aplica; omita para valer sempre.
- `description`: obrigatória, até 1024 caracteres — o Claude a lê para decidir quando usar o item.
- `metadata.version`: semver; **incremente** a cada mudança de conteúdo (a publicação recusa conteúdo
  alterado com a mesma versão).
- `metadata.sources`: slugs dos registros em `src/data/sources/<categoria>/<slug>.md` cujas **ideias**
  originaram o item (nunca texto copiado, traduzido ou parafraseado de perto — ADR 0012).
- `metadata.authored: true`: item autoral, sem fontes (então `sources` pode ser omitido).
- Valide com `uv run praxisforge library validate --type rule <nome>`.
- Rule é arquivo único: não cite arquivos locais por link relativo.

Apague esta seção e escreva aqui a regra, curta e verificável.
