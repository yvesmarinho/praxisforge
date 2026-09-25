<!-- Criado em: 25/09/2026 12:21 -->
<!-- Modificado em: 25/09/2026 12:23 -->

# Quickstart: validação ponta a ponta da 009

Pré-requisitos: `make install-deps`; branch `009-acervo-library` implementada.
Contratos em [contracts/cli-library.md](contracts/cli-library.md); entidades em
[data-model.md](data-model.md).

## 1. Migração preservou o acervo (US2, SC-002)

```bash
test ! -d skills && ls library/skills        # diretrizes-codificacao, guarda-barra-qualidade
git log --follow --oneline library/skills/diretrizes-codificacao/SKILL.md | tail -1   # histórico da 008
grep -rn "skills/" src/ docs/guides/ scripts/ | grep -v "library/skills\|\.claude/skills"   # vazio
```

Esperado: as 2 skills presentes, histórico seguindo a renomeação, nenhuma referência ao local antigo.

## 2. Um item de cada tipo a partir do template (US1, SC-001)

Em uma cópia temporária do repositório:

```bash
for t in skills commands agents hooks rules references; do ls library/_templates/$t*; done
# copiar cada template para library/<tipo>/exemplo..., preencher os campos marcados
uv run praxisforge library validate          # "N ok, 0 com falha"
```

Quebrar um command (apagar `description`) → `command/exemplo: description obrigatória` e código 1,
com os demais ainda reportados como ok.

## 3. Índice determinístico (US3, SC-003)

```bash
uv run praxisforge library index && sha256sum library/INDEX.md
uv run praxisforge library index && sha256sum library/INDEX.md    # mesmo hash
grep "reescrita pendente" library/INDEX.md                         # guarda-barra-qualidade
```

## 4. Publicação só em projeto (US4)

```bash
P=$(mktemp -d)
uv run praxisforge library publish --all --target "$P"            # 0
ls "$P/.claude/skills" "$P/.claude/commands" "$P/.claude/agents" "$P/.claude/rules"
uv run praxisforge library publish --all --target "$P"            # 0, nada muda
uv run praxisforge library publish --all --target global; echo $? # 2
uv run praxisforge skills validate --all; echo $?                 # 2 + dica "library validate"
```

## 5. Fontes v3 (US5)

```bash
uv run praxisforge sources validate src/data/sources               # "2 ok"
# registro com schema_version "2" → falha com instrução de conversão
```

## 6. Gates

```bash
make lint && make test        # inclui teste de escala: 200 itens < 5 s (SC-004)
```
