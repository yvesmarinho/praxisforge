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
<!-- Modificado em: 24/09/2026 16:54 -->

# Nome da skill

## Como preencher este template

1. Copie `skills/_template/` para `skills/<nome>/` — o `<nome>` usa minúsculas, dígitos e hífens
   (até 64 caracteres) e **deve ser igual** ao campo `name`.
2. `description`: obrigatória, não vazia, até 1024 caracteres — é o que o Claude lê para decidir
   quando usar a skill.
3. `metadata.version`: obrigatória, em semver (`MAJOR.MINOR.PATCH`). **Incremente** a versão a cada
   mudança de conteúdo; a publicação por cópia recusa conteúdo alterado com a mesma versão.
4. `metadata.sources`: slugs dos registros em `src/data/sources/<categoria>/<slug>.md` que
   originaram a skill. Pelo menos uma fonte precisa ter `extract_policy` `summary` ou `verbatim`;
   fontes `link` entram só como referência complementar.
5. `metadata.authored: true`: use quando a skill é autoral (sem fontes). Nesse caso `sources` pode
   ficar vazio ou ser omitido.
6. Arquivos de apoio (exemplos, scripts, referências) ficam dentro da pasta da skill e são citados
   no corpo por link relativo, ex.: `[exemplo](exemplos/exemplo.md)`. Todo link relativo precisa
   existir e não pode sair da pasta; URLs externas são ignoradas.
7. Valide com `uv run praxisforge skills validate <nome>` e publique com
   `scripts/publish-skills <nome> --target global` (ou `--target <pasta-do-projeto>`).

Apague esta seção e escreva aqui as instruções da skill.
