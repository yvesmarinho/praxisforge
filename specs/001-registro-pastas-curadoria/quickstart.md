<!-- Criado em: 21/09/2026 15:59 -->
<!-- Modificado em: 21/09/2026 16:01 -->

# Quickstart — validar a feature 001 ponta a ponta

Pré-requisitos: `uv sync` executado; branch `001-registro-pastas-curadoria`.
Contratos: [contracts/](contracts/) · Modelo: [data-model.md](data-model.md).

## 1. Gates de qualidade

```bash
make lint && make test && make validate-data && make security
```

Esperado: ruff e mypy sem erros; pytest verde com cobertura ≥ 90%, incluindo
`tests/architecture` (regras de camadas).

## 2. Registro inicial válido

```bash
uv run praxisforge folders validate
uv run praxisforge folders list
```

Esperado: código 0; `github_forks` listada com licença `unknown` e status `pending`, sem
caminho absoluto na saída.

## 3. Registrar, repetir e recusar duplicado (US1)

```bash
uv run praxisforge folders add --alias exemplo --description "Pasta de teste" \
  --content-type documents --license MIT --status not_scanned      # código 0
uv run praxisforge folders add --alias exemplo --description "Pasta de teste" \
  --content-type documents --license MIT --status not_scanned      # "inalterado", código 0
uv run praxisforge folders add --alias exemplo --description "Outra" \
  --content-type documents --license MIT --status not_scanned      # código 1, alias duplicado
```

## 4. Resolver o caminho por ambiente (US2)

```bash
export PRAXISFORGE_FOLDER_GITHUB_FORKS="$HOME/DevOps/github_forks"
uv run praxisforge folders resolve github_forks                    # código 0
unset PRAXISFORGE_FOLDER_GITHUB_FORKS
uv run praxisforge folders resolve github_forks                    # código 3, variável ausente
uv run praxisforge folders resolve --all                             # resumo N ok, M com falha
```

## 5. Contratos inválidos (US3)

Casos cobertos por `tests/contract/`: sem `schema_version`, versão `"2"`, campo obrigatório
ausente, licença `unknown` com status diferente de `pending`, alias com maiúsculas, caminho
absoluto no lugar do alias, fonte `pending` com `extract_allowed: true`. Cada um deve ser
rejeitado listando campo e motivo; um lote com uma pasta inválida valida as demais.

## 6. Camadas (US4)

Introduzir temporariamente `import yaml` em `src/praxisforge/domain/`; `make test` deve
falhar em `tests/architecture` citando módulo, import e regra. Remover e confirmar verde.

## 7. Nenhum caminho pessoal versionado (SC-005)

```bash
git grep -nE "/home/|/Users/" -- src schemas specs ':!specs/**/quickstart.md'
```

Esperado: nenhuma ocorrência.
