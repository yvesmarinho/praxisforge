<!-- Criado em: 24/09/2026 16:52 -->
<!-- Modificado em: 24/09/2026 16:52 -->

# ADR 0009: Biblioteca de skills versionada

## Status

Aceito (24/09/2026). Origem: feature `008-biblioteca-skills` e Princípio VI da constituição v3.0.0.

## Contexto

O Princípio VI faz do repositório a fonte de verdade das skills: `skills/<nome>/SKILL.md` mais
os arquivos de apoio. Faltava definir três coisas: o formato aceito, como provar de onde veio o
conteúdo e como publicar sem sobrescrever o que o curador já tem em `~/.claude/skills/`.

## Decisão

- **Formato**: é o formato de skill do Claude. O frontmatter tem `name` (minúsculas e hífens, até
  64 caracteres, igual ao nome da pasta) e `description` (1 a 1024 caracteres). O praxisforge
  exige ainda `metadata.version` em semver e aceita `metadata.sources` (slugs de fonte) e
  `metadata.authored`. Outros campos na raiz, como `allowed-tools`, são permitidos. O contrato é
  `schemas/skill-frontmatter-v1.json`. Ele é versionado pelo nome do arquivo, já que o formato do
  Claude não tem `schema_version`. Por isso o validador só exige esse campo quando o schema o
  declara.
- **Proveniência (FR-006, FR-007 e FR-007a)**:
  - cada slug citado precisa existir uma única vez em `src/data/sources/**` e passar em
    `validate_sources` (feature 006);
  - uma skill sem fontes precisa de `authored: true`;
  - uma skill não autoral precisa de ao menos uma fonte `summary` ou `verbatim`.
- **Arquivos de apoio**: todo link relativo no corpo precisa existir dentro da pasta. Links
  absolutos, com `file:` ou que saem da pasta via `..` são falha. URLs `http`, `https`, `mailto`
  e âncoras são ignoradas.
- **Marcador de publicação**: é o arquivo `.praxisforge-skill.json`, com o schema
  `skill-publication-v1.json`. Guarda `name`, `version`, `content_sha256` e `source`
  (`skills/<nome>`, nunca um caminho de máquina). O hash é um SHA-256 sobre caminho relativo e
  bytes de cada arquivo, em ordem, sem o marcador e sem `__pycache__`.
- **O que é "nosso"**: uma cópia com marcador válido, ou um symlink que aponta para a pasta da
  skill no repositório. Todo o resto é terceiro, e o praxisforge nunca altera nem remove.
- **Regra de versão** (só na cópia):
  - mesmo hash → a skill fica `inalterada`;
  - hash diferente com a mesma versão → a publicação é recusada;
  - versão nova → a skill é `atualizada`.
  A troca entre cópia e symlink sempre publica.
- **Atomicidade**: a cópia vai para um diretório temporário no destino. O destino antigo, se for
  nosso, é afastado. Depois vem o `rename`, com rollback se falhar. O symlink usa um link
  temporário mais `os.replace`. Falha de I/O dá `SkillPublicationError` (exit 3).
- **Órfãs**: `--all` lista as skills publicadas pelo praxisforge que saíram do repositório. Só
  `--prune` as remove.
- **Catálogo**: `skills/README.md` é gerado em ordem alfabética, sem data. É o único `.md`
  dispensado do cabeçalho de datas, porque precisa ser determinístico (SC-002).

## Consequências

- `scripts/publish-skills` é o caminho de publicação exigido pelo Princípio VI. Ele entra na raiz
  do repositório e repassa os argumentos para `praxisforge skills publish`.
- O catálogo do vault Obsidian continua manual.
- Limitação herdada da feature 007: `skills`, `src/data/sources` e `schemas` são resolvidos a
  partir do diretório atual, e o script contorna isso.
