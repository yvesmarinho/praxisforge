<!-- Criado em: 22/09/2026 16:15 -->
<!-- Modificado em: 23/09/2026 17:05 -->

# Guia — Operar a CLI `praxisforge` (estado atual: features 001 + 002 + 003)

Este guia documenta **o que já existe e funciona hoje** na CLI `praxisforge`. Cobre as três
features já implementadas e mergeadas em `main`:

- **001 — Registro de Pastas a Curar**: cadastro de pastas externas (fora do repo) via alias,
  contratos JSON Schema versionados.
- **002 — Varredura das Pastas Registradas**: confirma acessibilidade e atualiza `status`/
  `last_scanned` das pastas já registradas.
- **003 — Bootstrap do Registro de Pastas**: gera o registro inicial a partir de uma pasta-raiz,
  lendo README/LICENSE de cada subpasta; adiciona o status `ignore` para excluir pastas
  permanentemente de bootstrap/varredura futuros.

## Pré-requisitos

- Python 3.12+ com `uv` instalado.
- Ambiente do projeto instalado: `uv sync` (uma vez, a partir da raiz do repositório).
- Todos os comandos abaixo assumem `cd` para a raiz do repositório (`praxisforge/`).

## Conceitos-chave antes de operar

- **Alias**: identificador curto (`^[a-z][a-z0-9_]{1,62}$`) que representa uma pasta externa —
  nunca o caminho em si. Ex.: `github_forks`.
- **Registro** (`src/data/folders.yaml` por padrão): arquivo YAML versionado no repo, guarda os
  metadados de cada alias (descrição, tipo de conteúdo, licença, status, última varredura) — mas
  **nunca o caminho real**.
- **Resolução de caminho**: o caminho real de cada alias vem de uma variável de ambiente
  `PRAXISFORGE_FOLDER_<ALIAS_MAIÚSCULO>`, nunca do YAML. Isso existe para o registro poder ser
  versionado no git sem vazar caminhos absolutos da sua máquina.
- **`--registry`**: toda invocação da CLI aceita `--registry <caminho>` para apontar para um
  arquivo de registro diferente do padrão (`src/data/folders.yaml`). Útil para testes manuais sem
  tocar o dado real do projeto.

## Passo a passo

### 1. Registrar uma pasta a curar

```bash
uv run praxisforge folders add \
  --alias meu_alias \
  --description "Descrição do que essa pasta contém" \
  --content-type documents \
  --license MIT \
  --status not_scanned \
  --path ~/DevOps/github_forks/meu_repo
```

- `--alias`: obrigatório, único (repetir com os mesmos dados é idempotente; com dados diferentes,
  é recusado).
- `--description`: obrigatório, texto livre (1-500 caracteres).
- `--content-type`: obrigatório, slug (ex.: `documents`, `repository_forks`).
- `--license`: obrigatório — identificador SPDX (ex.: `MIT`) ou `unknown` se ainda não souber (aí
  o status fica automaticamente `pending`, independente do `--status` informado).
- `--status`: opcional, padrão `not_scanned`.
- `--path`: obrigatório (feature 005) — aceita `~`, relativo e links; é gravado na forma absoluta
  canônica. Recusado se não existir, não for pasta, não puder ser listado, já estiver registrado
  (mesmo com outras maiúsculas) ou estiver dentro de/contiver outra pasta registrada.

**Exit codes**: `0` registrado/inalterado · `1` regra de negócio violada (ex.: alias ou caminho já
registrado, aninhamento) · `2` argumento inválido/ausente · `3` caminho inexistente/sem permissão.

### 2. ~~Apontar o alias para o caminho real (variável de ambiente)~~ — removido na feature 005

Desde a feature 005 o caminho fica no próprio registro (`--path`); nenhuma variável é necessária.
Registros antigos (v1) são convertidos com `folders migrate` (passo 11). O texto abaixo é histórico.

```bash
export PRAXISFORGE_FOLDER_MEU_ALIAS=/caminho/real/da/pasta
```

O nome da variável é sempre `PRAXISFORGE_FOLDER_` + o alias em maiúsculo. Isso não é feito pela
CLI — é responsabilidade sua, tipicamente no `~/.bashrc`/`~/.zshrc` ou em um `.env` **não
versionado**.

### 3. Consultar o que já está registrado

```bash
# lista todas as pastas (alias, tipo, licença, status, última varredura)
uv run praxisforge folders list

# filtra por status
uv run praxisforge folders list --status pending

# detalhe de uma pasta
uv run praxisforge folders show meu_alias
```

### 4. Confirmar o caminho resolvido (sem alterar nada)

```bash
# um alias
uv run praxisforge folders resolve meu_alias

# todos os aliases
uv run praxisforge folders resolve --all
```

Só imprime o caminho real (ou o motivo da falha); não toca no registro. Útil para depurar
variáveis de ambiente antes de rodar uma varredura.

- **Verificação de conteúdo (feature 004)**: para pasta `curated` que é repositório git, a
  varredura compara os arquivos **da própria pasta** entre o commit gravado na curadoria e o HEAD
  atual. Mudou → status volta para `in_curation`. Cada pasta mostra a linha/coluna `conteúdo:`
  (`-`, `não verificado (não é repositório git)`, `referência registrada`, `sem mudança`,
  `mudou — revertida para em curadoria`) e o `--all` termina com `revertidas: N (aliases)`.
  Pasta curada antiga sem commit gravado recebe o HEAD como referência na primeira varredura.

**Exit codes**: `0` ok · `1` alias não registrado (individual) ou houve falha em algum item (modo
`--all`) · `3` variável ausente/caminho inválido/sem permissão/falha do `git` (modo individual).

### 5. Varrer (atualizar status/última varredura)

```bash
# uma pasta
uv run praxisforge folders scan meu_alias

# todas de uma vez
uv run praxisforge folders scan --all
```

- Pasta com status `not_scanned` → avança para `scanned` e grava `last_scanned`.
- Qualquer outro status (`scanned`, `in_curation`, `curated`, `pending`) → **mantém o status**, só
  atualiza `last_scanned`. Pastas `pending` (licença `unknown`) continuam `pending` mesmo depois de
  varridas — resolver a licença é sempre manual (passo 6).
- A varredura **não entra dentro da pasta**: não lista arquivos nem subpastas, só confirma que o
  caminho existe e é legível.
- No modo `--all`, falha de uma pasta não impede as demais; o resumo final mostra quantas foram
  atualizadas, quantas falharam e quantas foram **ignoradas** (pastas com `status: ignore`, ver
  passo 9), e também lista grupos de aliases que apontam para o **mesmo caminho real**
  (duplicidade, só informativo).
- Pastas com `status: ignore` são puladas automaticamente no modo `--all` (o caminho delas nem é
  conferido). A varredura **individual** explícita
  (`folders scan <alias>`) continua funcionando normalmente mesmo para um alias `ignore`.

**Exit codes**: `0` ok · `1` alias não registrado (individual) ou houve falha em algum item (modo
`--all`) · `3` variável ausente/caminho inválido/sem permissão (modo individual).

### 6. Atualizar metadados manualmente

```bash
uv run praxisforge folders update meu_alias \
  --license MIT \
  --status scanned \
  --last-scanned 2026-09-22T12:00:00-03:00
```

Todos os campos são opcionais — só os informados são alterados, o resto permanece igual. Use isso
para: resolver uma licença `unknown` (o que tira a pasta do status `pending`), forçar um status
manualmente, ou corrigir `last_scanned`.

Ao usar `--status curated`, o caminho da pasta precisa estar configurado
(`PRAXISFORGE_FOLDER_<ALIAS>`): se for repositório git, o HEAD é gravado e a saída mostra
`versão curada: <12 caracteres>`; senão, `versão curada: (pasta não é repositório git)`.
`folders show` exibe a versão curada gravada.

**Exit codes**: `0` ok · `1` regra de negócio violada (ex.: `last_scanned` no futuro, tentar mudar
status sem resolver licença `unknown`) · `2` argumento inválido · `3` marcar `curated` com caminho
não configurado/inválido ou falha do `git`.

### 7. Gerar o registro inicial a partir de uma pasta-raiz (bootstrap)

```bash
uv run praxisforge folders bootstrap ~/DevOps
```

- Lista as subpastas de primeiro nível de `~/DevOps` e registra como novas todas as que ainda
  não existem no registro — nunca sobrescreve uma pasta já registrada (idempotente: rodar de novo
  só adiciona pastas novas que apareceram desde a última execução).
- Para cada subpasta nova, tenta extrair `description` do README e `license` do LICENSE
  (heurística reconhecendo MIT/Apache-2.0/GPL-3.0/BSD-3-Clause); sem reconhecimento confiável, fica
  `license: unknown` / `status: pending` (mesma regra do passo 1).
- `content_type` recebe um valor genérico (`unclassified`) — ajuste manualmente depois com
  `folders update` conforme for curando cada pasta.
- O resumo final mostra quantas pastas foram registradas, quantas já existiam (puladas), quantas
  estavam marcadas `ignore` (puladas) e quantas falharam individualmente (ex.: nome de subpasta
  que não vira um alias válido).

**Exit codes**: `0` ok (mesmo com falhas de item individuais) · `1` a própria pasta-raiz é
inválida/inacessível.

### 8. Excluir uma pasta permanentemente de bootstrap/varredura (`status: ignore`)

```bash
uv run praxisforge folders update meu_alias --status ignore
```

- Marca a pasta como `ignore` — o bootstrap nunca mais a reprocessa, e `folders scan --all` a pula
  automaticamente (sem exigir a variável de ambiente correspondente).
- Aceito mesmo com licença `unknown` (não exige que a pasta esteja `pending` antes).
- **Nunca aplicado automaticamente** — só via `folders update`, sempre decisão manual do curador.
- Para reverter, use `folders update meu_alias --status <outro status>`.

### 9. Validar o registro inteiro contra o contrato

```bash
uv run praxisforge folders validate
```

Valida cada pasta do YAML contra `schemas/folders-schema-v1.json`; reporta falha por item sem
interromper a validação das demais.

### 10. Validar arquivos de proveniência de fontes (frontmatter)

```bash
uv run praxisforge sources validate src/data/sources/
# ou arquivos específicos
uv run praxisforge sources validate src/data/sources/papers/exemplo.md
```

Valida o frontmatter YAML de arquivos `.md` contra `schemas/source-schema-v1.json`. **Nota**: hoje
não existe nenhum caso de uso que *crie* esses arquivos automaticamente — eles são escritos à mão
pelo curador; este comando só valida o que já foi escrito.

**Exit codes**: `0` ok · `1` falha de validação em pelo menos um item.

### 11. Migrar um registro antigo (v1 → v2, feature 005)

```bash
uv run praxisforge folders migrate --root ~/DevOps/github_forks
```

- Para cada pasta, o caminho vem da variável antiga `PRAXISFORGE_FOLDER_<ALIAS>` (se existir) ou
  da subpasta de `--root` cujo nome normalizado é igual ao alias; a própria raiz registrada como
  pasta é **removida** (sem aninhamento).
- Aliases e todos os demais dados são preservados. Só grava se **nenhuma** pasta ficar pendente;
  pendências são listadas com o motivo (sem caminho, ambíguo, duplicado, entrada inválida).
- Rodar de novo num registro já v2 não altera nada.

**Exit codes**: `0` migrado ou já atual · `1` há pendências (nada gravado) ou registro inválido.

### 12. Corrigir o caminho de uma pasta movida

```bash
uv run praxisforge folders update meu_alias --path /novo/local/meu_repo
```

Mesmas validações do `add`; status, licença e versão curada são preservados.

## Referência rápida de exit codes (toda a CLI)

| Código | Significado |
|---|---|
| 0 | sucesso |
| 1 | falha de validação/regra de negócio (alias inexistente, dado inválido, falha de item em lote) |
| 2 | uso incorreto da CLI (argumento ausente/inválido) |
| 3 | falha de ambiente (variável de caminho ausente, caminho inválido, sem permissão ou falha do `git`) |

## O que a CLI **não** faz hoje

- Não olha dentro de uma pasta registrada além do primeiro nível — o bootstrap não desce
  recursivamente em subpastas de subpastas, e `folders scan` só confirma que o caminho existe.
- Não cria arquivos de fonte em `src/data/sources/` automaticamente — proveniência é sempre
  escrita manualmente (só a validação de schema existe, passo 10).
- Não agenda bootstrap nem varreduras — toda execução é manual, disparada por você.
- ~~Não detecta quando o conteúdo de uma pasta já curada mudou~~ — resolvido na feature 004
  (ver passo 5); pastas fora de repositório git continuam sem essa verificação.

Essas lacunas são candidatas a features futuras de curadoria/proveniência (ver `docs/TODO.md`).

## Referências

- [`docs/architecture/overview.md`](../architecture/overview.md) — camadas e decisões de design
- [`docs/reference/folders-yaml.md`](../reference/folders-yaml.md) — estrutura de `folders.yaml`
- [`specs/001-registro-pastas-curadoria/quickstart.md`](../../specs/001-registro-pastas-curadoria/quickstart.md)
- [`specs/002-varredura-pastas-curadoria/quickstart.md`](../../specs/002-varredura-pastas-curadoria/quickstart.md)
- [`specs/003-bootstrap-registro-pastas/quickstart.md`](../../specs/003-bootstrap-registro-pastas/quickstart.md)
