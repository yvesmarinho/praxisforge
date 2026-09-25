<!-- Criado em: 24/09/2026 10:58 -->
<!-- Modificado em: 25/09/2026 12:40 -->

# ADR 0007: Política de extração por licença

## Status

**Substituído** pelo [ADR 0012](0012-fontes-so-ideias.md) em 25/09/2026. Aceito (24/09/2026) — feature `006-politica-extracao-licenca`.

## Contexto

O praxisforge compila informações de repositórios curados numa base de conhecimento **pública**:
todo extrato gravado em `src/data/sources/` é redistribuído. Citar o originador não concede
permissão de cópia — quem concede é a licença. O registro de fonte v1 tinha só um booleano
(`extract_allowed`), que não distinguia "posso resumir" de "posso copiar literalmente" nem ligava a
decisão à licença.

## Decisão

- Três níveis ordenados em `extract_policy`: `link` < `summary` < `verbatim`.
  - `link`: só referência e metadados (origem, licença, descrição curta).
  - `summary`: síntese com palavras próprias + citações curtas com autor e origem (amparo da
    citação para estudo/comentário: Lei 9.610/98, art. 46, III).
  - `verbatim`: cópia literal de trechos/arquivos, com aviso de copyright e texto da licença
    preservados (`notice_preserved: true`).
- Tabela única no domínio (`domain/license_policy.py`), comparação sem caixa:

  | Licença | Documentação | Código (ou escopo ausente) |
  |---|---|---|
  | MIT, BSD-3-Clause, Apache-2.0 | verbatim | verbatim |
  | GPL-3.0 | verbatim | summary (código copiado herdaria a GPL) |
  | Elastic-2.0 | summary | summary (licença não livre) |
  | unknown | link | link |
  | não classificada | link | link |

- A fonte pode declarar política mais restritiva que a máxima, nunca mais permissiva
  (`ExtractPolicyExceedsLicenseError`).
- Atribuição: `author` obrigatório em `summary`/`verbatim`; Apache-2.0 em `verbatim` exige
  declarar `modified` (`IncompleteAttributionError`).
- Licença fora da tabela vale `link`, **sem aviso** na validação; `folders show` indica
  "licença não classificada". Ampliar a tabela exige novo ADR.
- A licença da fonte é declarada de forma independente — não é conferida contra a pasta
  registrada.
- `source-schema-v2.json` (breaking, novo major); v1 é rejeitado pedindo `extract_policy`. Sem
  migração automática: não havia registros de fonte versionados.
- A validação de fontes saiu da CLI para o caso de uso `validate_sources` (schema v2 + entidade),
  e `make validate-data` passa a validar `src/data/sources/` quando o diretório existir.

## Consequências

- Nenhum extrato acima do permitido passa pela validação local nem pelo CI.
- A validação confere os campos **declarados**; não detecta trechos copiados no corpo.
- Esta regra é orientação técnica de conformidade, **não** aconselhamento jurídico.

## Alternativas rejeitadas

- Tabela codificada no JSON Schema (`if/then`): duplicaria a regra e daria mensagens ruins.
- Converter `extract_allowed: true` em `verbatim`: inferiria a política mais permissiva.
- Rejeitar licença não classificada: travaria a curadoria sem ganho de segurança (`link` não copia).
