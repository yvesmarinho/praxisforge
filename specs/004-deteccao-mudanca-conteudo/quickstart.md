<!-- Criado em: 23/09/2026 11:35 -->
<!-- Modificado em: 23/09/2026 11:35 -->

# Quickstart: validação ponta a ponta da feature 004

Pré-requisitos: `uv sync`, `git` ≥ 2.x, registro de teste isolado (ver quickstart da 001 §1).

## Cenário 1 — marcar curada grava a versão (US1)

1. Criar repositório de teste em pasta temporária com 1 commit; registrar com alias `demo` e
   exportar `PRAXISFORGE_FOLDER_DEMO`.
2. `praxisforge folders update demo --status curated` → saída com `versão curada: <hash>`.
3. `praxisforge folders show demo` → mesmo hash. **Esperado**: `folders.yaml` contém `last_curated_commit`.

## Cenário 2 — mudança dentro da pasta reverte (US2)

1. Novo commit alterando arquivo dentro da pasta.
2. `praxisforge folders scan demo` → `conteúdo: mudou — revertida para em curadoria`; status `em curadoria`.

## Cenário 3 — subpasta: mudança fora não reverte (Clarificação Q3)

1. Registrar `sub` apontando para uma subpasta do repositório; marcar curada.
2. Commit alterando arquivo **fora** da subpasta; `folders scan sub` → `sem mudança`, continua curada.

## Cenário 4 — legado sem referência (US3)

1. Editar o YAML removendo `last_curated_commit` de uma pasta curada.
2. `folders scan <alias>` → `referência registrada`; novo commit + novo scan → revertida.

## Cenário 5 — lote com falha e ignore

1. Lote com pasta curada alterada, inalterada, `ignore`, não-git e uma com `git` indisponível
   (ex.: `PATH` sem git só para o teste de integração).
2. `folders scan --all` → só a alterada revertida; `ignore` pulada; falha por item reportada.

## Verificações de fechamento

- `make lint`, `make test` (cobertura ≥ 90%), `make validate-data`, `make security`.
- Nenhum caminho absoluto na saída dos cenários acima.
- Registro antigo (sem o campo) valida sem alteração (SC-004).
