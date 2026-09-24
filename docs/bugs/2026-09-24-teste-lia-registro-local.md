<!-- Criado em: 24/09/2026 14:39 -->
<!-- Modificado em: 24/09/2026 14:39 -->

# Teste de contrato dependia do registro local fora do versionamento (feature 007)

## Sintoma

Depois de realocar o registro real para `~/.config/praxisforge/folders.yaml` (`folders relocate`),
`make test` passou a falhar:

```
FAILED tests/contract/test_folders_schema_v2.py::test_registro_versionado_atual_valida_na_v2
FileNotFoundError: ... src/data/folders.yaml
```

## Causa

O teste (feature 005) validava `src/data/folders.yaml` como "registro versionado". A feature 007
tirou esse arquivo do versionamento (`git rm --cached` + `.gitignore`). Durante a implementação o
teste continuava verde só porque a cópia local do curador ainda existia no disco — no CI (clone
limpo) ele falharia.

## Correção

O teste passou a validar o registro versionado atual, `src/data/folders.example.yaml`.

## Verificação

- `make test`: 618 testes, cobertura 97,86%, com o registro real já no local padrão e sem
  `src/data/folders.yaml` no disco (mesma condição do CI).
- Lição: rodar os gates também **sem** arquivos ignorados presentes antes de abrir o PR.
