<!-- Criado em: 22/09/2026 11:59 -->
<!-- Modificado em: 22/09/2026 11:49 -->

# Contrato de Interface: `praxisforge folders scan`

Esta feature não introduz nenhum schema JSON novo (nenhuma mudança em
`schemas/folders-schema-v1.json` — ver [research.md](../research.md), Decisão 2). O contrato
exposto ao usuário é a interface de linha de comando abaixo.

## `folders scan <alias>`

Varre uma única pasta registrada.

- **Entrada**: `alias` (posicional, obrigatório nesta forma) — deve casar com
  `^[a-z][a-z0-9_]{1,62}$` (mesma regra de `Alias`, feature 001).
- **Pré-condição**: alias já registrado (`folders add` executado antes).
- **Saída (sucesso, exit code 0)**: mensagem confirmando `alias`, `status` resultante e
  `last_scanned` (ISO 8601, timezone-aware); nenhum caminho absoluto.
- **Saída (falha, exit code 1)**: alias não registrado → mensagem citando o alias
  (`FolderNotFoundError`); caminho não resolve → mensagem citando o motivo
  (`FolderPathNotConfiguredError` | `FolderPathInvalidError` | `FolderPathUnreadableError`), sem
  alterar o registro.

## `folders scan --all`

Varre todas as pastas registradas em lote.

- **Entrada**: nenhuma (mutuamente exclusivo com o `alias` posicional, mesmo grupo de
  `folders resolve --all`).
- **Saída (exit code 0 se ≥ 0 falhas e o comando em si não erra)**: resumo com contagem de
  pastas atualizadas e de pastas com falha (FR-007); lista de falhas individuais
  (alias + motivo, FR-006); lista de grupos de aliases duplicados, se houver (FR-008/FR-009) —
  a presença de duplicidade é só informativa e não altera o exit code.
- **Garantia**: falha de uma pasta nunca impede a varredura das demais (FR-006).
- **Garantia de segurança**: nenhuma linha de saída contém caminho absoluto do sistema de
  arquivos, exceto quando citando o caminho de uma pasta especificamente na mensagem de erro
  daquela própria pasta (FR-010/SC-004, mesma regra da feature 001).

## Exit codes (reaproveitados da feature 001)

| Código | Significado |
|---|---|
| 0 | operação concluída (varredura individual ok, ou lote executado — mesmo com falhas de item) |
| 1 | falha de validação/negócio (alias inexistente, caminho não resolve) |
| 2 | uso incorreto da CLI (argumentos inválidos) |
| 3 | falha de ambiente (ex.: registro corrompido/ilegível) |
