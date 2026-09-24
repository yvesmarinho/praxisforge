<!-- Criado em: 24/09/2026 11:44 -->
<!-- Modificado em: 24/09/2026 11:44 -->

# Contrato CLI — feature 007

| Situação | Comportamento |
|---|---|
| qualquer comando sem `--registry` | usa o local resolvido (precedência no data-model) |
| `add`/`bootstrap` com registro ausente | cria a pasta e o registro no local resolvido |
| `list`/`show`/`update`/`resolve`/`scan`/`validate`/`migrate` com registro ausente | exit 1: `registro ausente em <local> — crie com folders add ou folders bootstrap` |
| idem, com `src/data/folders.yaml` antigo e não vazio no diretório atual | + linha no stderr: `registro antigo encontrado em src/data/folders.yaml — execute: praxisforge folders relocate` |
| `folders relocate [--from ARQ]` | valida a origem, move para o local resolvido; imprime `registro movido para <local> (N pastas)`; exit 0 |
| `relocate` com destino existente | exit 1: `já existe registro em <local>; nada foi alterado` |
| `relocate` com origem ausente | exit 1 (`RegistryFileNotFoundError` citando a origem) |
| `relocate` com origem v1/inválida | exit 1 (pede `folders migrate` / lista violações) |
| `relocate` com origem sem pastas (`folders: {}`) | exit 1: `registro de origem sem pastas; nada a mover` |
| local resolvido é diretório | exit 2 citando o local |
| sem permissão de escrita no destino | exit 3 citando o local; origem intacta |
| `relocate` com falha de I/O | exit 3; origem intacta |
