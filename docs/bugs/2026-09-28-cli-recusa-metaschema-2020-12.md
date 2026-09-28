<!-- Criado em: 28/09/2026 16:31 -->
<!-- Modificado em: 28/09/2026 16:38 -->

# CLI `claude` recusa o `--json-schema` com `$schema` draft 2020-12

## Sintoma

No primeiro teste `live` da triagem (feature 011), toda chamada com um schema de `schemas/`
falhou com `Error: --json-schema is not a valid JSON Schema: no schema with key or ref
"https://json-schema.org/draft/2020-12/schema"` (exit 1). Com um schema sem `$schema`, a chamada
funcionava.

## Causa

O CLI valida o schema recebido com um metaschema próprio, que não conhece o draft 2020-12
declarado em todos os schemas do projeto. Os testes com o `claude` falso não pegavam o problema,
porque o falso não valida o schema.

## Correção

- O adapter (`infrastructure/claude_cli_model.py`) remove `$schema`, `$id` e `_meta` do schema
  **enviado ao CLI**. A validação local continua usando o schema completo, e é ela que vale
  (FR-007).
- Teste de regressão em `tests/integration/test_claude_cli_model.py` (o schema enviado não tem
  `$schema` nem `$id`).
- No mesmo teste `live`, o erro "Not logged in" aparecia como "sem mensagem": o CLI põe o motivo
  no campo `result` do JSON do stdout, e não no stderr. O adapter passou a usar esse campo quando o
  stderr está vazio.

## Achados seguintes (mesma sessão, primeira triagem real)

Depois dessa correção, a triagem real numa pasta pequena falhou nas 5 primeiras chamadas (o
disjuntor de falhas consecutivas parou a execução, como previsto):

1. **Modo estrito do CLI** (`strictTypes`): `minItems` sem `"type": "array"` no mesmo nó, dentro
   do `allOf`/`if`/`then` do `curation-triage-response-v1`. Correção no contrato (tipos explícitos
   nos subschemas condicionais, mesma semântica) e teste de contrato que aplica a regra estrita aos
   3 schemas de resposta.
2. **API**: o `input_schema` não aceita `allOf`/`anyOf`/`oneOf` na raiz. Correção no adapter: essas
   chaves também saem do schema enviado ao CLI; as regras condicionais continuam na validação
   local e no domínio. Teste de regressão no adapter.

Depois das correções, os três papéis (triagem, rascunho e juiz) funcionaram com o CLI real, e a
triagem da pasta pequena gravou 5 vereditos (US$ 0,08).

## Lição

Testes com dublê não substituem uma chamada real em integrações externas. O teste `live` agora é
passo obrigatório do quickstart e da ampliação da faixa de versões do CLI.
