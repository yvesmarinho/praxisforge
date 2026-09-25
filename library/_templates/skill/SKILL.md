---
name: nome-da-skill
description: Uma frase dizendo o que a skill faz e quando o Claude deve usá-la (até 1024 caracteres).
license: MIT
metadata:
  version: '0.1.0'
  sources: [slug-da-fonte]
  authored: false
---
<!-- Criado em: 24/09/2026 16:54 -->
<!-- Modificado em: 25/09/2026 13:11 -->

# Nome da skill

## Como preencher este template

1. Copie `library/_templates/skill/` para `library/skills/<nome>/` — o `<nome>` usa minúsculas,
   dígitos e hífens (até 64 caracteres) e **deve ser igual** ao campo `name`.
2. `description`: obrigatória, não vazia, até 1024 caracteres — é o que o Claude lê para decidir
   quando usar a skill.
3. `metadata.version`: obrigatória, em semver (`MAJOR.MINOR.PATCH`). **Incremente** a versão a cada
   mudança de conteúdo; a publicação por cópia recusa conteúdo alterado com a mesma versão.
4. `metadata.sources`: slugs dos registros em `src/data/sources/<categoria>/<slug>.md` cujas
   **ideias** originaram a skill — nunca texto copiado, traduzido ou parafraseado de perto
   (ADR 0012).
5. `metadata.authored: true`: use quando a skill é autoral (sem fontes). Nesse caso `sources` pode
   ficar vazio ou ser omitido.
6. `metadata.references: [<nome>]` (opcional): references de `library/references/` que a skill
   usa; elas são publicadas dentro da skill, em `references/<nome>.md`.
7. Arquivos de apoio (exemplos, scripts) ficam dentro da pasta da skill e são citados no corpo por
   link relativo, ex.: `[exemplo](exemplos/exemplo.md)`. Todo link relativo precisa existir e não
   pode sair da pasta; URLs externas são ignoradas.
8. Valide com `uv run praxisforge library validate --type skill <nome>` e publique num projeto com
   `scripts/publish-library --type skill <nome> --target <pasta-do-projeto>`.

Apague esta seção e escreva aqui as instruções da skill.
