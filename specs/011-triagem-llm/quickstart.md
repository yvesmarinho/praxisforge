<!-- Criado em: 28/09/2026 15:32 -->
<!-- Modificado em: 28/09/2026 15:40 -->

# Quickstart: validar a triagem com LLM

## Pré-requisitos

- Registro e convenções em `~/.config/praxisforge/` (features 007 e 010).
- `claude` instalado e autenticado (`claude /login`).
- Rodar na raiz do repositório (ou definir `PRAXISFORGE_ROOT`).

## 1. Gates automáticos (sem modelo real)

```bash
make lint && make test        # inclui o adapter testado com um `claude` falso
```

Esperado: testes de falha da 011 verdes, cobertura ≥ 90%. O teste de regressão de segurança
confere os flags `--tools ""`, `--strict-mcp-config`, `--setting-sources ""` e
`--disable-slash-commands`.

## 2. Prova de isolamento com o CLI real (manual, custo < US$ 0,01)

```bash
uv run pytest -m live tests/live/test_claude_cli_isolation.py
```

Esperado: o modelo declara só `StructuredOutput` como ferramenta, e o arquivo `PWNED` não é
criado no diretório temporário.

Obrigatório antes de ampliar a faixa de versões testadas do CLI no código (FR-037, SC-009).

## 3. Triagem pequena numa pasta real

```bash
uv run praxisforge curation inventory github_forks__andrej_karpathy_skills
uv run praxisforge curation triage github_forks__andrej_karpathy_skills --max-calls 10
uv run praxisforge curation status github_forks__andrej_karpathy_skills
```

Esperado:

- cada artefato elegível sai `triaged`, `drafted` ou `failed`;
- o artefato que originou `diretrizes-codificacao` é `covered`, citando `skill/diretrizes-codificacao`;
- os rascunhos ficam em `~/.config/praxisforge/curation/_drafts/`;
- nada muda no repositório (`git status` limpo) nem na pasta curada.

## 4. Teto e retomada

```bash
uv run praxisforge curation triage github_forks__agent_skills --max-calls 5; echo $?   # 4
uv run praxisforge curation triage github_forks__agent_skills --max-calls 5            # continua
```

Esperado: a primeira execução sai com 4 e mostra o comando de retomada; a segunda não reenvia
nenhum artefato já concluído.

## 5. Invalidação por prompt

Edite uma linha de `prompts/curation/criteria.md` (sem commitar) e rode a triagem da mesma pasta.
Os artefatos não revisados voltam a ser triados. Depois, desfaça a edição com
`git checkout prompts/curation/criteria.md`.
