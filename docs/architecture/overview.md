<!-- Criado em: 22/09/2026 10:11 -->
<!-- Modificado em: 22/09/2026 16:45 -->

# Arquitetura — Feature 001: Registro de Pastas a Curar e Contratos Versionados

> **Feature 002 (Varredura das Pastas Registradas)**: reaproveita 100% as camadas e portas
> abaixo, sem nenhuma mudança estrutural. Adiciona só `application/scan_folders.py` (casos de
> uso `scan_folder`/`scan_all_folders`, com detecção de aliases duplicados no lote) e o
> subcomando `folders scan` em `presentation/cli.py`. Ver `specs/002-varredura-pastas-curadoria/
> plan.md` e `research.md` para as decisões de design.
>
> **Feature 003 (Bootstrap do Registro de Pastas)**: mudança mínima de Domain/contrato (sexto
> valor de `CurationStatus`, `ignore`, e invariante relaxada, aditiva — mesmo
> `folders-schema-v1.json`), uma porta nova (`RootFolderProbe`) e seu adapter
> (`FilesystemFolderProbe`), o caso de uso `application/bootstrap_folders.py`, e o subcomando
> `folders bootstrap`. `folders scan --all` (feature 002) passa a pular pastas `ignore`. Ver
> `specs/003-bootstrap-registro-pastas/plan.md` e `research.md`.

## Camadas

O código em `src/praxisforge/` segue arquitetura em quatro camadas, com regras de
dependência verificadas automaticamente por `tests/architecture/` (AST, sem
dependência nova — ver [ADR 0003](../decisions/0003-verificacao-de-camadas-por-ast.md)):

```text
Presentation (cli.py)
   ↓ (+ Infrastructure só no ponto de composição, cli.py)
Application (casos de uso, DTOs, portas)
   ↓
Domain (entidades, value objects, exceções — Python puro)

Infrastructure (adapters) → depende de Domain + Application
```

- **Domain** (`domain/`): `Alias`, `CurationStatus`, `Folder`, `FolderRegistry`,
  `SourceRecord`, hierarquia de exceções (`errors.py`). Só stdlib; sem `logging`;
  sem libs externas ([ADR 0001](../decisions/0001-domain-sem-pydantic.md)).
- **Application** (`application/`): casos de uso (`register_folder`,
  `query_folders`, `update_folder`, `resolve_folder_path`, `validate_registry`),
  DTOs pydantic de entrada (`dto.py`), portas (`ports.py`:
  `FolderRegistryRepository`, `PathResolver`, `ContractValidator`), reexportação
  de erros para a Presentation (`errors.py`) e logging estruturado próprio
  (`logging_events.py`, duplicado do de Infrastructure para não depender dela).
- **Infrastructure** (`infrastructure/`): adapters reais —
  `yaml_folder_registry.py` (repositório YAML, escrita atômica), `env_path_resolver.py`
  (resolve `PRAXISFORGE_FOLDER_<ALIAS>`), `jsonschema_validator.py` (Draft 2020-12
  com `FormatChecker`), `source_frontmatter.py` (leitor de frontmatter),
  `logging_setup.py` (formatter JSON), `yaml_loader.py` (SafeLoader compartilhado
  sem resolvedor de timestamp).
- **Presentation** (`presentation/cli.py`): CLI `argparse`; único ponto que
  importa Infrastructure (composição das dependências); converte exceções em
  mensagens pt-BR e códigos de saída.

## Fluxo dos casos de uso

1. **Registrar** (`folders add`): CLI → `RegisterFolderInput` (DTO valida forma) →
   `register_folder` → `FolderRegistry.add` (invariantes de domínio) →
   `YamlFolderRegistryRepository.save` (escrita atômica).
2. **Consultar** (`folders list|show`): CLI → `query_folders.list_folders`/`show_folder`
   → `repository.load()` (valida contrato + reconstrói entidades) → `FolderRegistry.list/get`.
3. **Atualizar** (`folders update`): CLI → `UpdateFolderInput` → `update_folder` →
   `FolderRegistry.update` (atômico: tudo ou nada) → `save`.
4. **Resolver caminho** (`folders resolve`): CLI → `resolve_folder_path`/`resolve_all_folder_paths`
   → confere o alias no registro → `EnvPathResolver.resolve` (variável de ambiente,
   segue link simbólico, valida permissão).
5. **Validar** (`folders validate`, `sources validate`): CLI →
   `validate_registry`/leitura direta de frontmatter → `JsonSchemaContractValidator`
   por item, agregando falhas em `BatchReport`/`FoldersBatchReport` sem interromper o lote.

## Validação em duas etapas (FR-009, constituição II)

1. **Contrato** (`JsonSchemaContractValidator`): JSON Schema Draft 2020-12 com
   `FormatChecker`, reporta **todas** as violações de uma vez.
2. **Domínio**: construção de `Folder`/`FolderRegistry`/`SourceRecord` garante
   invariantes que o schema não expressa (unicidade de alias, coerência entre campos).

## Decisões arquiteturais centrais

Ver ADRs em `docs/decisions/`. Resumo:

- Domain sem `pydantic`; pydantic só na fronteira Application/CLI.
- Registro YAML gerenciado pela ferramenta, sem preservar comentários; escrita
  atômica (arquivo temporário + `os.replace`).
- Loader YAML customizado (`NoTimestampSafeLoader`) sem o resolvedor implícito
  de timestamp, para que datas permaneçam `str` ISO 8601 (o schema exige `string`
  com `format: date-time`/`date`).
- Guarda de camadas por AST em `tests/architecture/`, sem dependência nova
  (alternativa a `import-linter`).
- `update` de pasta aceita `license` além de `status`/`last_scanned`, para que
  uma pasta com licença `unknown` (como `github_forks`) não fique presa em
  `pending`.

## Achado real do guarda de arquitetura

Durante a implementação, `tests/architecture/test_layer_rules.py` detectou duas
violações reais: Application importando `infrastructure.logging_setup` (log
estruturado) e `presentation/cli.py` importando `domain.curation_status`/`domain.errors`
diretamente. Corrigido com `application/logging_events.py` (log duplicado,
só stdlib) e `application/errors.py` (reexportação de exceções), sem afrouxar
a matriz de dependências — confirmando o valor do guarda automatizado (US4).

## Mapa de módulos

| Módulo | Responsabilidade |
|--------|-------------------|
| `domain/errors.py` | Hierarquia `PraxisForgeError` e `Violation` |
| `domain/alias.py` | Value object `Alias` |
| `domain/curation_status.py` | Enum `CurationStatus` |
| `domain/folder.py` | Entidade `Folder` |
| `domain/folder_registry.py` | Agregado `FolderRegistry` |
| `domain/source_record.py` | Entidade `SourceRecord` (proveniência) |
| `application/ports.py` | Portas (Dependency Inversion) |
| `application/dto.py` | DTOs pydantic de entrada |
| `application/register_folder.py` | Caso de uso: registrar |
| `application/query_folders.py` | Casos de uso: listar/consultar |
| `application/update_folder.py` | Caso de uso: atualizar |
| `application/resolve_folder_path.py` | Casos de uso: resolver caminho (individual/lote) |
| `application/scan_folders.py` | Casos de uso: varrer pasta (individual/lote) + detectar aliases duplicados (feature 002); pula pastas `ignore` no lote (feature 003) |
| `application/bootstrap_folders.py` | Caso de uso: gerar registro inicial a partir de uma pasta-raiz (feature 003) |
| `application/validate_registry.py` | Caso de uso: validar registro em lote |
| `application/logging_events.py` | Log estruturado (versão Application) |
| `application/errors.py` | Reexportação de erros para Presentation |
| `infrastructure/yaml_folder_registry.py` | Adapter do repositório (YAML) |
| `infrastructure/env_path_resolver.py` | Adapter do resolvedor de caminho |
| `infrastructure/jsonschema_validator.py` | Adapter do validador de contrato |
| `infrastructure/source_frontmatter.py` | Leitor de frontmatter de fontes |
| `infrastructure/logging_setup.py` | Configuração de logging (formatter JSON) |
| `infrastructure/yaml_loader.py` | `SafeLoader` compartilhado |
| `infrastructure/filesystem_folder_probe.py` | Adapter que lista subpastas e extrai description/license via filesystem (feature 003) |
| `presentation/cli.py` | CLI `praxisforge` |
