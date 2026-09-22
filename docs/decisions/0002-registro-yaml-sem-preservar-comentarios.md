<!-- Criado em: 22/09/2026 10:15 -->
<!-- Modificado em: 22/09/2026 10:12 -->

# ADR 0002: Registro YAML sem preservar comentários, com escrita atômica

## Status

Aceito (22/09/2026)

## Contexto

`src/data/folders.yaml` é reescrito pela ferramenta a cada `add`/`update`.
FR-015 exige idempotência e diffs estáveis no git; FR-017 exige resistência a
falha no meio da escrita.

## Decisão

`PyYAML` (`safe_dump`, `sort_keys=True`, `allow_unicode=True`), gravando em
arquivo temporário no mesmo diretório e trocando com `os.replace` (atômico).
Comentários no YAML não são preservados — o arquivo é gerenciado pela
ferramenta, não editado manualmente. Leitura usa um `SafeLoader` próprio
(`NoTimestampSafeLoader`) sem o resolvedor implícito de timestamp, para que
`last_scanned`/`date` permaneçam `str` ISO 8601 (o schema exige `string`).

## Alternativas descartadas

- `ruamel.yaml` (preserva comentários): dependência nova fora do conjunto-chave
  da constituição, para um benefício (comentários) que não existe hoje no
  arquivo gerado.
- Reescrita direta do arquivo (sem temporário): não é atômica, arrisca
  corrupção em falha no meio da escrita.

## Consequências

- Diffs de `folders.yaml` no git são estáveis e ordenados por alias.
- Qualquer comentário manual adicionado ao arquivo é perdido na próxima
  gravação — documentado aqui para não surpreender.
