<!-- Criado em: 24/09/2026 14:36 -->
<!-- Modificado em: 24/09/2026 14:36 -->

# ADR 0008: Registro de pastas fora do repositório

## Status

Aceito (24/09/2026) — feature `007-registro-fora-do-repo`; constituição v3.0.0 (Princípio V).

## Contexto

Desde a feature 005 o registro de pastas guarda o caminho absoluto de cada pasta, ou seja, reflete
a máquina do curador. O repositório é **público**: versionar `src/data/folders.yaml` expunha a
estrutura de diretórios pessoal, e o guarda de caminhos pessoais falhava localmente sempre que o
registro estava populado.

## Decisão

- O registro real vive fora do repositório. Local resolvido nesta ordem:
  1. `--registry ARQUIVO`;
  2. `PRAXISFORGE_REGISTRY` (quando não vazia);
  3. `$XDG_CONFIG_HOME/praxisforge/folders.yaml` (quando a variável é absoluta; relativa é ignorada,
     como manda a especificação XDG);
  4. `~/.config/praxisforge/folders.yaml`.
  `~` e caminhos relativos de `--registry`/`PRAXISFORGE_REGISTRY` são expandidos/resolvidos.
- `add`, `bootstrap` e `relocate` criam a pasta do registro; os demais comandos falham com
  "registro ausente em <local>" (exit 1). Local que é diretório → exit 2.
- O repositório versiona só `src/data/folders.example.yaml` (caminhos fictícios em
  `/srv/praxisforge/`), validado em `make validate-data`; `src/data/folders.yaml` vai para o
  `.gitignore`. O guarda `test_no_absolute_paths` passa a olhar só o conteúdo **versionado**
  (`git ls-files`).
- `folders relocate [--from ARQ]` move o registro antigo (padrão `src/data/folders.yaml`) para o
  local resolvido: valida a origem (v1 → pede `folders migrate`; inválida → violações; sem pastas
  → recusa), nunca sobrescreve o destino, copia para um temporário, confere os bytes, troca de
  forma atômica e só então remove a origem. Falha de I/O → exit 3 com a origem intacta.
- Enquanto o registro resolvido não existir e houver um registro antigo com pastas no diretório
  atual, os comandos de leitura sugerem `folders relocate`.
- `relocate` (mover o arquivo) é distinto de `migrate` (converter v1 → v2).

## Consequências

- Gates locais e de CI passam com o registro pessoal populado.
- Outros clones: como `src/data/folders.yaml` saiu do versionamento, atualizar um clone cujo arquivo
  não foi modificado localmente o remove — rodar `folders relocate` **antes** de atualizar.
- Limitação mantida: a CLI procura `schemas/` e o registro antigo a partir do diretório atual
  (deve ser executada na raiz do projeto).

## Alternativas rejeitadas

- Arquivo local ignorado dentro do repositório (`folders.local.yaml`): mantinha o dado pessoal na
  árvore do projeto e o guarda de caminhos pessoais continuaria sensível a ele.
- Caminhos relativos a uma raiz, versionados: revertia parte da feature 005 e exigia nova versão do
  schema.
- Migração automática ao detectar o registro antigo: ação implícita sobre dados do usuário.
