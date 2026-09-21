<!-- Criado em: 21/09/2026 16:20 -->
<!-- Modificado em: 21/09/2026 16:12 -->

---

description: "Tasks — 001-registro-pastas-curadoria"

---

# Tasks: Registro de Pastas a Curar e Contratos Versionados

**Input**: Design documents from `/specs/001-registro-pastas-curadoria/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: OBRIGATÓRIOS (constituição III — Test-First, NON-NEGOTIABLE). Em cada fase a ordem é: testes de falha → confirmar vermelho → implementação → verde. Implementação escrita antes dos testes deve ser descartada.

**Organization**: agrupadas por user story; cada fase é um incremento testável de forma independente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência em tarefa incompleta)
- **[Story]**: US1–US4 (mapeia para as user stories da spec)
- Caminhos relativos à raiz do repositório

## Convenções de código (valem para toda tarefa que cria/edita `.py`)

- Cabeçalho `# -*- coding: utf-8 -*-` + docstring de programa (NOME, TITULO, DATA, MODIFICADO, VERSÃO, DEPEND, HISTÓRICO, STATUS); datas do sistema em `America/Sao_Paulo`
- Type hints em parâmetros e retornos; docstrings reST (`:param:`, `:return:`); `pathlib`; imports seletivos
- Sem `print()`: a CLI escreve com `sys.stdout.write`/`sys.stderr.write`; logs via `logging`
- Domain: só stdlib, sem `logging`; `try/except` só nas fronteiras (CLI, I/O, serialização), exceções específicas
- Nenhum caminho absoluto em código, YAML, logs ou mensagens (exceto a saída de `folders resolve`)
- Ao concluir cada grupo: `make lint && make test` verdes antes de seguir

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: esqueleto das camadas, fixtures e validação de dados

- [ ] T001 Criar os subpacotes com `__init__.py` documentado: `src/praxisforge/domain/`, `src/praxisforge/application/`, `src/praxisforge/infrastructure/`, `src/praxisforge/presentation/`; e os diretórios `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/architecture/`, `schemas/`, `src/data/`
- [ ] T002 [P] Criar `tests/conftest.py` com fixtures: `tmp_registry_path` (arquivo YAML em `tmp_path`), `env_folder` (define/limpa `PRAXISFORGE_FOLDER_*` via `monkeypatch`), `valid_folder_doc` (dict válido) e `fixed_now` (relógio fixo `America/Sao_Paulo`)
- [ ] T003 [P] Criar `.yamllint.yaml` (regras `relaxed`, linha até 120) e o alvo `validate-data` no `Makefile` que roda `uv run yamllint src/data` e `uv run check-jsonschema --schemafile schemas/folders-schema-v1.json src/data/folders.yaml`
- [ ] T004 [P] Criar `tests/unit/application/` e `tests/unit/domain/` (com `__init__.py` se necessário) e confirmar que `make test` continua verde com os testes existentes

**Checkpoint**: estrutura pronta; `make lint && make test` verdes.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: contratos, exceções, entidades de domínio, portas e validador — bloqueiam todas as user stories

**⚠️ CRITICAL**: nenhuma user story começa antes desta fase.

### Testes primeiro (vermelho)

- [ ] T005 [P] Escrever `tests/unit/domain/test_errors.py`: hierarquia de `data-model.md` (todas derivam de `PraxisForgeError`; `ContractValidationError` carrega lista de `Violation(field, reason)`; `UnsupportedSchemaVersionError` informa versão encontrada e suportadas; mensagens não contêm caminho absoluto)
- [ ] T006 [P] Escrever `tests/unit/domain/test_alias.py`: rejeita vazio, só espaços, maiúsculas, começa com dígito, `/`, `..`, 1 ou 64+ caracteres → `InvalidAliasError`; aceita `github_forks`; `env_var_name` = `PRAXISFORGE_FOLDER_GITHUB_FORKS`
- [ ] T007 [P] Escrever `tests/unit/domain/test_curation_status.py`: cinco valores exatos, conversão de string inválida → erro semântico, rótulos pt-BR
- [ ] T008 [P] Escrever `tests/unit/domain/test_folder.py`: descrição vazia e com 501 caracteres, `content_type` fora do slug, licença vazia, licença `unknown` com status ≠ `pending` → `UnknownLicenseRequiresPendingError`, `not_scanned` com `last_scanned` preenchido, `last_scanned` futuro → `FutureScanDateError`, `last_scanned` sem timezone; caso feliz apenas acompanhado dos de falha
- [ ] T009 Escrever `tests/unit/domain/test_folder_registry.py`: `add` novo; `add` idêntico é no-op (idempotente); `add` com dados diferentes → `AliasAlreadyRegisteredError` sem alterar o agregado; `get` inexistente → `FolderNotFoundError`; `update` de status/`last_scanned`/`license` atômico (mudança inválida não altera nada); `schema_version` diferente de `"1"` → `UnsupportedSchemaVersionError`; `list` ordenado por alias
- [ ] T010 [P] Escrever `tests/contract/test_folders_schema.py`: valida `schemas/folders-schema-v1.json` (metaschema) e casos válidos/inválidos da spec (sem `schema_version`, versão `"2"`, campo ausente, alias maiúsculo, alias que é caminho absoluto, licença `unknown` com status ≠ `pending`, `not_scanned` com data, status fora do conjunto)
- [ ] T011 [P] Escrever `tests/contract/test_source_schema.py`: valida `schemas/source-schema-v1.json` (metaschema) e casos: campos obrigatórios ausentes, `origin` com caminho absoluto, `unknown` + `active`, `pending` + `extract_allowed: true`, data inválida
- [ ] T012 [P] Escrever `tests/contract/test_schemas_match_contracts.py`: `schemas/*.json` idênticos (ignorando `_meta`) aos rascunhos em `specs/001-registro-pastas-curadoria/contracts/`
- [ ] T013 [P] Escrever `tests/integration/test_jsonschema_validator.py`: reporta **todas** as violações de uma vez (campo + motivo); versão ausente/`"2"` → `UnsupportedSchemaVersionError`; schema ausente/ilegível → erro específico de infraestrutura (FR-017)
- [ ] T014 [P] Escrever `tests/unit/application/test_dto.py`: DTOs pydantic de entrada (`RegisterFolderInput`, `UpdateFolderInput`) rejeitam tipos errados, vazios e alias inválido antes de chegar ao Domain
- [ ] T015 [P] Escrever `tests/integration/test_logging_setup.py`: saída em JSON com `event`, `alias`, `outcome`, `error_type`; nenhuma linha contém caminho absoluto ou segredo passados como extra
- [ ] T016 Executar `uv run pytest tests/unit tests/contract tests/integration -p no:cacheprovider` e **confirmar que T005–T015 falham** (ImportError/AssertionError); registrar a saída resumida no commit

### Implementação (verde)

- [ ] T017 Implementar `src/praxisforge/domain/errors.py` (hierarquia completa + `Violation`) — faz T005 passar
- [ ] T018 [P] Implementar `src/praxisforge/domain/alias.py` — faz T006 passar
- [ ] T019 [P] Implementar `src/praxisforge/domain/curation_status.py` — faz T007 passar
- [ ] T020 Implementar `src/praxisforge/domain/folder.py` (dataclass frozen com invariantes em `__post_init__`) — faz T008 passar
- [ ] T021 Implementar `src/praxisforge/domain/folder_registry.py` (agregado: `add`, `get`, `update` atômico, `list`, checagem de versão) — faz T009 passar
- [ ] T022 [P] Criar `schemas/folders-schema-v1.json` e `schemas/source-schema-v1.json` copiando os rascunhos de `specs/001-registro-pastas-curadoria/contracts/` — faz T010–T012 passarem
- [ ] T023 Definir portas em `src/praxisforge/application/ports.py`: `FolderRegistryRepository` (`load() -> FolderRegistry`, `load_raw() -> dict[str, object]`, `save(registry)`, `exists() -> bool`), `PathResolver` (`resolve(alias) -> Path`), `ContractValidator` (`validate(document, schema_name) -> None` levantando `ContractValidationError`)
- [ ] T024 Implementar `src/praxisforge/infrastructure/jsonschema_validator.py` (Draft 2020-12, `iter_errors`, ordena violações por campo) — faz T013 passar
- [ ] T025 [P] Implementar `src/praxisforge/application/dto.py` (DTOs pydantic) — faz T014 passar
- [ ] T026 [P] Implementar `src/praxisforge/infrastructure/logging_setup.py` (formatter JSON, sanitização de caminhos absolutos) — faz T015 passar
- [ ] T027 Rodar `make lint && make test` e `make validate-data` (pulando `folders.yaml` ainda inexistente) — tudo verde, cobertura ≥ 90%

**Checkpoint**: Domain, contratos, portas e validador prontos; user stories podem começar (US1 e US2 em paralelo após este ponto, se houver mais de uma pessoa; US3 depende de US1 para o adapter YAML).

---

## Phase 3: User Story 1 — Registrar e consultar pastas a curar (Priority: P1) 🎯 MVP

**Goal**: manter o registro versionado (`src/data/folders.yaml`) com registrar/listar/consultar/atualizar e o registro inicial `github_forks`.

**Independent Test**: registrar `github_forks`, listar e consultar sem nenhuma outra funcionalidade; duplicado recusado; update atômico (spec US1 cenários 1–5).

### Testes primeiro (vermelho)

- [ ] T028 [P] [US1] Escrever `tests/integration/test_yaml_folder_registry.py`: `save` → `load` ida e volta; escrita determinística (bytes idênticos ao regravar); escrita atômica (falha simulada em `os.replace` mantém o arquivo original íntegro); arquivo ausente → `RegistryFileNotFoundError`; YAML corrompido → `RegistryUnavailableError` com arquivo/linha; permissão negada (`chmod 000`) → `RegistryUnavailableError`; `add` em arquivo ausente cria o arquivo com `folders: {}` (clarificação Q2); registro com `folders: {}` é válido
- [ ] T029 [P] [US1] Escrever `tests/unit/application/test_register_folder.py` (com repositório fake): novo alias grava; idêntico → resultado `unchanged` sem gravar; dados diferentes → `AliasAlreadyRegisteredError` e nada gravado; repositório indisponível propaga `RegistryUnavailableError`; entrada inválida barrada pelo DTO
- [ ] T030 [P] [US1] Escrever `tests/unit/application/test_query_folders.py`: `list` (com e sem filtro de status), `show` de alias existente e inexistente (`FolderNotFoundError`), saída sem qualquer caminho absoluto
- [ ] T031 [P] [US1] Escrever `tests/unit/application/test_update_folder.py`: atualiza só os campos informados; atômico; `last_scanned` futuro recusado; licença `unknown` mantida com status ≠ `pending` recusada; licença válida + novo status na mesma operação aceita (spec cenário 5); alias inexistente → `FolderNotFoundError`
- [ ] T032 [P] [US1] Escrever `tests/integration/test_cli_folders.py` (chama `main(argv)`): `add`/`list`/`show`/`update` com `--registry` em `tmp_path`; códigos de saída 0/1/2/3 conforme `contracts/cli-contract.md`; mensagens em pt-BR no `stderr`; nenhuma saída contém caminho absoluto; segundo `add` idêntico imprime "inalterado" com código 0
- [ ] T033 [US1] Executar os testes T028–T032 e **confirmar que falham**; registrar no commit

### Implementação (verde)

- [ ] T034 [US1] Implementar `src/praxisforge/infrastructure/yaml_folder_registry.py` (`safe_load`/`safe_dump` ordenado por alias, escrita atômica com arquivo temporário + `os.replace`, valida com `ContractValidator` ao carregar, `load_raw`, criação do arquivo só via `save` do `add`) — faz T028 passar
- [ ] T035 [P] [US1] Implementar `src/praxisforge/application/register_folder.py` — faz T029 passar
- [ ] T036 [P] [US1] Implementar `src/praxisforge/application/query_folders.py` — faz T030 passar
- [ ] T037 [P] [US1] Implementar `src/praxisforge/application/update_folder.py` — faz T031 passar
- [ ] T038 [US1] Implementar `src/praxisforge/presentation/cli.py` com os subcomandos `folders add|list|show|update`, composição das dependências (único ponto que importa Infrastructure), mapeamento exceção → mensagem pt-BR + código de saída, datas exibidas em `DD/MM/AAAA HH:MM`; registrar `[project.scripts] praxisforge = "praxisforge.presentation.cli:main"` em `pyproject.toml` e rodar `uv sync` — faz T032 passar
- [ ] T039 [US1] Criar `src/data/folders.yaml` com `schema_version: "1"` e `github_forks` (licença `unknown`, status `pending`, `last_scanned: null`); rodar `make validate-data` e `uv run praxisforge folders list` (quickstart §2)
- [ ] T040 [US1] Rodar `make lint && make test`; executar o quickstart §3 manualmente (registrar, repetir, recusar duplicado) e apagar a pasta `exemplo` criada no teste manual

**Checkpoint**: US1 entregue e demonstrável de forma independente (**MVP**).

---

## Phase 4: User Story 2 — Resolver o caminho real por configuração externa (Priority: P1)

**Goal**: resolver alias → caminho real via `PRAXISFORGE_FOLDER_<ALIAS>`, sem caminho absoluto no repositório.

**Independent Test**: definir a variável para `github_forks` e resolver; remover e ver falha clara (spec US2 cenários 1–4).

### Testes primeiro (vermelho)

- [ ] T041 [P] [US2] Escrever `tests/integration/test_env_path_resolver.py` (`tmp_path` + `monkeypatch`): variável ausente/vazia → `FolderPathNotConfiguredError` (mensagem cita o nome da variável); caminho relativo, com `..` → `FolderPathInvalidError`; inexistente; arquivo em vez de diretório; sem permissão (`chmod 000`) → `FolderPathUnreadableError`; link simbólico válido é seguido e retorna o destino real (clarificação Q3); link simbólico quebrado → `FolderPathInvalidError`; mensagens só citam o alias em questão, nunca outros caminhos
- [ ] T042 [P] [US2] Escrever `tests/unit/application/test_resolve_folder_path.py` (resolvedor e repositório fakes): alias não registrado → `FolderNotFoundError` (não consulta o ambiente); falha de resolução de um alias não afeta a resolução de outro em lote; log estruturado sem caminho
- [ ] T043 [P] [US2] Escrever `tests/integration/test_cli_resolve.py`: `folders resolve github_forks` imprime o caminho real e retorna 0; variável ausente → código 3 e mensagem com o nome da variável; alias inexistente → código 1
- [ ] T044 [P] [US2] Escrever `tests/contract/test_no_absolute_paths.py`: varre `src/`, `schemas/` e `src/data/` procurando `/home/`, `/Users/`, `C:\` (SC-005) e garante que um registro com caminho absoluto no lugar do alias é rejeitado pelo schema
- [ ] T045 [US2] Executar T041–T044 e **confirmar que falham** (T044 pode passar parcialmente; registrar quais)

### Implementação (verde)

- [ ] T046 [US2] Implementar `src/praxisforge/infrastructure/env_path_resolver.py` (`os.environ`, `Path.resolve(strict=True)`, `os.access(R_OK|X_OK)`, exceções específicas) — faz T041 passar
- [ ] T047 [US2] Implementar `src/praxisforge/application/resolve_folder_path.py` — faz T042 passar
- [ ] T048 [US2] Adicionar o subcomando `folders resolve` em `src/praxisforge/presentation/cli.py` (única saída que imprime caminho absoluto) — faz T043 passar
- [ ] T049 [US2] Rodar `make lint && make test`; executar o quickstart §4 e §7

**Checkpoint**: US1 + US2 funcionam de forma independente.

---

## Phase 5: User Story 3 — Validar registros contra contratos versionados (Priority: P2)

**Goal**: validar registro de pastas e fontes contra contratos versionados, com todas as violações e falha por item agregada.

**Independent Test**: validar registro correto e variações inválidas; lote de 100 pastas com 1 inválida processa as outras 99 (spec US3 cenários 1–5).

### Testes primeiro (vermelho)

- [ ] T050 [P] [US3] Escrever `tests/unit/domain/test_source_record.py`: campos obrigatórios; `unknown` ⇒ `pending` e `extract_allowed=false`; `pending` com `extract_allowed=true` recusado; data futura; `origin` com caminho absoluto
- [ ] T051 [P] [US3] Escrever `tests/unit/application/test_validate_registry.py` (fakes): `BatchReport` com itens ok e `ItemFailure(alias, error_type, message)`; **100 pastas com 1 inválida ⇒ 99 ok + 1 falha, sem levantar** (SC-004); violações de uma pasta listadas todas de uma vez; versão não suportada do registro inteiro levanta `UnsupportedSchemaVersionError`; registro ausente → `RegistryFileNotFoundError`; a validação por pasta usa `load_raw()` e valida cada entrada embrulhada em `{schema_version, folders: {alias: entry}}`
- [ ] T052 [P] [US3] Escrever `tests/integration/test_source_frontmatter.py`: lê frontmatter YAML de `.md` em `tmp_path`; sem frontmatter, frontmatter corrompido, arquivo ilegível → erros específicos; lote de arquivos com falha por item
- [ ] T053 [P] [US3] Escrever `tests/integration/test_cli_validate.py`: `folders validate` (código 0 com registro válido; código 1 listando todas as violações e resumo `N ok, M com falha`); `sources validate PATH...` (arquivo e diretório; falha por item não interrompe o lote)
- [ ] T054 [P] [US3] Escrever `tests/integration/test_validate_scale.py`: 200 pastas em `tmp_path` — listagem e validação completas em < 5 s (SC-003, marcar com `@pytest.mark.slow` se necessário)
- [ ] T055 [US3] Executar T050–T054 e **confirmar que falham**; registrar no commit

### Implementação (verde)

- [ ] T056 [US3] Implementar `src/praxisforge/domain/source_record.py` — faz T050 passar
- [ ] T057 [P] [US3] Implementar `src/praxisforge/infrastructure/source_frontmatter.py` (leitor de frontmatter, sem executar código, `yaml.safe_load`) — faz T052 passar
- [ ] T058 [US3] Implementar `src/praxisforge/application/validate_registry.py` (`BatchReport`, `ItemFailure`, validação de pastas e de fontes em lote) — faz T051 passar
- [ ] T059 [US3] Adicionar `folders validate` e `sources validate` em `src/praxisforge/presentation/cli.py` — faz T053 passar; conferir T054
- [ ] T060 [US3] Rodar `make lint && make test`; executar o quickstart §5

**Checkpoint**: US1–US3 independentes e validadas.

---

## Phase 6: User Story 4 — Camadas com regras de dependência verificáveis (Priority: P3)

**Goal**: verificação automática das regras de dependência entre camadas.

**Independent Test**: introduzir uma dependência proibida e ver o teste falhar apontando módulo, import e regra (spec US4 cenários 1–2).

### Testes primeiro (vermelho)

- [ ] T061 [P] [US4] Escrever `tests/architecture/test_layer_checker.py` contra um pacote sintético em `tmp_path`: `domain` importando `yaml`/`pydantic`/`requests` → violação; `domain` importando `logging` → violação; `domain` importando `praxisforge.infrastructure` → violação; `application` importando `praxisforge.infrastructure` ou `presentation` → violação; `infrastructure` importando `presentation` → violação; `presentation` importando `praxisforge.domain` diretamente → violação; `presentation/cli.py` importando `infrastructure` (ponto de composição) → permitido; mensagem cita módulo, import e regra (SC-006: 100% detectadas)
- [ ] T062 [P] [US4] Escrever `tests/architecture/test_layer_rules.py`: aplica o checker ao `src/praxisforge/` real e exige zero violações
- [ ] T063 [US4] Executar T061–T062 e **confirmar que falham** (checker inexistente)

### Implementação (verde)

- [ ] T064 [US4] Implementar `tests/architecture/layer_checker.py` (percorre módulos com `ast`, matriz de dependências de `research.md` D10, retorna lista de `LayerViolation(module, imported, rule)`) — faz T061 e T062 passarem
- [ ] T065 [US4] Corrigir eventuais violações reais reveladas por T062 (sem afrouxar a matriz) e rodar `make lint && make test`; executar o quickstart §6

**Checkpoint**: as quatro user stories entregues.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: documentação exigida, gates finais, memória e PR

- [ ] T066 [P] Criar `docs/architecture/overview.md` (camadas, fluxo dos casos de uso, regras de dependência, decisões, mapa de módulos) com cabeçalho de datas
- [ ] T067 [P] Criar ADRs em `docs/decisions/` (MADR simplificado): `0001-domain-sem-pydantic.md`, `0002-registro-yaml-sem-preservar-comentarios.md`, `0003-verificacao-de-camadas-por-ast.md`, `0004-update-aceita-licenca.md`
- [ ] T068 [P] Acrescentar (sem sobrescrever) as novas entradas em `docs/INDEX.md` e `docs/TODO.md` (features entregues e pendências: varredura das pastas = feature 002; catálogo de skills vazio; `scripts/` fora do gate do ruff)
- [ ] T069 Rodar todos os gates: `uv run ruff check .`, `uv run ruff format --check src tests`, `uv run mypy` (0 erros), `uv run pytest` (cobertura ≥ 90%, incluindo cenários de falha de FS e ambiente — SC-007), `make validate-data`
- [ ] T070 Executar o `quickstart.md` completo (§1–§7) e confirmar cada resultado esperado; registrar divergências em `docs/bugs/` se houver (relatório de erro + correção)
- [ ] T071 Atualizar `graphify` (`graphify update .`) e registrar no vault `claude_memory` a feature concluída: `projects/praxisforge.md` (decisões, catálogo, pendências) e `daily/AAAA-MM-DD.md`, listando novas notas no `00-index.md`; sem segredos nem caminhos internos
- [ ] T072 Abrir o PR da branch `001-registro-pastas-curadoria` para `main` (commits Conventional em pt-BR, corpo do PR com "o quê / por quê / verificação"); aguardar CI verde antes de qualquer merge

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: depende do Setup — **bloqueia todas as user stories**
- **US1 (P1)**: depende da Foundational; é o MVP
- **US2 (P1)**: depende da Foundational e usa o repositório de US1 apenas por porta (fake nos testes); a integração real com o registro usa o adapter de T034
- **US3 (P2)**: depende da Foundational e do adapter YAML (T034) e da CLI (T038)
- **US4 (P3)**: depende apenas de que os módulos existam (T038, T048, T059 idealmente concluídas para o checker cobrir todo o código); os testes T061 rodam contra pacote sintético e podem começar após a Foundational
- **Polish (Phase 7)**: depende das stories desejadas

### Ordem dentro de cada story

1. Testes de falha (vermelho) → confirmar que falham
2. Entidades/contratos → serviços/casos de uso → adapters → CLI
3. Verde → refatorar com a suíte como rede de segurança
4. `make lint && make test` antes de avançar

### Parallel Opportunities

- Foundational: T005–T008, T010–T015 (testes em arquivos distintos); T018–T019, T022, T025–T026 (implementações independentes)
- US1: T028–T032 (testes) e T035–T037 (casos de uso) em paralelo
- US2: T041–T044 em paralelo
- US3: T050–T054 em paralelo
- US4: T061–T062 em paralelo
- Polish: T066–T068 em paralelo
- US1 e US2 podem ser tocadas por pessoas diferentes após a Foundational; `cli.py` é arquivo compartilhado — serializar T038 → T048 → T059

### Exemplo de execução paralela (US1)

```text
Task: "T028 tests/integration/test_yaml_folder_registry.py"
Task: "T029 tests/unit/application/test_register_folder.py"
Task: "T030 tests/unit/application/test_query_folders.py"
Task: "T031 tests/unit/application/test_update_folder.py"
Task: "T032 tests/integration/test_cli_folders.py"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Setup → Foundational
2. US1 completa e validada de forma independente (quickstart §2–§3)
3. Abrir PR intermediário se desejado (Foundational + US1)

### Incremental Delivery

1. + US2 → resolução de caminho (fecha requisito de proveniência/privacidade)
2. + US3 → validação em lote de pastas e fontes
3. + US4 → guarda-corpo de arquitetura
4. Polish → docs, gates finais, vault, PR

### Regras de qualidade por tarefa

- Nenhuma tarefa de implementação começa antes do vermelho confirmado do seu grupo de testes
- Todo teste de sucesso vem com os de falha correspondentes; toda dependência externa (FS, ambiente) tem ao menos um teste de indisponibilidade/permissão negada
- Commits pequenos por grupo (Conventional Commits, pt-BR); nunca commitar direto na `main`; sem `--no-verify`

## Notes

- 72 tarefas: Setup 4 · Foundational 23 · US1 13 · US2 9 · US3 11 · US4 5 · Polish 7
- Fora do escopo (feature 002): varredura das pastas, curadoria, provedores de IA, skills
