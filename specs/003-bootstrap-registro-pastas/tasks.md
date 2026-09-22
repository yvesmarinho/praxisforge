<!-- Criado em: 22/09/2026 17:20 -->
<!-- Modificado em: 22/09/2026 16:43 -->

---

description: "Tasks — 003-bootstrap-registro-pastas"

---

# Tasks: Bootstrap do Registro de Pastas

**Input**: Design documents from `/specs/003-bootstrap-registro-pastas/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: OBRIGATÓRIOS (constituição III — Test-First, NON-NEGOTIABLE). Em cada fase a ordem é: testes de falha → confirmar vermelho → implementação → verde. Implementação escrita antes dos testes deve ser descartada.

**Organization**: agrupadas por user story; cada fase é um incremento testável de forma independente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência em tarefa incompleta)
- **[Story]**: US1–US3 (mapeia para as user stories da spec)
- Caminhos relativos à raiz do repositório

## Convenções de código (valem para toda tarefa que cria/edita `.py`)

- Cabeçalho `# -*- coding: utf-8 -*-` + docstring de programa (NOME, TITULO, DATA, MODIFICADO, VERSÃO, DEPEND, HISTÓRICO, STATUS); datas do sistema em `America/Sao_Paulo`
- Type hints em parâmetros e retornos; docstrings reST (`:param:`, `:return:`); `pathlib`; imports seletivos
- Sem `print()`: a CLI escreve com `sys.stdout.write`/`sys.stderr.write`; logs via `logging`
- Nenhum caminho absoluto em código, saída CLI, logs ou relatório (FR-014), **exceto** a mensagem
  de erro sobre a própria pasta-raiz inválida (exceção explícita — ver `contracts/cli-bootstrap.md`)
- Subpastas processadas em ordem alfabética (determinismo — FR-002/research.md Decisão 4a)
- Ao concluir cada grupo: `make lint && make test` verdes antes de seguir

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: confirmar baseline verde; nenhuma dependência nova é necessária

- [X] T001 Rodar `uv sync && make lint && make test` a partir da branch `003-bootstrap-registro-pastas` e confirmar baseline 100% verde antes de iniciar qualquer tarefa nova

**Checkpoint**: ambiente confirmado.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: mudanças de Domain e contrato compartilhadas pelas 3 user stories — o novo valor de
status `ignore`, a invariante relaxada, o schema atualizado e a exceção semântica de raiz
inválida. Nenhuma user story usa `status: ignore` ou a nova exceção sem essas mudanças.

**⚠️ CRITICAL**: nenhuma user story começa antes desta fase.

### Testes primeiro (vermelho)

- [X] T002 [P] Adicionar a `tests/unit/domain/test_curation_status.py` o caso: `CurationStatus.IGNORE`
      existe, `CurationStatus.from_str("ignore")` funciona, `label_pt_br()` retorna `"ignorada"`
- [X] T003 [P] Adicionar a `tests/unit/domain/test_folder.py` o caso: `license="unknown"` com
      `status=CurationStatus.IGNORE` é aceito sem levantar (invariante relaxada, FR-011); manter o
      caso de regressão já existente (`unknown` + `scanned` continua levantando
      `UnknownLicenseRequiresPendingError`)
- [X] T004 [P] Adicionar a `tests/contract/test_folders_schema.py` os casos: documento com
      `status: "ignore"` é válido; documento com `license: "unknown"` + `status: "ignore"` é
      válido; regressão — `license: "unknown"` + `status: "scanned"` continua inválido
- [X] T005 [P] Adicionar a `tests/unit/domain/test_errors.py` o caso: `InvalidRootPathError(root,
      reason)` existe, é subclasse de `PraxisForgeError`, mensagem cita `root` e `reason` sem
      vazar informação além do esperado
- [X] T006 Rodar `uv run pytest tests/unit/domain/test_curation_status.py tests/unit/domain/test_folder.py tests/contract/test_folders_schema.py tests/unit/domain/test_errors.py -p no:cacheprovider` e **confirmar que T002–T005 falham**

### Implementação (verde)

- [X] T007 [P] Adicionar `IGNORE = "ignore"` a `src/praxisforge/domain/curation_status.py`
      (`_ROTULOS_PT_BR["ignore"] = "ignorada"`) — faz T002 passar
- [X] T008 [P] Relaxar a invariante em `src/praxisforge/domain/folder.py`: `license == "unknown"`
      exige `status in (CurationStatus.PENDING, CurationStatus.IGNORE)` — faz T003 passar
- [X] T009 [P] Adicionar `InvalidRootPathError(root: str, reason: str)` a
      `src/praxisforge/domain/errors.py` (subclasse de `PraxisForgeError`) — faz T005 passar
- [X] T010 Atualizar `schemas/folders-schema-v1.json`: `status.enum` +`"ignore"`; o `if/then` de
      `license == "unknown"` passa a exigir `status.enum: ["pending", "ignore"]` (atualizar também
      `_meta.modificado_em`) — faz T004 passar
- [X] T011 Rodar `make lint && make test` e confirmar verde, cobertura ≥ 90%

**Checkpoint**: Domain e contrato prontos; US1, US2 e US3 podem começar (US2 depende de US1 estar
pronto; US3 é independente das duas).

---

## Phase 3: User Story 1 — Gerar o registro inicial a partir de uma pasta-raiz (Priority: P1) 🎯 MVP

**Goal**: `folders bootstrap <root>` lista as subpastas de primeiro nível de `<root>` e registra
como novas todas as que ainda não existem no registro, extraindo `description`/`license` quando
possível.

**Independent Test**: apontar o bootstrap para uma pasta-raiz de teste com 3 subpastas (uma com
README+LICENSE MIT reconhecível, uma com README mas sem LICENSE, uma sem nenhum dos dois) sobre um
registro vazio, rodar e confirmar que as 3 aparecem em `folders.yaml` com os campos coerentes
(quickstart.md, Cenário 1).

### Testes primeiro (vermelho)

- [X] T012 [P] [US1] Escrever `tests/integration/test_filesystem_folder_probe.py`:
      `list_subfolders()` retorna só diretórios de primeiro nível, ordenados alfabeticamente,
      segue link simbólico, ignora link quebrado silenciosamente; `root` inexistente/não-diretório/
      sem permissão de leitura → `InvalidRootPathError`; `read_description()` extrai o primeiro
      parágrafo útil (ignora cabeçalhos `#`/badges `![`/`[![` no início), trunca em 500
      caracteres, retorna `None` se não houver README, retorna `None` se o README existir mas
      estiver vazio ou só tiver cabeçalhos/badges; `detect_license()` reconhece MIT/Apache-2.0/
      GPL-3.0/BSD-3-Clause pelas frases-chave de `research.md` Decisão 2, retorna `None` se não
      reconhecer, retorna `None` se o texto corresponder a mais de uma licença simultaneamente
      (ambiguidade)
- [X] T013 [P] [US1] Escrever `tests/unit/application/test_bootstrap_folders.py` com os casos
      (registro vazio no início de cada teste): subpasta com README+LICENSE MIT reconhecível →
      registrada com `license: MIT`, `status: not_scanned`, `description` extraída; subpasta com
      README sem LICENSE (ou LICENSE não reconhecido) → registrada com `license: unknown`,
      `status: pending`; subpasta sem README nem LICENSE → registrada com `license: unknown`,
      `status: pending`, `description` padrão (indicando ausência de README); pasta-raiz sem
      nenhuma subpasta → 0 registradas, sem erro; duas subpastas novas cujos nomes slugificam para
      o mesmo alias → a primeira (ordem alfabética) é registrada, a segunda vira falha individual
      (`AliasAlreadyRegisteredError`); nome de subpasta que não vira alias válido mesmo
      slugificado → falha individual (`InvalidAliasError`); **escala (SC-003)** — pasta-raiz com
      50 subpastas sintéticas (40 com README+LICENSE reconhecíveis, 10 sem nenhum dos dois) → as
      50 são registradas com sucesso (as 10 como `unknown`/`pending`), sem interromper a execução;
      **FR-012 explícito** — em nenhum dos casos acima nenhuma pasta registrada pelo bootstrap
      recebe `status: CurationStatus.IGNORE` (`assert all(f.status is not CurationStatus.IGNORE
      for f in <pastas registradas>)`), documentando por nome a garantia de que o bootstrap nunca
      atribui `ignore` sozinho
- [X] T014 [US1] Escrever `tests/integration/test_cli_bootstrap.py`: `folders bootstrap <root>`
      com subpastas válidas → exit code 0, resumo lista as registradas; `root` inexistente → exit
      code 1, mensagem cita o caminho de `root` (exceção explícita de FR-014); nenhuma saída
      contém caminho absoluto de nenhuma subpasta (só o de `root`, quando ele próprio é o erro)
- [X] T015 [US1] Rodar `uv run pytest tests/integration/test_filesystem_folder_probe.py tests/unit/application/test_bootstrap_folders.py tests/integration/test_cli_bootstrap.py -p no:cacheprovider` e **confirmar que T012–T014 falham**

### Implementação (verde)

- [X] T016 [US1] Definir a porta `RootFolderProbe` em `src/praxisforge/application/ports.py`:
      `list_subfolders(root: Path) -> list[Path]`, `read_description(path: Path) -> str | None`,
      `detect_license(path: Path) -> str | None`
- [X] T017 [US1] Implementar `src/praxisforge/infrastructure/filesystem_folder_probe.py`
      (`FilesystemFolderProbe`): `list_subfolders` via `Path.iterdir()`/`is_dir()`, ordenado,
      ignorando link quebrado, levantando `InvalidRootPathError` conforme T012;
      `read_description`/`detect_license` conforme as heurísticas de `research.md` Decisões 2–3 —
      faz T012 passar
- [X] T018 [US1] Implementar `src/praxisforge/application/bootstrap_folders.py`: dataclass frozen
      `BootstrapReport` (`registered: list[str]`, `skipped_existing: list[str]`,
      `skipped_ignored: list[str]`, `failures: list[ItemFailure]`, todos default `[]`); função
      privada de slugificação de nome→candidato a alias (`research.md` Decisão 4); função
      `bootstrap_folders(repository, probe, root)` que carrega o registro, lista subpastas
      (ordenadas), e para cada uma tenta registrar via `Alias()` + `Folder()` + `registry.add()`,
      capturando `InvalidAliasError`/`AliasAlreadyRegisteredError` como `ItemFailure`; persiste o
      registro atualizado uma única vez ao final (escrita atômica) — faz T013 passar. **Nesta
      tarefa ainda não verificar `existing_at_start`** (isso é US2); com um registro vazio no
      início, todo alias candidato é necessariamente novo
- [X] T019 [US1] Adicionar o subcomando `folders bootstrap <root>` em
      `src/praxisforge/presentation/cli.py` (parser + handler; composição de
      `FilesystemFolderProbe()` em `main()`); handler converte `BootstrapReport` em resumo amigável
      (exit 0) e `InvalidRootPathError`/demais `PraxisForgeError` em mensagem + exit code 1, citando
      o caminho de `root` quando for o próprio erro — faz T014 passar. **Nota**: nesta fase
      `skipped_existing`/`skipped_ignored` sempre vêm vazios no resumo impresso (a lógica que os
      popula só chega em T024, US2) — comportamento esperado, não é bug desta tarefa
- [X] T020 [US1] Rodar `make lint && make test` e confirmar verde, cobertura ≥ 90%

**Checkpoint**: MVP entregável — bootstrap registra pastas novas a partir de uma raiz
(quickstart.md Cenário 1).

---

## Phase 4: User Story 2 — Rodar o bootstrap de novo sem duplicar ou perder curadoria manual (Priority: P1)

**Goal**: rodar `folders bootstrap <root>` sobre uma raiz já processada nunca altera nenhum campo
de uma pasta já registrada (curada manualmente ou de uma execução anterior), e pastas `ignore`
nunca são reprocessadas.

**Independent Test**: registrar/curar uma pasta manualmente (ex.: `status: curated`), rodar o
bootstrap de novo sobre a mesma raiz e confirmar que ela permanece intocada; marcar outra pasta
como `ignore` e confirmar que ela é pulada e contada separadamente (quickstart.md Cenário 2).

### Testes primeiro (vermelho)

- [X] T021 [P] [US2] Adicionar a `tests/unit/application/test_bootstrap_folders.py` os casos: uma
      subpasta cujo alias já existe no registro **antes** da execução (com `status: curated`,
      por exemplo) → nenhum campo (`description`/`license`/`content_type`/`status`/
      `last_scanned`) é alterado pelo rerun, alias entra em `skipped_existing`; uma subpasta cujo
      alias já existe com `status: ignore` → pulada, entra em `skipped_ignored`, nenhum campo
      alterado; uma execução com 1 subpasta nova + 1 existente + 1 ignore → `BootstrapReport`
      reflete a contagem correta nos 3 grupos simultaneamente
- [X] T022 [US2] Adicionar a `tests/integration/test_cli_bootstrap.py`: rodar `folders bootstrap
      <root>` duas vezes seguidas sem mudança no filesystem → `folders.yaml` idêntico byte a byte
      entre as duas execuções; resumo da segunda execução mostra a contagem de "já existentes" e
      "ignoradas" corretamente
- [X] T023 [US2] Rodar `uv run pytest tests/unit/application/test_bootstrap_folders.py tests/integration/test_cli_bootstrap.py -p no:cacheprovider` e **confirmar que T021–T022 falham**

### Implementação (verde)

- [X] T024 [US2] Em `bootstrap_folders()` (`application/bootstrap_folders.py`), capturar
      `existing_at_start = set(registry.folders)` **antes** do loop sobre as subpastas; para cada
      alias candidato já presente em `existing_at_start`: se `registry.get(alias).status is
      CurationStatus.IGNORE` → adicionar a `skipped_ignored`, senão → adicionar a
      `skipped_existing`; em ambos os casos, **não** chamar `Folder()`/`registry.add()` para esse
      alias — faz T021 passar. **Nota de execução**: essa lógica já havia sido implementada em
      T018 (US1), por ser necessária para a corretude da função desde o início (evitar que
      `registry.add()` mascarasse colisões como no-op idempotente — ver bug corrigido durante
      T018). T021 confirma o comportamento correto sem exigir código novo nesta tarefa.
- [X] T025 [US2] Ajustar o handler de `folders bootstrap` em `cli.py` para imprimir a contagem
      completa do resumo (registradas / já existentes / ignoradas / falhas) — faz T022 passar.
      **Nota de execução**: já implementado em T019 (US1); T022 confirma sem código novo.
- [X] T026 [US2] Rodar `make lint && make test` e confirmar verde, cobertura ≥ 90%

**Checkpoint**: idempotência garantida (quickstart.md Cenário 2, SC-002).

---

## Phase 5: User Story 3 — Marcar uma pasta para ser sempre ignorada (Priority: P2)

**Goal**: o curador consegue marcar manualmente uma pasta como `status: ignore` via `folders
update`, e a varredura em lote (`folders scan --all`, feature 002) passa a pulá-la.

**Independent Test**: registrar uma pasta, marcá-la `ignore` via `folders update`, rodar `folders
scan --all` e confirmar que ela é pulada e contada separadamente, sem exigir variável de ambiente
para ela (quickstart.md Cenário 3).

### Testes primeiro (vermelho)

- [X] T027 [P] [US3] Adicionar a `tests/unit/application/test_update_folder.py` o caso: `folders
      update` aceita `status="ignore"` mesmo quando a `license` atual é `unknown`, sem exigir que
      ela já seja `pending`
- [X] T028 [P] [US3] Adicionar a `tests/unit/application/test_scan_folders.py` o caso:
      `scan_all_folders()` pula uma pasta com `status: ignore` — não chama `resolver.resolve()`
      para ela, não entra em `ok` nem `failures`, entra em um novo campo `ScanBatchReport.ignored:
      list[str]` (default `[]`); demais pastas continuam processadas normalmente
- [X] T029 [P] [US3] Adicionar a `tests/integration/test_cli_folders.py` o caso: `folders update
      <alias> --status ignore` aceito com exit code 0, mesmo com licença `unknown`
- [X] T030 [US3] Adicionar a `tests/integration/test_cli_scan.py` os casos: `folders scan --all`
      com uma pasta `ignore` no meio do lote → resumo mostra a contagem de "ignoradas"
      separadamente, sem tentar resolver caminho para ela (não exige
      `PRAXISFORGE_FOLDER_<ALIAS>` daquela pasta); `folders scan <alias>` individual e explícito
      sobre um alias `ignore` continua funcionando normalmente (não é pulado — FR-013 só se aplica
      ao modo `--all`)
- [X] T031 [US3] Rodar `uv run pytest tests/unit/application/test_update_folder.py tests/unit/application/test_scan_folders.py tests/integration/test_cli_folders.py tests/integration/test_cli_scan.py -p no:cacheprovider` e **confirmar que T028 e T030 falham** (T027/T029 já devem passar assim que a Fase 2 estiver pronta — `folders update` já aceita qualquer valor válido do enum sem checagem adicional; mantidos como regressão explícita)

### Implementação (verde)

- [X] T032 [US3] Em `src/praxisforge/application/scan_folders.py`, `scan_all_folders()`: antes de
      chamar `resolver.resolve(alias)`, checar `folder.status is CurationStatus.IGNORE`; se for,
      adicionar o alias a um novo campo `ScanBatchReport.ignored: list[str] = field(default_factory=list)`
      e continuar para a próxima pasta, sem contar em `ok` nem `failures` — faz T028 passar
- [X] T033 [US3] Ajustar o handler de `folders scan --all` em `cli.py` para imprimir a contagem de
      "ignoradas" no resumo final — faz T030 passar
- [X] T034 [US3] Rodar `make lint && make test` e confirmar verde, cobertura ≥ 90%

**Checkpoint**: as três user stories entregues (quickstart.md Cenário 3, SC-004).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: documentação e validação final, sem lógica nova

- [X] T035 [P] Atualizar `docs/architecture/overview.md` (mapa de módulos) com
      `application/bootstrap_folders.py` e `infrastructure/filesystem_folder_probe.py`
- [X] T036 [P] Atualizar `docs/reference/folders-yaml.md`: tabela de status +`ignore`; invariante
      relaxada; remover/atualizar a seção "Mudança planejada (feature 003, ainda não
      implementada)" já que agora está implementada
- [X] T037 [P] Atualizar `docs/guides/operar-cli-praxisforge.md`: novo passo `folders bootstrap`;
      status `ignore` na lista de status; nota sobre `folders scan --all` pular pastas `ignore`
- [X] T038 Rodar manualmente os 3 cenários de `quickstart.md` (incluindo a verificação de
      segurança) e confirmar aderência
- [X] T039 Atualizar `docs/INDEX.md` e `docs/TODO.md` (acrescentar, nunca sobrescrever): feature
      003 concluída
- [X] T040 Marcar T001–T039 como concluídas neste arquivo à medida que forem fechadas

**Checkpoint final**: `make lint && make test` verdes, `make validate-data` verde, cobertura
≥ 90%, checklist `checklists/contract-migration-idempotencia.md` (21/21 já revisada) sem
pendências.

---

## Dependencies & Execution Order

```text
Phase 1 (Setup) ──> Phase 2 (Foundational) ──> Phase 3 (US1, P1) ──> Phase 4 (US2, P1)
                                                       │
                                                       └──> Phase 5 (US3, P2, independente de US2)
Phase 4 e Phase 5 ──> Phase 6 (Polish)
```

- Phase 2 bloqueia todas as user stories (novo status, invariante, schema, exceção de domínio).
- US2 depende de US1 (estende `bootstrap_folders()` já existente com a checagem
  `existing_at_start`).
- US3 é independente de US1/US2 — só depende da Fase 2 (status `ignore` já aceito pelo domínio) e
  pode ser implementada em paralelo à Fase 3/4 se houver mais de uma pessoa.

## Parallel Execution Examples

Fase 2: T002/T003/T004/T005 tocam arquivos diferentes — escrever em paralelo antes de T006.

Fase 3 (US1): T012 (probe) e T013 (caso de uso) tocam arquivos diferentes e são independentes
entre si; T014 (CLI) depende conceitualmente dos outros dois existirem para ter algo a testar via
subprocesso da CLI, mas pode ser escrito em paralelo (só roda depois).

Fase 5 (US3): T027/T028/T029 tocam arquivos diferentes — paralelos entre si; T030 depende de T028
estar implementado para fazer sentido (mesma lógica de `ScanBatchReport.ignored`).

Fase 6: T035/T036/T037 são independentes entre si (arquivos de documentação diferentes).

## Implementation Strategy

- **MVP primeiro**: Fase 1 → Fase 2 → Fase 3 (US1) entrega `folders bootstrap <root>` funcional
  registrando pastas novas — já demonstrável (quickstart.md Cenário 1).
- **Incremento 2**: Fase 4 (US2) adiciona a garantia de idempotência — obrigatório antes de
  qualquer uso real do bootstrap em cima de um registro que já tem curadoria manual.
- **Incremento 3**: Fase 5 (US3) adiciona o status `ignore` de ponta a ponta (aplicação manual +
  respeito pela varredura em lote) — pode ser feita em paralelo às Fases 3/4 por outra pessoa,
  já que só depende da Fase 2.
- **Fechamento**: Fase 6 documenta e valida ponta a ponta.
