<!-- Criado em: 23/09/2026 13:03 -->
<!-- Modificado em: 23/09/2026 15:39 -->

# Research: Caminho absoluto no registro de pastas

## R1 — Onde validar o caminho
- **Decision**: Domain valida só a **forma** (string absoluta começando com "/", sem segmento "..",
  sem "~", sem barra final, não vazia); `FilesystemFolderLocator` faz `expanduser` + `resolve(strict=True)`
  (canonização, links resolvidos) e checa diretório/legibilidade.
- **Rationale**: Domain sem I/O (constituição I); canonização depende do disco.
- **Alternatives**: validar tudo no Domain com `Path.resolve` (I/O no Domain — rejeitado).

## R2 — Porta substituta de PathResolver
- **Decision**: `FolderLocator` com `canonicalize(alias: str, raw: str) -> Path` (registro/update/migração) e
  `check(alias: str, path: Path) -> Path` (resolve/scan/curated). `PathResolver` e `EnvPathResolver`
  removidos; leitura de `PRAXISFORGE_FOLDER_<ALIAS>` sobrevive só em `LegacyPathSource.lookup(alias)`
  (migração, Q1).
- **Rationale**: FR-008 (única fonte = registro); mantém exceções semânticas já existentes
  (`FolderPathInvalidError`, `FolderPathUnreadableError`) para pasta movida/sem permissão.

## R3 — Contrato
- **Decision**: `folders-schema-v2.json` = v1 + `path` obrigatório (`type: string`, `pattern: "^/"`,
  `minLength: 2`) e `schema_version: const "2"`; unicidade de `path` é invariante de domínio
  (JSON Schema não expressa unicidade entre valores de propriedades de um objeto).
- `YamlFolderRegistryRepository.load()` com `schema_version: "1"` → `RegistryMigrationRequiredError`
  (exit 1, mensagem "execute praxisforge folders migrate"). `load_raw()` continua lendo qualquer versão.
- `add` em registro inexistente cria direto em v2.

## R4 — Alias do bootstrap (Q2 + clarify)
- **Decision**: `alias = f"{slug(raiz.name)}__{slug(sub.name)}"`; se ocupado por **outro caminho**,
  sufixo `_2`, `_3`…; se > 63 caracteres, trunca a parte da subpasta preservando `<raiz>__` e sufixo.
  Slug vazio/iniciando com dígito → prefixo `p`. Raízes de mesmo nome se distinguem pelo sufixo.
  Subpastas em ordem alfabética (determinismo).
- Idempotência por caminho canônico: subpasta cujo caminho já está registrado é "existente"
  (ou "ignorada" se `status: ignore`), independentemente do alias.

## R5 — Migração (Q1)
- **Decision**: `migrate_registry(repository, legacy, locator, root: Path | None)`: lê v1 via
  `load_raw`; para cada alias: (1) `legacy.lookup(alias)`; (2) subpasta de `root` cujo
  `slug(nome) == alias` (0 ou >1 candidatos → pendência); canoniza e checa unicidade. Grava v2
  **somente se** não houver pendência (atômico, FR-011); v2 de entrada → no-op (idempotente).
  Preserva alias e todos os campos (inclui `last_curated_commit`).
- Aliases antigos do bootstrap (sem prefixo de raiz) são preservados (FR-015).

## R6 — Saídas
- `list` ganha coluna de caminho; `show` linha `caminho:`; `resolve` já imprime o caminho;
  `scan`/`bootstrap`/`migrate` e logs só com alias (FR-012). Erros sobre um item podem citar o
  caminho apenas quando o próprio caminho é o problema (inexistente/sem permissão/duplicado).

## R7 — Aninhamento e maiúsculas (checklist identidade-pasta)
- **Decision**: comparação por `str(path).casefold()`; aninhamento = um caminho é igual ao outro +
  "/" + resto (checagem de prefixo por componentes, não por string crua).
- Migração: entrada cujo path é ancestral de ≥ 1 outra entrada é removida e listada em
  `removed_roots` (FR-017) antes da checagem de unicidade.
