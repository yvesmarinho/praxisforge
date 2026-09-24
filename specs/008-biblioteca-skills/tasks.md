<!-- Criado em: 24/09/2026 15:55 -->
<!-- Modificado em: 24/09/2026 16:06 -->

# Tasks: Biblioteca de skills versionada

**Input**: Design documents from `/specs/008-biblioteca-skills/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli-skills.md,
skill-frontmatter-v1.json, skill-publication-v1.json), quickstart.md

**Tests**: OBRIGATÓRIOS (constituição III). Em cada grupo: testes de falha → confirmar vermelho →
implementar → verde.

**Organization**: US1 (P1) template + validação; US2 (P2) catálogo; US3 (P3) publicação.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Confirmar baseline verde na branch `008-biblioteca-skills` (`make lint`, `make test`, `make validate-data`)

---

## Phase 2: Foundational (bloqueia todas as stories)

### Testes (vermelho primeiro)

- [X] T002 [P] Testes de contrato em tests/contract/test_skill_schemas.py: `schemas/skill-frontmatter-v1.json` e `schemas/skill-publication-v1.json` são Draft 2020-12 válidos e idênticos (sem `_meta`) aos de specs/008-biblioteca-skills/contracts/; frontmatter: aceita `name`/`description`/`metadata.version` válidos e campos extras na raiz (`allowed-tools`); rejeita `name` com maiúsculas/espaço/>64, `description` vazia/>1024, `metadata` sem `version`, versão não semver (`1`, `1.0`, `v1.0.0`), `sources` repetidas, `authored` não booleano; marcador: rejeita hash com 63 caracteres, `source` absoluto, campo extra
- [X] T003 [P] Testes em tests/unit/domain/test_errors.py: `InvalidSkillError(name, violations)` ⊂ `PraxisForgeError` com `name` e `violations` (lista de `Violation`) e mensagem com todas; `SkillNotFoundError(name)`, `ForeignSkillDestinationError(name, location)`, `SkillVersionNotBumpedError(name, version)` ⊂ `PraxisForgeError`; `SkillPublicationError(name, reason)` ⊂ `PraxisForgeError`
- [X] T004 [P] Testes em tests/unit/domain/test_skill.py para `SkillName` e `Skill.from_parts(folder_name, frontmatter, references)`: nome divergente da pasta; nome fora do formato/>64; descrição vazia (após strip)/>1024; versão não semver (casos: `1`, `01.0.0`, `1.0.0-`), aceita `1.0.0-rc.1+build.5`; sem fontes e `authored` falso → violação (FR-007); `sources` repetidas; referência com `..` saindo da pasta, caminho absoluto (`/etc/x`) e esquema `file:`; **todas** as violações coletadas numa única `InvalidSkillError`; skill válida autoral e válida com fontes
- [X] T005 [P] Testes em tests/unit/domain/test_skill.py para `extract_references(body)`: coleta alvos de `[t](a)` e `![a](b)`; ignora `http:`, `https:`, `mailto:` e âncoras `#x`; remove `#fragmento` de `arquivo.md#sec`; ordem estável sem duplicatas
- [X] T006 Rodar T002–T005 e **confirmar vermelho**

### Implementação

- [X] T007 Criar schemas/skill-frontmatter-v1.json e schemas/skill-publication-v1.json a partir dos contratos (com `_meta` atualizado)
- [X] T008 [P] Exceções em src/praxisforge/domain/errors.py (+ `__all__`) e reexportação em src/praxisforge/application/errors.py
- [X] T009 [P] Criar src/praxisforge/domain/skill.py (stdlib: `SkillName`, `Skill`, `extract_references`, regex semver 2.0), cabeçalho padrão e docstrings reST com doctest
- [X] T010 Fixture autouse em tests/conftest.py: `HOME=<tmp_path>/home` (nenhum teste publica no `~/.claude` real)
- [X] T011 Rodar T002–T005 e a suíte inteira; **confirmar verde**; `make lint`

**Checkpoint**: domínio e contratos de skill prontos.

---

## Phase 3: User Story 1 — Criar e validar skills (P1) 🎯 MVP

**Goal**: template no repo e `skills validate <nome>|--all` com forma + proveniência, falha por skill.

**Independent Test**: skills em `tmp_path` (com `src/data/sources` fictício); cada regra quebrada gera a falha correspondente e o lote continua.

### Testes (vermelho primeiro)

- [X] T012 [P] [US1] Testes de integração em tests/integration/test_filesystem_skill_repository.py para `FilesystemSkillRepository(skills_dir)`: `list_names()` ignora pastas com `_`/`.` e arquivos soltos, ordenado; `load(name)` devolve frontmatter, corpo e referências existentes/ausentes; pasta sem `SKILL.md`, sem frontmatter, frontmatter inválido/não fechado → `InvalidSkillError` com o motivo; nome inexistente → `SkillNotFoundError`; `content_hash(name)` SHA-256 estável, muda ao alterar qualquer arquivo e ignora `.praxisforge-skill.json` e `__pycache__`
- [X] T013 [P] [US1] Testes em tests/unit/application/test_validate_skills.py com fakes (repositório de skills, índice de fontes via `SourceReader` + `ContractValidator`): fonte citada inexistente; slug ambíguo (duas categorias); fonte inválida (falha de `validate_sources`); todas as fontes `link` e não autoral → violação FR-007a; uma `summary` + uma `link` → ok; autoral sem fontes → ok; referência de arquivo ausente; lote com válidas e inválidas agrega por skill; `--all` vazio → relatório vazio; nome inexistente → falha do item
- [X] T014 [P] [US1] Testes em tests/integration/test_cli_skills_validate.py (cwd = projeto temporário com `schemas/`, `skills/`, `src/data/sources/`): `skills validate <nome>` ok → exit 0; linhas `<skill>: <motivo>` e resumo `N ok, M com falha`; `--all` com uma inválida → exit 1; nome inexistente → exit 1; `skills validate` sem nome nem `--all` → exit 2
- [X] T015 [P] [US1] Teste em tests/contract/test_skill_template.py: `skills/_template/SKILL.md` existe, tem frontmatter válido no schema v1 com `name` de exemplo e instruções de preenchimento no corpo; o template não é listado como skill
- [X] T016 [US1] Rodar T012–T015 e **confirmar vermelho**

### Implementação

- [X] T017 [US1] Portas `SkillRepository` (`list_names`, `load`, `content_hash`, `skill_dir`) em src/praxisforge/application/ports.py e adapter src/praxisforge/infrastructure/filesystem_skill_repository.py (frontmatter com o loader seguro existente; validação de forma pelo schema v1 via `ContractValidator` + entidade)
- [X] T018 [US1] Caso de uso src/praxisforge/application/validate_skills.py (`validate_skills(repo, validator, source_reader, sources_dir, names) -> SkillValidationReport`), índice de slugs e regra FR-006/FR-007a reaproveitando `validate_sources`; log estruturado
- [X] T019 [US1] Subcomando `skills validate [nome] [--all]` em src/praxisforge/presentation/cli.py
- [X] T020 [US1] Criar skills/_template/SKILL.md (frontmatter válido de exemplo + instruções: formato, `metadata.version`, `sources`/`authored`, arquivos de apoio por link relativo)
- [X] T021 [US1] Rodar T012–T015 e a suíte; **confirmar verde**; `make lint`; tests/architecture

**Checkpoint**: MVP — skills podem ser criadas e validadas.

---

## Phase 4: User Story 2 — Catálogo (P2)

**Goal**: `skills catalog` gera `skills/README.md` determinístico com as skills válidas.

**Independent Test**: gerar duas vezes e comparar bytes; skill inválida omitida com exit 1.

### Testes (vermelho primeiro)

- [X] T022 [P] [US2] Testes em tests/unit/application/test_build_catalog.py: conteúdo com cabeçalho fixo "gerado — não editar", tabela `| Skill | Propósito | Versão | Caminho | Fontes |` em ordem alfabética; descrição com quebras/`|` normalizada; fontes ordenadas ou "autoral"; sem skills → mensagem "nenhuma skill"; inválidas omitidas e listadas no resultado; mesma entrada → mesma saída (determinismo)
- [X] T023 [P] [US2] Testes em tests/integration/test_cli_skills_catalog.py: `skills catalog` grava `skills/README.md`; segunda execução idêntica byte a byte (SC-002); inválida → exit 1 com `catálogo: N skills (M omitidas)`; template fora do catálogo
- [X] T024 [US2] Rodar T022–T023 e **confirmar vermelho**

### Implementação

- [X] T025 [US2] Porta `CatalogWriter` em src/praxisforge/application/ports.py, adapter src/praxisforge/infrastructure/filesystem_catalog_writer.py (escrita atômica) e caso de uso src/praxisforge/application/build_catalog.py
- [X] T026 [US2] Subcomando `skills catalog` em src/praxisforge/presentation/cli.py
- [X] T027 [US2] Rodar T022–T023; **confirmar verde**; `make lint`

---

## Phase 5: User Story 3 — Publicação (P3)

**Goal**: `skills publish` idempotente, por cópia ou symlink, sem tocar terceiros, com regra de versão, órfãs e `--prune`.

**Independent Test**: publicar em `HOME` temporário; repetir; alterar sem versão; terceiro; órfã.

### Testes (vermelho primeiro)

- [X] T028 [P] [US3] Testes de integração em tests/integration/test_filesystem_skill_publisher.py com arquivos reais: `inspect(dest, name, skill_dir)` distingue ausente, nosso-cópia (marcador válido), nosso-symlink, terceiro (pasta sem marcador, marcador inválido, symlink para outro lugar, arquivo); `publish_copy` grava arquivos + marcador válido no schema e substitui destino nosso de forma atômica; falha simulada (monkeypatch de cópia) mantém o destino antigo e não deixa temporários; destino sem permissão → `SkillPublicationError`; `publish_symlink` cria/troca o link; `remove` só remove destinos nossos; `list_published(dest)` devolve só os nossos
- [X] T029 [P] [US3] Testes em tests/unit/application/test_publish_skills.py com fakes: skill inválida recusada (sem chamar o publisher); ausente → publicada; mesmo hash → inalterada; hash diferente + versão diferente → atualizada; hash diferente + mesma versão → `SkillVersionNotBumpedError` e demais seguem; terceiro → `ForeignSkillDestinationError`; symlink existente e modo symlink → inalterada; troca cópia↔symlink sempre publica, sem regra de versão (inclusive symlink→cópia com a mesma versão); `--all` lista órfãs sem remover; `prune` remove só órfãs nossas; falha de gravação agregada como erro de ambiente
- [X] T030 [P] [US3] Testes em tests/integration/test_cli_skills_publish.py (HOME temporário, projeto temporário): `--target global` → `~/.claude/skills/<nome>/`; `--target <pasta>` → `<pasta>/.claude/skills/<nome>/`; pasta de projeto inexistente → exit 2; `--prune` sem `--all` → exit 2; linhas `<skill> → publicada|inalterada|atualizada|recusada (...)`; exit 1 com recusas; exit 3 sem permissão; órfã listada e removida com `--prune`; terceiro intacto (SC-004); segunda publicação sem mudança não altera `mtime` dos arquivos (SC-003)
- [X] T031 [P] [US3] Teste em tests/integration/test_publish_skills_script.py: `scripts/publish-skills` é executável, tem shebang e repassa argumentos (resultado igual ao comando; usa `subprocess` com `HOME` temporário e cwd do projeto)
- [X] T032 [P] [US3] Teste de escala em tests/integration/test_skills_scale.py: 50 skills autorais pequenas — validate, catalog e publish medidos separadamente, < 5 s cada (SC-005); fixture barata (arquivos mínimos) para não repetir a lentidão do CI do PR #15
- [X] T033 [US3] Rodar T028–T032 e **confirmar vermelho**

### Implementação

- [X] T034 [US3] Porta `SkillPublisher` (`inspect`, `publish_copy`, `publish_symlink`, `remove`, `list_published`) em src/praxisforge/application/ports.py e adapter src/praxisforge/infrastructure/filesystem_skill_publisher.py (marcador `.praxisforge-skill.json` validado no schema, cópia em temporário + rename, `OSError` → `SkillPublicationError`)
- [X] T035 [US3] Caso de uso src/praxisforge/application/publish_skills.py (valida via `validate_skills`, decide por estado do destino e regra de versão, órfãs/prune, relatório por skill)
- [X] T036 [US3] Subcomando `skills publish` em src/praxisforge/presentation/cli.py (`--target global` = `Path.home()/.claude/skills`; pasta → `<pasta>/.claude/skills`; `--mode`, `--all`, `--prune`; exit codes do contrato)
- [X] T037 [US3] Criar scripts/publish-skills (bash, cabeçalho de datas, `set -euo pipefail`, `cd` para a raiz do repo, `exec uv run praxisforge skills publish "$@"`, `chmod +x`)
- [X] T038 [US3] Rodar T028–T032; **confirmar verde**; `make lint`; tests/architecture

---

## Phase 6: Polish & Cross-Cutting

- [X] T039 [P] ADR docs/decisions/0009-biblioteca-de-skills.md (formato, proveniência FR-007a, marcador/hash, regra de versão, órfãs/prune, catálogo sem cabeçalho de datas)
- [X] T040 [P] Guia docs/guides/criar-publicar-skills.md (criar a partir do template, validar, catalogar, publicar, atalho) e **acréscimos** em README.md, docs/guides/operar-cli-praxisforge.md, docs/architecture/overview.md e docs/TODO.md (registrar que `skills` resolve `skills/` e `src/data/sources/` a partir do diretório atual; `--target ./global` para pasta chamada `global`)
- [X] T041 Gerar skills/README.md inicial com `skills catalog` (catálogo vazio, "nenhuma skill")
- [X] T042 Executar os cenários de specs/008-biblioteca-skills/quickstart.md com `HOME` temporário e skill descartável
- [X] T043 Gates finais: `make lint`, `ruff format --check` nos arquivos alterados, `make test` (cobertura ≥ 90%), `make validate-data`, `make security`; `graphify update .`
- [X] T044 Relatório em docs/bugs/ apenas se surgir bug; registrar a sessão no vault `claude_memory` conforme o Princípio VII: nota de sessão em `daily/`, atualização de `projects/praxisforge.md` (incluindo a seção "Catálogo de skills") e listagem de toda nota nova no `00-index.md`

---

## Dependencies & Execution Order

- Setup (T001) → Foundational (T002–T011) → US1 (T012–T021) → US2 (T022–T027) e US3 (T028–T038) → Polish (T039–T044).
- US2 depende de US1 (repositório + validação). US3 depende de US1 (validação e hash); US2 e US3 são independentes entre si.

## Parallel Examples

- Foundational: T002–T005 juntos; depois T008 e T009.
- US1: T012–T015 juntos.
- US2 e US3 em paralelo após a US1; dentro da US3, T028–T032 juntos.
- Polish: T039 e T040 juntos.

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1 (T001–T021) — biblioteca com template e validação.
2. US2: catálogo navegável.
3. US3: publicação segura e idempotente + atalho.
4. Polish: ADR, guias, catálogo inicial, gates, vault.
