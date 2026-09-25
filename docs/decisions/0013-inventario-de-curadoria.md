<!-- Criado em: 25/09/2026 14:59 -->
<!-- Modificado em: 25/09/2026 14:59 -->

# ADR 0013: Inventário de curadoria determinístico, fora do repositório

## Status

Aceito (25/09/2026). Feature 010-inventario-curadoria; primeira etapa da curadoria automatizada
(debate `docs/debates/curadoria-automatizada.md`), antes da triagem por LLM (011) e da revisão (012).

## Contexto

A curadoria manual do `agent_skills` gerou uma única skill: commands, agents, hooks, references e o
`CLAUDE.md` ficaram de fora sem registro. A automação precisa de uma base que não esqueça nada,
seja reproduzível e permita retomar e refazer só o que mudou.

## Decisão

- **Inventário sem LLM**: cada pasta registrada vira um manifesto com todo artefato (tipo, caminho,
  tamanho, SHA-256) e toda exclusão com motivo (lista fixa, `.gitignore`, > 256 KiB, binário,
  links, ilegível, texto fora das convenções). Manifesto ordenado e sem data.
- **Convenções fora do repositório**: `<dir do registro>/curation-conventions.yaml` (padrão
  `~/.config/praxisforge/`), validadas por `curation-conventions-schema-v1`; o repositório guarda
  só `src/data/curation-conventions.example.yaml`. Sem o arquivo, o inventário recusa e explica.
  Regras de diretório (skill com marker `SKILL.md`, `hooks`): o diretório mais externo é dono de
  toda a subárvore. `.md` sem regra → `unknown`; outro texto → excluído `uncurated`.
- **Estado por alias** em `<dir do registro>/curation/<alias>/{manifest,state}.json`, só com
  artefatos curáveis; reconciliação por hash (novo/alterado → `pending`, sumido → `removed`).
  A versão das convenções é o SHA-256 das regras: reclassificação volta para `pending`.
- **Robustez**: `fcntl.flock` por alias (segunda execução recusa), gravação temp + `os.replace`,
  validação ao ler e ao gravar; estado corrompido nunca é sobrescrito.
- **`pathspec`** (semântica gitignore) para `.gitignore` e padrões; o domínio recebe o matcher
  injetado e não depende da biblioteca.

## Alternativas descartadas

- Convenções no repositório: cada máquina ajusta as suas (decisão do curador, 25/09/2026).
- `git ls-files` para o `.gitignore`: exige work tree; pastas copiadas sem `.git` falhariam.
- Lockfile com `O_EXCL`: fica órfão após crash.
- Exclusões no estado (etapa "ignorado"): distorceria a contagem de "completa" (esclarecimento Q1).

## Consequências

- `curation inventory (<alias> | --all)` e `curation status [<alias>] [--json]`.
- A 011 lê o estado para triar só `pending`; a 012 atribui as etapas finais.
