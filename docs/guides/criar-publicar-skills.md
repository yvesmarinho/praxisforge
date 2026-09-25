<!-- Criado em: 24/09/2026 16:52 -->
<!-- Modificado em: 25/09/2026 09:58 -->

# Criar e publicar skills

Este guia cobre o fluxo completo da biblioteca de skills: criar a partir do template, validar,
gerar o catálogo e publicar. As decisões estão no
[ADR 0009](../decisions/0009-biblioteca-de-skills.md). Os comandos rodam de qualquer subpasta do
repositório: a CLI acha a raiz subindo até o `pyproject.toml` do praxisforge. Fora dele, defina
`PRAXISFORGE_ROOT` ([ADR 0010](../decisions/0010-raiz-do-projeto-por-marcador.md)).

## 1. Criar

```bash
cp -r skills/_template skills/minha-skill
```

Depois, edite `skills/minha-skill/SKILL.md`:

- `name: minha-skill`: igual ao nome da pasta, com minúsculas, dígitos e hífens (até 64
  caracteres);
- `description`: o que a skill faz e quando usá-la (até 1024 caracteres);
- `metadata.version`: versão em semver, que deve ser incrementada a cada mudança de conteúdo;
- `metadata.sources`: slugs dos registros em `src/data/sources/<categoria>/<slug>.md`. Pelo menos
  um deles precisa ter `extract_policy` `summary` ou `verbatim`;
- `metadata.authored: true`: use quando a skill não vem de nenhuma fonte.

Os arquivos de apoio ficam dentro da pasta da skill e são citados por link relativo, por exemplo
`[exemplo](exemplos/a.md)`.

## 2. Validar

```bash
uv run praxisforge skills validate minha-skill
uv run praxisforge skills validate --all
```

A saída tem uma linha `<skill>: <campo>: <motivo>` para cada problema e termina com o resumo
`N ok, M com falha`. O exit code é `0` quando tudo passa, `1` quando há falha e `2` quando falta
o nome e o `--all`, ou quando os dois são passados juntos.

## 3. Catálogo

```bash
uv run praxisforge skills catalog
```

O comando regenera `skills/README.md`. Não edite esse arquivo à mão. O resultado é determinístico:
rodar duas vezes gera o mesmo arquivo. Skills inválidas ficam de fora, aparecem listadas na saída e
fazem o comando sair com `1`.

## 4. Publicar

```bash
scripts/publish-skills minha-skill --target global            # ~/.claude/skills/minha-skill/
scripts/publish-skills --all --target ~/projetos/app          # ~/projetos/app/.claude/skills/
scripts/publish-skills --all --target global --mode symlink   # link para o repositório
scripts/publish-skills --all --target global --prune          # remove órfãs publicadas por nós
```

O atalho é equivalente a `uv run praxisforge skills publish ...`. A saída tem uma linha por skill:

| Resultado | Quando |
|---|---|
| `publicada` | o destino não existia |
| `inalterada` | o conteúdo já é idêntico (nada é gravado) |
| `atualizada` | a versão é nova, ou houve troca entre cópia e symlink |
| `recusada (...)` | a skill é inválida, o conteúdo mudou sem incrementar a versão, ou já existe no destino uma skill de terceiro com o mesmo nome |

Com `--all`, a saída lista também as skills **órfãs**: aquelas que o praxisforge publicou e que
não existem mais no repositório. Elas só são removidas com `--prune`. Uma pasta de projeto chamada
`global` precisa ser passada como `--target ./global`.

O exit code é `0` quando tudo dá certo, `1` quando alguma skill é recusada, `2` em caso de uso
incorreto (pasta de projeto inexistente ou `--prune` sem `--all`) e `3` em falha de gravação. Nesse
último caso o destino continua como estava.
