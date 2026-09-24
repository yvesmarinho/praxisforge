<!-- Criado em: 18/09/2026 15:56 -->
<!-- Modificado em: 24/09/2026 14:36 -->

# Praxisforge

[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![GitHub Flow](https://img.shields.io/badge/Workflow-GitHub%20Flow-blue.svg)](https://docs.github.com/en/get-started/quickstart/github-flow)
![Branch Protection](https://img.shields.io/badge/Branch%20Protection-Recommended-green)

> Curadoria e engenharia de agentes para Claude — pesquisa, síntese e refino contínuo de conhecimento aplicado ao desenvolvimento de agentic AI.

**Domínio**: programming | **Linguagem**: python
**Criado em**: 2026-09-18T18:56:11Z
**Repositório**: [git@github.com:yvesmarinho/praxisforge.git](git@github.com:yvesmarinho/praxisforge.git)

---

## 🚀 Início Rápido

```bash
# Instalar dependências
make install-deps

# Iniciar desenvolvimento
make dev
```

## 📚 Documentação

- [Índice](docs/INDEX.md)
- [Tarefas](docs/TODO.md)

## 🤝 Contribuindo

Este projeto segue as melhores práticas de Git/GitHub para garantir qualidade e colaboração eficiente.

### Workflow Git

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) para:
- Convenções de branches (`feature/NNN-descricao`, `fix/descricao`)
- Padrões de commits (Conventional Commits)
- Processo de Pull Request
- Estratégias de merge
- Proteção de branches

### Configuração de Branch Protection

Para configurar proteção de branches no GitHub, consulte [docs/BRANCH_PROTECTION_SETUP.md](docs/BRANCH_PROTECTION_SETUP.md).

## 🏗️ Estrutura

Consulte os [documentos de arquitetura](docs/) para detalhes.

## 🧰 CLI `praxisforge` — funcionalidades

A CLI mantém o **registro de pastas a curar** (onde está cada fonte, licença, status de curadoria)
e valida os **registros de fonte** (proveniência e política de extração). Execute sempre com
`uv run praxisforge ...`. Guia completo: [docs/guides/operar-cli-praxisforge.md](docs/guides/operar-cli-praxisforge.md).

**Opções globais**: `--registry ARQUIVO` (registro a usar; hoje o padrão é `src/data/folders.yaml`,
que passará para fora do repositório com a feature 007) e `--log-level NÍVEL`.

### Registro de pastas (`folders`)

| Comando | O que faz |
|---|---|
| `folders add --alias A --description D --content-type T --license L --path P [--status S]` | Registra uma pasta com caminho absoluto (único, sem aninhamento); cria o registro se não existir |
| `folders list [--status S]` | Lista alias, tipo, licença, status, política máxima de extração, última varredura e caminho |
| `folders show A` | Detalhes de uma pasta, incluindo versão curada e política máxima de extração |
| `folders update A [--status S] [--last-scanned DATA] [--license L] [--path P]` | Atualiza metadados; `--status curated` grava a versão (HEAD do git) curada |
| `folders resolve A \| --all` | Confere se o caminho registrado existe e é legível (não altera nada) |
| `folders scan A \| --all` | Varre as pastas: atualiza status/última varredura e reverte `curated` → `in_curation` quando o conteúdo mudou desde a curadoria |
| `folders bootstrap RAIZ` | Registra as subpastas de 1º nível da raiz ainda ausentes (alias `<raiz>__<subpasta>`, descrição e licença detectadas de README/LICENSE) |
| `folders validate` | Valida o registro inteiro contra o contrato (`folders-schema-v2`) |
| `folders migrate [--root RAIZ]` | Converte um registro antigo (v1, caminho por variável de ambiente) para o v2 |

**Status de curadoria**: `not_scanned` (não varrida), `scanned` (varrida), `in_curation` (em
curadoria), `curated` (curada), `pending` (pendente — licença desconhecida) e `ignore` (ignorada
por bootstrap e varredura em lote).

### Registros de fonte (`sources`)

| Comando | O que faz |
|---|---|
| `sources validate CAMINHO...` | Valida arquivos `.md` (diretórios recursivamente) contra `source-schema-v2` e a política de extração por licença |

**Política de extração** (`extract_policy`): `link` (só referência) < `summary` (síntese própria +
citações curtas) < `verbatim` (cópia literal com aviso de copyright e licença). A máxima depende da
licença: MIT/BSD-3-Clause/Apache-2.0 → `verbatim`; GPL-3.0 → `verbatim` só para documentação, senão
`summary`; Elastic-2.0 → `summary`; `unknown`/não classificada → `link`. Detalhes em
[ADR 0007](docs/decisions/0007-politica-de-extracao-por-licenca.md) e
[docs/reference/sources-frontmatter.md](docs/reference/sources-frontmatter.md).

### Códigos de saída

`0` sucesso · `1` falha de validação/regra de negócio · `2` uso incorreto · `3` falha de ambiente
(caminho inválido, sem permissão, falha do `git`).

### Atualização — registro fora do repositório (feature 007)

- O registro de pastas real **não fica mais no repositório**: por padrão
  `$XDG_CONFIG_HOME/praxisforge/folders.yaml` (ou `~/.config/praxisforge/folders.yaml`).
  Precedência: `--registry` > `PRAXISFORGE_REGISTRY` > XDG > `~/.config`.
- O repositório versiona apenas o exemplo `src/data/folders.example.yaml`.
- Novo comando: `folders relocate [--from ARQUIVO]` — move um registro antigo
  (`src/data/folders.yaml`) para o novo local, validando a origem e sem sobrescrever o destino.
  Rode-o **antes** de atualizar outros clones. Detalhes em
  [ADR 0008](docs/decisions/0008-registro-fora-do-repositorio.md).

