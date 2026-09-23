<!-- Criado em: 23/09/2026 11:35 -->
<!-- Modificado em: 23/09/2026 11:35 -->

# Research: Detecção de mudança de conteúdo pós-curadoria

## R1 — Como consultar o git

- **Decision**: adapter `GitCliInspector` chamando o executável `git` via `subprocess.run`
  (lista de argumentos, `shell=False`, `timeout=10`, `check=False`), com `git -C <pasta>`.
- **Rationale**: zero dependência nova; `git` já é pré-requisito do ambiente; comandos estáveis e
  de saída previsível. `-C <pasta>` faz o git localizar o repositório mesmo quando a pasta é
  subpasta dele.
- **Alternatives**: GitPython (dependência pesada, também chama o executável por baixo);
  pygit2/libgit2 (dependência nativa); ler `.git/HEAD` manualmente (não cobre packed-refs,
  worktrees nem diff por caminho).
- **Bandit**: B404/B603 são esperados; marcar `# nosec` com justificativa (argumentos fixos, sem
  shell, hash validado por regex antes de ir para a linha de comando).

## R2 — Evolução do contrato

- **Decision**: propriedade opcional `last_curated_commit` em `folders-schema-v1.json`, tipo
  `string` com `pattern ^[0-9a-f]{40}([0-9a-f]{24})?$` (SHA-1 ou SHA-256), fora de `required`.
- **Rationale**: atende as três condições do critério de mudança aditiva da feature 003 → sem v2.
  Registros existentes validam sem migração (FR-012 / SC-004).
- **Alternatives**: `folders-schema-v2.json` com o campo obrigatório (`null` por padrão) —
  exigiria migração do YAML e do loader sem ganho real.

## R3 — O que é "mudou dentro da pasta" (Clarificação Q3)

- **Decision**: com a pasta como diretório de trabalho (`-C`), executar
  `git diff --quiet <gravado> HEAD -- .` → código 0 = sem mudança, 1 = mudou, outro = erro.
- **Rationale**: `-- .` restringe o diff à própria pasta (raiz ou subpasta do repositório),
  cobre avanço, retrocesso e mudança de branch do HEAD. Compara árvores, não o working tree →
  alterações não commitadas não contam (premissa da spec).
- **Commit gravado ausente** (histórico reescrito): checar antes com
  `git cat-file -e <hash>^{commit}`; ausente → tratar como "mudou" (edge case da spec).

## R4 — Identificar pasta git e HEAD

- **Decision**: `git -C <pasta> rev-parse --verify -q HEAD`. Código 0 → hash;
  "não é repositório" (`rev-parse --is-inside-work-tree` falha) → `None` (fora do mecanismo);
  repositório sem commits (rev-parse HEAD falha dentro de work tree) → `None`.
- **Erros** (`ContentInspectionError`): executável `git` ausente, timeout, código de saída
  inesperado (ex.: repositório corrompido, `safe.directory`).

## R5 — Onde a regra fica

- **Decision**: Application (`scan_folders.py`) decide entre `baseline_recorded`,
  `unchanged`, `reverted`, `not_git`, `not_applicable`; a porta só responde fatos
  (`head_commit`, `changed_since`). Resultado exposto num enum `ContentCheck` em
  `ScanResult.content_check`.
- **Falha do inspector**: varredura individual → exceção semântica (exit 3, status inalterado);
  lote → `ItemFailure` para o item, demais seguem (FR-009). `last_scanned` do item com falha
  não é atualizado (mesma semântica de falha das features 002/003).

## R6 — Marcar como curada (US1)

- **Decision**: `update_folder()` recebe `PathResolver` e `GitContentInspector` e, **só quando
  o status resultante é `curated`**, resolve o caminho e grava `head_commit()` (ou mantém o valor
  anterior se `None`, i.e. não-git). Falha de resolução ou do inspector → exceção, registro
  intocado (FR-003). Outros status nunca tocam no git nem no campo (FR-010: mantido como histórico).
- **Não-git que já tinha hash** (`.git` removido): ao remarcar curada o hash antigo é mantido?
  **Decision**: sim, mantido; a varredura sinaliza `not_git` e não reverte (edge case da spec).
