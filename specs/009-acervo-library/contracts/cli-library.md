<!-- Criado em: 25/09/2026 12:21 -->
<!-- Modificado em: 25/09/2026 12:22 -->

# Contrato: CLI `praxisforge library`

Códigos de saída: `0` ok · `1` falha de validação/negócio · `2` uso · `3` ambiente (I/O, raiz do
projeto não encontrada, `library/` ausente).

## `library validate [--type T] [<nome>]`

| Entrada | Efeito |
|---------|--------|
| sem argumentos | valida todos os itens de todos os tipos |
| `--type T` | valida só o tipo `T` (skill, command, agent, hook, rule, reference) |
| `--type T <nome>` | valida um item |
| `<nome>` sem `--type` | erro de uso (2) |
| tipo desconhecido | erro de uso (2) |

Saída: uma linha por falha, `<kind>/<nome>: <motivo>`; uma linha por item com reescrita pendente,
`<kind>/<nome>: reescrita pendente`; resumo final `N ok, M com falha`.
Arquivos fora de um diretório de tipo conhecido → `?/<caminho>: tipo desconhecido` (conta como falha).

## `library index`

Gera `library/INDEX.md` (determinístico). Saída: `índice: N itens (M omitidos)` e, por omitido,
`<kind>/<nome>: <motivo>`. Falha de gravação → 3; o índice anterior permanece.

## `library publish (--type T <nome> | --all) --target <pasta> [--mode copy|symlink] [--prune]`

| Situação | Resultado |
|----------|-----------|
| `--target global` | 2: "publicação só em pastas de projeto" |
| tipo `hook` ou `reference` | 2: tipo não publicável (motivo) |
| `--prune` sem `--all` | 2 |
| item inválido | não publicado; reportado; código final 1 |
| item de terceiro no destino | intocado; reportado como recusa; código final 1 |
| tudo publicado ou já em dia | 0 |
| falha de I/O | 3 |

Destinos em `<pasta>/.claude/`: `skills/<nome>/`, `commands/<nome>.md`, `agents/<nome>.md`,
`rules/<nome>.md`. `--all` publica todos os tipos publicáveis.

## `skills validate|catalog|publish` (removidos)

Qualquer uso → 2 com a mensagem: `comando removido — use: praxisforge library <equivalente>`
(`catalog` → `index`).

## Contratos de dados (JSON Schema, `schemas/`)

| Arquivo | Status |
|---------|--------|
| `skill-frontmatter-v1.json` | alterado (aditivo): `metadata.references`, `metadata.rewrite_pending` |
| `command-frontmatter-v1.json` | novo |
| `agent-frontmatter-v1.json` | novo |
| `rule-frontmatter-v1.json` | novo |
| `hook-frontmatter-v1.json` | novo |
| `reference-frontmatter-v1.json` | novo |
| `library-publication-v1.json` | novo (sucede `skill-publication-v1`, que continua lido) |
| `source-schema-v3.json` | novo, breaking (sem níveis de extração) |
