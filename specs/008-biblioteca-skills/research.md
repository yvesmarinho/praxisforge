<!-- Criado em: 24/09/2026 15:12 -->
<!-- Modificado em: 24/09/2026 15:12 -->

# Research: Biblioteca de skills versionada

## R1 — Formato do SKILL.md

- **Decision**: frontmatter YAML entre `---` (mesmo leitor seguro das fontes, sem timestamp);
  campos: `name` (`^[a-z0-9]+(-[a-z0-9]+)*$`, ≤ 64), `description` (1–1024), `license`
  (opcional), `metadata` (objeto; praxisforge exige `version` semver e aceita `sources: [slug]`,
  `authored: bool`). Outros campos do formato do Claude (ex.: `allowed-tools`) são permitidos
  (`additionalProperties: true` na raiz; `metadata` com as chaves conhecidas tipadas).
- **Rationale**: compatível com as skills do Claude (ex.: `~/.claude/skills/doc-python`).
- **Alternatives**: arquivo de metadados separado (`skill.yaml`) — duplicaria nome/descrição.

## R2 — Semver

- **Decision**: regex oficial semver 2.0 (com pré-release/build opcionais), só stdlib.
- **Alternatives**: pacote `semver` — dependência nova para uma regex.

## R3 — Arquivos referenciados

- **Decision**: links Markdown `[texto](alvo)` e `![alt](alvo)` no corpo; ignorar alvos com
  esquema (`http:`, `https:`, `mailto:`), âncoras puras (`#...`) e remover `#fragmento`; alvo
  resolvido relativo à pasta da skill; `..` que sai da pasta → falha; inexistente → falha.
- **Rationale**: é o mecanismo de referência a arquivos de apoio usado nas skills do Claude.

## R4 — Proveniência

- **Decision**: índice de fontes = `src/data/sources/**/<slug>.md` → slug (nome sem `.md`); slug em
  duas categorias → falha "slug ambíguo". Cada fonte citada é validada pelo caso de uso
  `validate_sources` (006) e sua `extract_policy` lida do frontmatter; regra FR-007/FR-007a no
  caso de uso `validate_skills`.
- **Rationale**: reaproveita schema v2 + regra de licença; o domínio da skill não depende de fontes.

## R5 — Identificação do que o praxisforge publicou

- **Decision**: cópia → arquivo `.praxisforge-skill.json` dentro do destino:
  `{schema_version:"1", name, version, content_sha256, source}` (`source` = caminho relativo
  `skills/<nome>`, sem caminho de máquina). Symlink → alvo resolvido igual à pasta da skill no
  repositório. Qualquer outra pasta/arquivo de mesmo nome = terceiro (`ForeignSkillDestinationError`).
- **Rationale**: verificável no próprio destino (FR-014); hash permite "inalterada" e a regra de
  versão (FR-013) sem comparar arquivo a arquivo.
- **Hash**: SHA-256 sobre (caminho relativo, bytes) de todos os arquivos da skill em ordem
  lexicográfica, ignorando o próprio marcador e `__pycache__`.

## R6 — Atomicidade da publicação

- **Decision**: cópia para `<destino>/.<nome>.tmp-XXXX`, grava marcador, remove o destino antigo
  (se nosso) e `rename`; em falha remove o temporário e mantém o antigo. Symlink: cria
  `.<nome>.lnk-XXXX` e `os.replace`. `OSError` → `SkillPublicationError` (exit 3).
- **Rationale**: FR-015 (sem publicação parcial).

## R7 — Regra de versão

- **Decision**: marcador com mesmo `content_sha256` → inalterada; hash diferente e mesma
  `version` → `SkillVersionNotBumpedError` (exit 1); versão diferente → atualiza. Troca de modo
  (cópia ↔ symlink) sempre permitida entre destinos nossos. Symlink: sem regra de versão.

## R8 — Catálogo

- **Decision**: `skills/README.md` com cabeçalho fixo (comentário "gerado — não editar") e tabela
  `| Skill | Propósito | Versão | Caminho | Fontes |`, ordem alfabética, descrição em uma linha
  (quebras → espaço, `|` escapado), fontes ordenadas ou "autoral"; escrita atômica; sem data.
- **Nota**: o cabeçalho de datas exigido nos `.md` do projeto é dispensado aqui por ser arquivo
  gerado determinístico (registrar no ADR).

## R9 — Destino global nos testes

- **Decision**: fixture autouse define `HOME=<tmp>/home` para toda a suíte (além do XDG da 007);
  o global é `Path.home()/.claude/skills` resolvido na CLI.

## R10 — scripts/publish-skills

- **Decision**: bash com shebang, cabeçalho de datas, `set -euo pipefail`, `cd` para a raiz do repo
  (diretório do script/..), `exec uv run praxisforge skills publish "$@"`.
