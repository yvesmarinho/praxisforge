<!-- Criado em: 22/09/2026 16:15 -->
<!-- Modificado em: 22/09/2026 13:52 -->

# Guia — Operar a CLI `praxisforge` (estado atual: features 001 + 002)

Este guia documenta **o que já existe e funciona hoje** na CLI `praxisforge`, antes da feature
003 (descoberta de fontes dentro de pastas registradas, ainda em especificação). Cobre as duas
features já implementadas e mergeadas em `main`:

- **001 — Registro de Pastas a Curar**: cadastro de pastas externas (fora do repo) via alias,
  contratos JSON Schema versionados.
- **002 — Varredura das Pastas Registradas**: confirma acessibilidade e atualiza `status`/
  `last_scanned` das pastas já registradas.

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
  --status not_scanned
```

- `--alias`: obrigatório, único (repetir com os mesmos dados é idempotente; com dados diferentes,
  é recusado).
- `--description`: obrigatório, texto livre (1-500 caracteres).
- `--content-type`: obrigatório, slug (ex.: `documents`, `repository_forks`).
- `--license`: obrigatório — identificador SPDX (ex.: `MIT`) ou `unknown` se ainda não souber (aí
  o status fica automaticamente `pending`, independente do `--status` informado).
- `--status`: opcional, padrão `not_scanned`.

**Exit codes**: `0` registrado/inalterado · `1` regra de negócio violada (ex.: alias já existe com
dados diferentes) · `2` argumento inválido/ausente.

### 2. Apontar o alias para o caminho real (variável de ambiente)

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

**Exit codes**: `0` ok · `1` alias não registrado (individual) ou houve falha em algum item (modo
`--all`) · `3` variável ausente/caminho inválido/sem permissão (modo individual).

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
  caminho existe e é legível. Descobrir o que tem dentro é a feature 003 (ainda não implementada).
- No modo `--all`, falha de uma pasta não impede as demais; o resumo final mostra quantas foram
  atualizadas e quantas falharam, e também lista grupos de aliases que apontam para o **mesmo
  caminho real** (duplicidade, só informativo).

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

**Exit codes**: `0` ok · `1` regra de negócio violada (ex.: `last_scanned` no futuro, tentar mudar
status sem resolver licença `unknown`) · `2` argumento inválido.

### 7. Validar o registro inteiro contra o contrato

```bash
uv run praxisforge folders validate
```

Valida cada pasta do YAML contra `schemas/folders-schema-v1.json`; reporta falha por item sem
interromper a validação das demais.

### 8. Validar arquivos de proveniência de fontes (frontmatter)

```bash
uv run praxisforge sources validate src/data/sources/
# ou arquivos específicos
uv run praxisforge sources validate src/data/sources/papers/exemplo.md
```

Valida o frontmatter YAML de arquivos `.md` contra `schemas/source-schema-v1.json`. **Nota**: hoje
não existe nenhum caso de uso que *crie* esses arquivos automaticamente — eles são escritos à mão
pelo curador; este comando só valida o que já foi escrito.

## Referência rápida de exit codes (toda a CLI)

| Código | Significado |
|---|---|
| 0 | sucesso |
| 1 | falha de validação/regra de negócio (alias inexistente, dado inválido, falha de item em lote) |
| 2 | uso incorreto da CLI (argumento ausente/inválido) |
| 3 | falha de ambiente (variável de caminho ausente, caminho inválido ou sem permissão) |

## O que a CLI **não** faz hoje

- Não descobre pastas sozinha — todo registro é manual (`folders add`).
- Não olha dentro de uma pasta registrada — `folders scan` só confirma que o caminho existe.
- Não cria arquivos de fonte em `src/data/sources/` automaticamente — proveniência é sempre
  escrita manualmente (só a validação de schema existe, passo 8).
- Não agenda varreduras — toda execução é manual, disparada por você.

Essas lacunas são o escopo da feature 003 (`specs/003-descoberta-fontes-pastas/spec.md`, em
especificação) e de features futuras de curadoria/proveniência.

## Referências

- [`docs/architecture/overview.md`](../architecture/overview.md) — camadas e decisões de design
- [`specs/001-registro-pastas-curadoria/quickstart.md`](../../specs/001-registro-pastas-curadoria/quickstart.md)
- [`specs/002-varredura-pastas-curadoria/quickstart.md`](../../specs/002-varredura-pastas-curadoria/quickstart.md)
