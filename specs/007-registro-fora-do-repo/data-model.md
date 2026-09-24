<!-- Criado em: 24/09/2026 11:44 -->
<!-- Modificado em: 24/09/2026 11:44 -->

# Data Model: Registro de pastas fora do repositório

O formato do registro não muda (`folders-schema-v2`). Mudam o **local** e os arquivos versionados.

## Local do registro (derivado)

| Fonte | Condição | Resultado |
|---|---|---|
| `--registry P` | informado | `P` (expandido/resolvido) |
| `PRAXISFORGE_REGISTRY` | definida e não vazia | valor (expandido/resolvido) |
| `XDG_CONFIG_HOME` | definida, não vazia e absoluta | `$XDG_CONFIG_HOME/praxisforge/folders.yaml` |
| fallback | sempre | `~/.config/praxisforge/folders.yaml` |

## Registro antigo (legado)

`<cwd>/src/data/folders.yaml` com `folders` não vazio. Só gera dica e é a origem padrão de
`folders relocate`.

## Registro de exemplo (versionado)

`src/data/folders.example.yaml`: `schema_version: "2"`, 3 pastas fictícias sob
`/srv/praxisforge/`; válido no contrato; nunca usado como padrão.

## Exceções

| Exceção | Base | Quando |
|---|---|---|
| `RegistryFileNotFoundError(location)` | `RegistryUnavailableError` (existente) | registro ausente no local resolvido; mensagem cita o local |
| `RegistryAlreadyExistsError(location)` | `PraxisForgeError` | `relocate` com destino já existente |
| `RegistryRelocationError(reason)` | `PraxisForgeError` | falha de I/O ao mover (origem preservada) |

## Estados do relocate

`origem válida + destino ausente` → movido (origem removida, destino idêntico) ·
`destino existe` → recusa, nada muda · `origem ausente/vazia/inválida/v1` → recusa, nada muda ·
`falha de I/O` → recusa, origem intacta, destino parcial removido.
