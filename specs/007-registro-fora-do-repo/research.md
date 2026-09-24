<!-- Criado em: 24/09/2026 11:44 -->
<!-- Modificado em: 24/09/2026 11:44 -->

# Research: Registro de pastas fora do repositório

## R1 — Resolução do local

- **Decision**: função pura `resolve_registry_path(cli_value, env, home, cwd) -> Path` em
  `infrastructure/registry_location.py`; a CLI passa `os.environ`, `Path.home()` e `Path.cwd()`.
  Ordem: `--registry` > `PRAXISFORGE_REGISTRY` (não vazia) > `$XDG_CONFIG_HOME` (não vazia,
  absoluta) + `praxisforge/folders.yaml` > `home/.config/praxisforge/folders.yaml`. `~` expandido
  com o `home` recebido; relativo resolvido contra `cwd`.
- **Rationale**: testável sem monkeypatch global; nenhum caminho fixo (FR-012).
- **Alternatives**: `platformdirs` (dependência nova para 4 linhas); ler `os.environ` dentro da
  função (acopla testes ao ambiente real).
- **Nota XDG**: pela especificação, `XDG_CONFIG_HOME` relativo deve ser ignorado → cai no fallback.

## R2 — Criação da pasta

- **Decision**: nada novo — `YamlFolderRegistryRepository.save` já faz `mkdir(parents=True)`;
  só `add`/`bootstrap` (e `relocate`) gravam registro inexistente (FR-003/FR-004 já vigentes).
- **Rationale**: comportamento existente cobre o requisito; só falta teste com o local padrão.

## R3 — Mensagem de registro ausente

- **Decision**: `RegistryFileNotFoundError(location: str)` → "registro ausente em <local> — crie
  com `folders add` ou `folders bootstrap`". A CLI, antes de despachar comandos que exigem o
  registro, se ele não existir e `find_legacy_registry(cwd)` achar `src/data/folders.yaml` com
  ao menos uma pasta, escreve no stderr a dica "registro antigo encontrado em src/data/folders.yaml
  — execute: praxisforge folders relocate".
- **Rationale**: o local é o "próprio item com problema" (Princípio V permite citá-lo); a dica
  fica na Presentation, sem acoplar o domínio ao layout antigo do repositório.
- **Alternatives**: migrar automaticamente — ação implícita sobre dados do usuário; rejeitado.

## R4 — Comando de migração

- **Decision**: `folders relocate [--from ARQ]` (padrão `src/data/folders.yaml` relativo ao
  diretório atual). Caso de uso `relocate_registry(source_repo, target_path, mover)`:
  1) destino existe → `RegistryAlreadyExistsError` (nada muda); 2) `source_repo.load()` valida
  (v1 → `RegistryMigrationRequiredError`; inválido → `ContractValidationError`); 3)
  `mover.move(src, dst)`. Adapter: cria a pasta do destino, `shutil.copy2` + verificação de
  bytes + `unlink` da origem; falha de I/O → `RegistryRelocationError` com origem intacta.
- **Rationale**: nome distinto de `migrate` (que converte formato v1→v2); cópia verificada antes
  de apagar protege contra perda (SC-003).
- **Alternatives**: `os.replace` (falha entre sistemas de arquivos diferentes); instrução manual
  `mv` (sem validação nem proteção do destino).

## R5 — Exemplo versionado e CI

- **Decision**: `src/data/folders.example.yaml` com 3 pastas fictícias em `/srv/praxisforge/...`
  (status variados, incluindo `pending` com `unknown`); `make validate-data` valida o exemplo;
  `src/data/folders.yaml` entra no `.gitignore` e sai do índice (`git rm --cached`).
- **Rationale**: FR-005–FR-007; o guarda `test_no_absolute_paths` já bloqueia `/home/`.
- **Risco**: `git rm --cached` em outros clones apaga o arquivo na próxima atualização da
  branch se não estiver modificado — documentar "rode `folders relocate` antes de `git pull`"
  (no clone deste usuário o arquivo está modificado, então o git recusa sobrescrever).

## R6 — Isolamento dos testes

- **Decision**: fixture `autouse` em `tests/conftest.py`: `XDG_CONFIG_HOME=<tmp>/xdg`,
  remove `PRAXISFORGE_REGISTRY`.
- **Rationale**: com o novo padrão, qualquer teste que chame `main()` sem `--registry` tocaria
  o `~/.config` real.

## R7 — Limitação conhecida

- `schemas/` continua resolvido relativo ao diretório atual (`_SCHEMAS_DIR`); rodar a CLI fora
  da raiz do projeto não é suportado nesta feature (fora de escopo; registrar no TODO).
