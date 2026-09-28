<!-- Criado em: 28/09/2026 15:09 -->
<!-- Modificado em: 28/09/2026 15:09 -->
# Cabeçalhos da feature 010 com horário adiantado

## Sintoma

Os cabeçalhos (`DATA`, `MODIFICADO`, `HISTÓRICO`) de 13 arquivos da feature 010 em `src/` e `tests/` tinham horários **posteriores** ao commit que os introduziu (até 15:45 para um commit feito às 15:11 de 25/09/2026). Em alguns casos, `DATA` também ficou posterior a `MODIFICADO`.

## Causa

Os horários foram estimados em vez de obtidos com `TZ=America/Sao_Paulo date`.

## Correção

- Os horários adiantados foram ajustados para o horário do commit que introduziu cada arquivo (`33d627d`/`8a7182f`: 15:06; `f2b801c`: 15:11).
- `MODIFICADO` foi atualizado para o horário da correção, e uma entrada foi acrescentada no histórico.
- Método de detecção: comparar cada horário do cabeçalho com `git log -1 --format=%cI <arquivo>`.

## Fora do escopo (registrado no TODO)

Há o mesmo problema em arquivos antigos: `specs/002-*`, `specs/003-*` e `docs/bugs/2026-09-24-ci-scan-escala-quadratica.md`.

## Lição

Nunca escrever horário em cabeçalho sem consultar o relógio do sistema.
