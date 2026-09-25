---
description: Uma frase dizendo o que o comando faz e quando usá-lo (até 1024 caracteres).
argument-hint: "[argumento]"
metadata:
  version: '0.1.0'
  sources: [slug-da-fonte]
  authored: false
---
<!-- Criado em: 25/09/2026 13:10 -->
<!-- Modificado em: 25/09/2026 13:10 -->

# Nome do comando

## Como preencher este template

- Copie para `library/commands/<nome>.md`: o `<nome>` (minúsculas, dígitos e hífens, até 64
  caracteres) é o próprio comando (`/<nome>`); o command **não** declara `name`.
- `description`: obrigatória, até 1024 caracteres — o Claude a lê para decidir quando usar o item.
- `metadata.version`: semver; **incremente** a cada mudança de conteúdo (a publicação recusa conteúdo
  alterado com a mesma versão).
- `metadata.sources`: slugs dos registros em `src/data/sources/<categoria>/<slug>.md` cujas **ideias**
  originaram o item (nunca texto copiado, traduzido ou parafraseado de perto — ADR 0012).
- `metadata.authored: true`: item autoral, sem fontes (então `sources` pode ser omitido).
- Valide com `uv run praxisforge library validate --type command <nome>`.
- Command é arquivo único: não cite arquivos locais por link relativo (eles não iriam na publicação).

Apague esta seção e escreva aqui o prompt do comando (`$ARGUMENTS` recebe os argumentos).
