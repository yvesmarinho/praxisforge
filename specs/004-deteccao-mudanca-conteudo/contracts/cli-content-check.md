<!-- Criado em: 23/09/2026 11:35 -->
<!-- Modificado em: 23/09/2026 11:35 -->

# Contrato CLI — verificação de conteúdo

Exit codes inalterados: 0 ok, 1 validação, 3 ambiente (inclui `ContentInspectionError`).

## `praxisforge folders update <alias> --status curated`

- Pasta git: grava `last_curated_commit` = HEAD. Saída acrescenta
  `versão curada: <hash curto de 12 caracteres>`.
- Pasta não-git: status muda; saída acrescenta `versão curada: (pasta não é repositório git)`.
- Caminho não configurado/inacessível ou falha do git → exit 3, registro inalterado.
- Outros status: comportamento idêntico à feature 001 (git não é consultado).

## `praxisforge folders show <alias>`

- Nova linha `versão curada: <hash curto>` ou `versão curada: -`.

## `praxisforge folders scan <alias>` / `--all`

Nova linha/coluna `conteúdo` por pasta, com o rótulo pt-BR do `ContentCheck`:

| ContentCheck | Rótulo |
|---|---|
| not_applicable | `-` |
| not_git | `não verificado (não é repositório git)` |
| baseline_recorded | `referência registrada` |
| unchanged | `sem mudança` |
| reverted | `mudou — revertida para em curadoria` |

- Lote: resumo final acrescenta `revertidas: N` com os aliases revertidos.
- Falha do git no lote: item aparece na seção de falhas (`ItemFailure`), status inalterado.
- Nenhuma saída contém caminho absoluto (FR-013).
