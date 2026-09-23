<!-- Criado em: 23/09/2026 17:04 -->
<!-- Modificado em: 23/09/2026 17:04 -->

# `folders update` regravava a versão curada ao editar outro campo

## Contexto

Feature 004 (`last_curated_commit`), detectado durante a feature 005
(`005-caminho-absoluto-registro`), ao escrever o teste de FR-016
(`update --path` deve preservar a versão curada).

## Sintoma

Em uma pasta já `curated`, qualquer `folders update` que **não** mudasse o
status (ex.: `--license`, `--last-scanned`, `--path`) consultava o git e
sobrescrevia `last_curated_commit` com o HEAD atual — marcando como revisado um
conteúdo que ninguém revisou e escondendo a mudança da varredura seguinte.

## Causa raiz

`update_folder()` decidia gravar a versão pelo status **resultante**
(`updated_registry.get(alias).status is CURATED`) em vez do ato explícito de
marcar `--status curated`.

## Correção

- Teste de regressão primeiro (vermelho confirmado):
  `tests/unit/application/test_update_folder.py::test_update_de_licenca_em_pasta_curada_nao_regrava_versao`.
- `src/praxisforge/application/update_folder.py`: a versão só é gravada quando o
  status informado na chamada é `curated` (`status is CurationStatus.CURATED`).

## Impacto

Registros que passaram por `update` sem mudar status em pastas curadas entre as
features 004 e 005 podem ter `last_curated_commit` mais novo que a revisão real.
Não há como reconstruir o valor original; se houver dúvida, remarcar a pasta como
`in_curation` e revisá-la de novo.
