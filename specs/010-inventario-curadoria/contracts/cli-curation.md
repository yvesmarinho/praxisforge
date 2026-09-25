<!-- Criado em: 25/09/2026 14:35 -->
<!-- Modificado em: 25/09/2026 14:40 -->

# Contrato da CLI: `praxisforge curation`

Opção global herdada: `--registry <arquivo>` (define também onde fica `curation/`).

## `curation inventory <alias> | --all`

Inventaria uma pasta registrada (ou todas, exceto `ignore`) e grava
`<dir do registro>/curation/<alias>/{manifest.json,state.json}`.

Saída (stdout, uma linha por pasta):

```text
<alias>: <N> artefatos (<k> pendentes, <r> removidos), <e> excluídos — incompleta
<alias>: FALHA — <motivo sem caminho absoluto>
Resumo: <ok> inventariadas, <f> falharam, <s> puladas (ignore)
```

| Exit | Quando |
|---|---|
| 0 | todas inventariadas |
| 1 | estado corrompido/versão desconhecida; convenções inválidas; em `--all`, ≥ 1 pasta falhou |
| 1 | alias inexistente (mesmo padrão de `folders scan`) |
| 2 | uso: sem alvo, `<alias>` e `--all` juntos |
| 3 | ambiente: pasta inacessível (alias único), lock ocupado, registro ilegível, convenções ausentes |

Garantias: nenhuma escrita na pasta inventariada nem no repositório (FR-008, SC-006); em falha,
o estado anterior fica intacto.

## `curation status [<alias>] [--json]`

Sem alias: todas as pastas registradas (exceto `ignore`).

```text
ALIAS            SITUAÇÃO         PEND TRIA RASC REVI PROM FALH DESC REMO
agent_skills     incompleta         41    0    0    0    0    0    0    2
karpathy_skills  sem inventário      -    -    -    -    -    -    -    -
```

Com alias, lista também as falhas (`path: last_error`). `--json` emite
`{"folders":[{"alias","situation","counts":{stage:int},"failures":[{"path","error"}]}]}`.

| Exit | Quando |
|---|---|
| 0 | consulta feita (qualquer situação) |
| 1 | algum estado corrompido (mostrado como `estado inválido`) |
| 1 | alias inexistente |
| 3 | registro ilegível |

## Convenções

`<dir do registro>/curation-conventions.yaml` — padrão `~/.config/praxisforge/curation-conventions.yaml`
(schema `curation-conventions-schema-v1`). Ausente → exit 3 com a instrução
`cp src/data/curation-conventions.example.yaml ~/.config/praxisforge/curation-conventions.yaml`.
Conteúdo do exemplo
(ordem = prioridade):

Regras `directory` casam o caminho do diretório; o diretório mais externo que casar é dono de
tudo abaixo dele (arquivos de apoio, `CLAUDE.md` interno etc. não viram artefatos próprios).

| kind | pattern | unit |
|---|---|---|
| skill | `**/skills/*` (marker `SKILL.md`) | directory |
| hook | `**/hooks` | directory |
| command | `**/commands/**/*.md` | file |
| agent | `**/agents/*.md` | file |
| rule | `**/rules/*.md` | file |
| reference | `**/references/*.md` | file |
| project_instruction | `**/CLAUDE.md`, `**/AGENTS.md` | file |

Resto: `.md` → `unknown`; outro texto → excluído `uncurated`.
