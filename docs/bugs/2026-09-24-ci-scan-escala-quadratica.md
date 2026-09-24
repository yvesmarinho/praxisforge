<!-- Criado em: 24/09/2026 09:40 -->
<!-- Modificado em: 24/09/2026 09:40 -->

# CI: teste de escala da varredura estoura 30 s (PR #15)

## Sintoma

No PR #15 (feature 005), o job `Lint, tipagem, testes e validação de dados` falhou na
etapa de testes (o lint passou):

```
tests/integration/test_scan_content_scale.py:100: AssertionError
E       assert 35.53705819 < 30.0
```

Localmente o mesmo teste passava em 10,6 s; o runner do GitHub é cerca de 3× mais lento.

## Causa

Profile do `scan_all_folders` com 100 pastas (21,9 s com profiler ligado):

| Custo | Tempo | Origem |
|---|---|---|
| `repository.load()` por pasta (101×) | 13,4 s | `_aplicar_varredura` relia e validava o YAML inteiro |
| `repository.save()` por pasta (101×) | 6,1 s | `_aplicar_varredura` regravava o YAML inteiro |
| checagem de conflito de caminho (incluída acima) | 3,3 s | `FolderRegistry.__post_init__` compara pares a cada construção (feature 005) |
| git | ~2 s | esperado |

Reler e regravar o arquivo a cada pasta deixava o lote em O(n²). A checagem de caminho
único/sem aninhamento da 005, também O(n²) por construção, somou o suficiente para passar
do limite no CI.

## Correção

1. `scan_all_folders` carrega o registro uma vez, aplica cada varredura em memória e grava
   uma única vez ao fim (só se ao menos uma pasta foi varrida com sucesso).
   `_aplicar_varredura` passou a receber e devolver o `FolderRegistry`; `scan_folder`
   continua gravando logo após a sua varredura.
2. `_componentes` (domínio) com `functools.lru_cache`, evitando recalcular os componentes
   de cada caminho em cada comparação.

Efeito colateral aceito: se o processo morrer no meio do lote, nenhuma pasta dele é
persistida (antes, as já varridas ficavam gravadas). Falha por item continua isolada em
`failures`.

## Verificação

- Testes de regressão em `tests/unit/application/test_scan_folders.py`:
  `test_lote_carrega_e_grava_o_registro_uma_unica_vez` (vermelho antes da correção) e
  `test_lote_sem_nenhuma_pasta_ok_nao_grava`.
- Teste de escala: 10,6 s → 2,5 s localmente.
- `make lint` limpo; `make test`: 431 testes, cobertura 96,59%.
