<!-- Criado em: 25/09/2026 14:35 -->
<!-- Modificado em: 25/09/2026 14:40 -->

# Research: Inventário de curadoria por pasta

Decisões técnicas da feature 010. Cada uma resolve um ponto que a spec deixou para o plano.

## R1. Onde gravar manifesto e estado

- **Decision**: `<dir do registro>/curation/<alias>/manifest.json` e `state.json`. O diretório vem
  de `resolve_registry_path(...)` (padrão `~/.config/praxisforge/curation/<alias>/`).
- **Rationale**: FR-009 exige ficar junto do registro e fora do repositório; reaproveita a
  resolução `--registry` > `PRAXISFORGE_REGISTRY` > XDG já testada (ADR 0008). Quem move o
  registro com `--registry` leva a curadoria junto.
- **Alternatives**: `$XDG_STATE_HOME` (separa de onde o curador procura; rejeitado pelo debate);
  `curation/` no repositório (proibido pela constituição V).

## R2. Convenções de classificação

- **Decision**: arquivo `<dir do registro>/curation-conventions.yaml` (padrão
  `~/.config/praxisforge/curation-conventions.yaml`, mesma resolução de R1), validado por
  `schemas/curation-conventions-schema-v1.json`. Cada regra: `kind`, `pattern` (glob relativo à
  pasta, `**` permitido) e `unit` (`file` ou `directory`, este último fazendo o diretório pai do
  arquivo casado — ou o próprio diretório — virar um artefato só). Ordem da lista = prioridade.
  A versão das convenções é o SHA-256 do conteúdo canônico da lista (vai no manifesto e no estado).
- **Rationale**: FR-004 (ampliável sem código) e FR-016 (mudança de convenção detectável: versão
  diferente → artefatos reclassificados voltam para pendente). Casamento com `PurePosixPath.full_match`
  (Python 3.13) não está disponível em 3.12 → usar `pathspec` (gitwildmatch) também aqui.
  O repositório mantém `src/data/curation-conventions.example.yaml` (sem caminhos pessoais,
  validado no CI, mesmo padrão de `folders.example.yaml`). Arquivo ausente → `ConventionsMissingError`
  (exit 3) com a instrução de copiar o exemplo; o inventário não cria o arquivo sozinho.
- **Alternatives**: convenções em código (fere FR-004); convenções no repositório (rejeitado pelo
  curador em 25/09/2026: cada máquina ajusta as suas); campo `version` manual (esquecível).

## R3. `.gitignore`

- **Decision**: dependência `pathspec` (já presente transitivamente; passa a ser declarada).
  Cada `.gitignore` encontrado na descida é compilado com `GitIgnoreSpec` e aplicado aos caminhos
  relativos ao seu diretório, na ordem git (pai antes do filho, negação `!` respeitada).
- **Rationale**: funciona em pastas que não são repositório git; determinístico; testável sem git.
- **Alternatives**: `git ls-files --exclude-standard` via `GitCliInspector` (exige work tree e
  processo externo; pastas copiadas sem `.git` falhariam); parser próprio (reinventar negação).

## R4. Hash e unidade do artefato

- **Decision**: SHA-256 por arquivo; artefato-diretório (skill, hook) tem hash = SHA-256 da lista
  ordenada `"<caminho relativo>\0<sha do arquivo>\n"` de todos os arquivos não ignorados dentro dele.
- **Rationale**: SC-004 — mudar um arquivo de apoio muda só o hash da skill dona.

## R5. Binário, tamanho, links e ilegíveis

- **Decision**: binário = byte NUL nos primeiros 8 KiB; limite 256 KiB (`262.144` bytes, arquivo
  a arquivo); `os.walk(followlinks=False)`; link simbólico para arquivo dentro da pasta é lido
  pelo alvo, para fora ou para diretório é ignorado (`symlink_outside`, `symlink_dir`) — sem
  seguir diretórios não há ciclo. `PermissionError`/`OSError` ao ler → `unreadable`.
- **Rationale**: heurística do git; cobre todos os edge cases da spec sem travar.

## R6. Lock e gravação atômica

- **Decision**: `fcntl.flock(LOCK_EX | LOCK_NB)` em `<alias>/.lock`; falha → `CurationLockedError`
  (exit 3). Gravação: temporário na mesma pasta + `os.replace` (padrão de `yaml_folder_registry`).
  Estado antes da gravação é lido e validado; JSON inválido ou `schema_version` desconhecida →
  `CurationStateCorruptError` (exit 1), sem sobrescrever.
- **Rationale**: FR-013/FR-014; `flock` é liberado pelo kernel se o processo morre (sem lock órfão).
- **Alternatives**: lockfile `O_EXCL` (fica órfão após crash).

## R7. Etapas e situação

- **Decision**: enum `Stage` com valores em inglês, como `CurationStatus`: `pending`, `triaged`,
  `drafted`, `reviewed`, `promoted`, `failed`, `discarded` (a etapa "ignorado" da spec), `removed`.
  Finais: `promoted`, `discarded`, `removed` e `reviewed` com `verdict == "accepted"`.
  Situação da pasta: `complete` | `incomplete` | `not_inventoried`.
- **Rationale**: evita confundir o descarte da triagem com a exclusão do FR-006 (esclarecimento
  de 25/09/2026).

## R8. CLI

- **Decision**: novo grupo `praxisforge curation`:
  - `curation inventory (<alias> | --all)` — exit 0 ok; 1 algum alias falhou/estado corrompido;
    2 uso (alias inexistente, sem alvo); 3 ambiente (pasta inacessível, lock ocupado).
  - `curation status [<alias>] [--json]` — tabela por etapa e situação; exit 0 (1 só se estado
    corrompido).
- **Rationale**: FR-001, FR-017, FR-021; mantém `folders` focado no registro.

## R9. Desempenho

- **Decision**: leitura em blocos de 64 KiB para hash, só dos arquivos não ignorados; sem
  paralelismo. Teste de desempenho com 5.000 arquivos pequenos gerados em `tmp_path` (marcador
  `slow`, limite 10 s).
- **Rationale**: SC-005 cabe com folga em I/O sequencial.
