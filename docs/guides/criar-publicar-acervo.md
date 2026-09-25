<!-- Criado em: 24/09/2026 16:52 -->
<!-- Modificado em: 25/09/2026 13:13 -->

# Criar, validar e publicar itens do acervo

O acervo `library/` guarda seis tipos de recurso: **skills**, **commands**, **agents**, **hooks**,
**rules** e **references**. Este guia cobre o fluxo completo: criar a partir do template, validar,
gerar o índice e publicar num projeto. Decisões: [ADR 0011](../decisions/0011-acervo-library.md)
(acervo) e [ADR 0012](../decisions/0012-fontes-so-ideias.md) (só ideias). Os comandos rodam de
qualquer subpasta do repositório; fora dele, defina `PRAXISFORGE_ROOT`
([ADR 0010](../decisions/0010-raiz-do-projeto-por-marcador.md)).

## 1. Criar

| Tipo | Template | Destino | Nome vem de |
|------|----------|---------|-------------|
| skill | `library/_templates/skill/` | `library/skills/<nome>/SKILL.md` | `name` = pasta |
| command | `library/_templates/command.md` | `library/commands/<nome>.md` | arquivo |
| agent | `library/_templates/agent.md` | `library/agents/<nome>.md` | `name` = arquivo |
| hook | `library/_templates/hook/` | `library/hooks/<nome>/HOOK.md` + scripts | `name` = pasta |
| rule | `library/_templates/rule.md` | `library/rules/<nome>.md` | arquivo |
| reference | `library/_templates/reference.md` | `library/references/<nome>.md` | `name` = arquivo |

```bash
cp -r library/_templates/skill library/skills/minha-skill
cp library/_templates/command.md library/commands/revisar.md
```

Todo item declara em `metadata`:

- `version`: semver, incrementada a cada mudança de conteúdo;
- `sources`: slugs de `src/data/sources/<categoria>/<slug>.md` cujas **ideias** originaram o item
  (nunca texto copiado, traduzido ou parafraseado de perto), ou `authored: true` sem fontes;
- `rewrite_pending: true` (opcional): marca um item antigo que é obra derivada e precisa ser
  reescrito; é só informativo.

Só skills citam references (`metadata.references: [<nome>]`) e arquivos de apoio por link relativo.
Commands, agents, rules e references são arquivos únicos e não citam arquivos locais. Hooks
declaram `event`, `matcher` (opcional) e `run` (scripts da pasta, com `+x`).

## 2. Validar

```bash
uv run praxisforge library validate                         # tudo
uv run praxisforge library validate --type command          # um tipo
uv run praxisforge library validate --type skill minha-skill # um item
```

A saída tem uma linha `<tipo>/<nome>: <campo>: <motivo>` por problema, uma linha
`<tipo>/<nome>: reescrita pendente` por item marcado e o resumo `N ok, M com falha`. Entradas fora
dos seis tipos aparecem como `?/<caminho>: tipo desconhecido`. Exit code: `0` tudo válido, `1`
falha, `2` uso incorreto (nome sem `--type`, tipo desconhecido), `3` `library/` ausente.

## 3. Índice

```bash
uv run praxisforge library index
```

Regenera `library/INDEX.md` (não edite à mão). É determinístico: rodar duas vezes gera o mesmo
arquivo. Itens inválidos ficam de fora e são listados na saída.

## 4. Publicar num projeto

```bash
scripts/publish-library --type skill minha-skill --target ~/projetos/app
scripts/publish-library --all --target ~/projetos/app
scripts/publish-library --all --target ~/projetos/app --mode symlink
scripts/publish-library --all --target ~/projetos/app --prune
```

O atalho equivale a `uv run praxisforge library publish ...`. Publicáveis: skills, commands,
agents e rules, em `<projeto>/.claude/<tipo>s/`. Hooks e references **não** são publicados (as
references citadas vão dentro da skill). **Não existe publicação global**: `--target global` sai com
erro de uso. Para ligar um hook num projeto, copie o script para `.claude/hooks/` e registre-o no
`.claude/settings.json` do projeto, como descrito no próprio `HOOK.md`.

| Resultado | Quando |
|---|---|
| `publicada` | o destino não existia |
| `inalterada` | o conteúdo já é idêntico (nada é gravado) |
| `marcador atualizado` | publicação antiga (feature 008) com conteúdo igual; só o marcador é regravado |
| `atualizada` | versão nova, troca entre cópia e symlink, ou symlink antigo recriado |
| `recusada (...)` | item inválido, conteúdo mudou sem nova versão, ou item de terceiro no destino |

Com `--all`, a saída lista os itens **órfãos** (publicados por nós e que saíram do acervo); só são
removidos com `--prune`. Exit code: `0` ok, `1` alguma recusa, `2` uso incorreto, `3` falha de
gravação (o destino continua como estava).

Publicações antigas no escopo global (`~/.claude/skills/<nome>/.praxisforge-skill.json`) não são
mais tocadas pelo praxisforge; se existirem, remova-as à mão.
