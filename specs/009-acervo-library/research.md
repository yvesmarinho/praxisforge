<!-- Criado em: 25/09/2026 12:21 -->
<!-- Modificado em: 25/09/2026 12:27 -->

# Research: Acervo `library/` por tipo de recurso

Todas as incógnitas do Technical Context resolvidas abaixo. Evidência de formato: exemplos reais do
fork `agent-skills` (commit `d2c37ef`) e das skills já publicadas pela feature 008.

## R1. Formato de cada tipo no Claude Code

**Decision**: todos os tipos são Markdown com frontmatter YAML. Os metadados do praxisforge ficam
sempre sob a chave `metadata` (como já acontece nas skills), para não colidir com campos do Claude Code.

| Tipo | Layout no acervo | Campos do Claude Code | Obrigatórios no praxisforge |
|------|------------------|-----------------------|-----------------------------|
| skill | `library/skills/<nome>/SKILL.md` + apoio | `name`, `description` | `name`, `description`, `metadata.version` |
| command | `library/commands/<nome>.md` | `description` (+ `argument-hint`, `allowed-tools`, `model` opcionais) | `description`, `metadata.version`; `name` = nome do arquivo (não vai no frontmatter) |
| agent | `library/agents/<nome>.md` | `name`, `description` (+ `tools`, `model` opcionais) | `name`, `description`, `metadata.version` |
| rule | `library/rules/<nome>.md` | `description`, `paths` (lista de globs, opcional) | `description`, `metadata.version`; `name` = nome do arquivo |
| hook | `library/hooks/<nome>/HOOK.md` + scripts | — (hooks vivem no `settings.json`) | `name`, `description`, `event`, `run`, `metadata.version` |
| reference | `library/references/<nome>.md` | — (não é lido pelo Claude Code) | `name`, `description`, `metadata.version` |

**Rationale**: é o formato que o Claude Code já lê (exemplos em `.claude/commands/review.md`,
`agents/code-reviewer.md`, `.claude/rules/skills-contributing.md` do fork). O Claude Code ignora chaves
de frontmatter que não conhece. A 008 já publica skills com `metadata`, e elas carregam normalmente.

**Alternatives considered**: um arquivo `.praxisforge.yaml` separado ao lado de cada item foi
descartado porque duplica a fonte de verdade e some na publicação por cópia de arquivo único.

## R2. Hooks: o que o acervo guarda

**Decision**: pasta `library/hooks/<nome>/` com um `HOOK.md`. O frontmatter traz `event` (enum dos
eventos do Claude Code: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`,
`SessionStart`, `SessionEnd`, `Notification`, `PreCompact`), `matcher` (opcional) e `run` (lista de
arquivos da pasta que o hook executa). O corpo explica o que o hook faz e como ligá-lo à mão.

**Rationale**: atende o FR-005 (evento, finalidade, arquivos que existem) sem tocar em `settings.json`,
já que hooks não são publicáveis nesta feature (clarificação 1).

**Alternatives considered**: guardar um trecho `hooks.json` pronto (formato do plugin) foi descartado
por misturar configuração com a documentação; pode virar gerador na publicação futura.

## R3. References citadas por outros itens

**Decision**: um item cita references por slug em `metadata.references: [<nome>]`, e não por link
relativo. Link relativo que sai da pasta do item continua proibido. Nesta feature, **só skills** podem
citar references. Na publicação, as references citadas são copiadas para dentro da skill publicada
(`<skill>/references/<nome>.md`).

**Rationale**: skill é o único tipo publicável com pasta e arquivos de apoio. Commands, agents e rules
são arquivos únicos, e anexar arquivo a eles exigiria um diretório extra no projeto que o Claude Code
não lê. **Ajuste na spec**: o FR-021 passa a dizer "skill publicada".

**Alternatives considered**: publicar as references em `<projeto>/.claude/references/`. Descartado
porque o Claude Code não lê esse diretório e o item publicado ficaria dependendo de um caminho externo.

## R4. Marcador de publicação e compatibilidade (FR-017, FR-020)

**Decision**: um novo contrato `library-publication-v1.json` com `kind`, `name`, `version`,
`content_sha256` e `source` (`library/<kind>/<nome>`).
- **skill**: o marcador continua em `<skill>/.praxisforge-skill.json`.
- **command, agent e rule**: o marcador vira arquivo oculto irmão, `.<nome>.md.praxisforge.json`,
  no mesmo diretório do item publicado.
- **leitura**: marcadores `skill-publication-v1` (source `skills/<nome>`) continuam sendo
  reconhecidos como do praxisforge e são regravados no formato novo na próxima publicação.
- **symlink**: é reconhecido como nosso quando resolve para dentro de `library/`, ou para `skills/`
  no caso de links antigos.

**Migração do marcador (FR-017b)**: marcador antigo com conteúdo e versão iguais → só o marcador é
regravado ("marcador atualizado"), sem tocar no conteúdo e sem acionar a regra de versão. O hash usa
caminhos relativos à pasta do item (confirmado em `filesystem_skill_repository.py`), então o `git mv`
não muda o hash. Symlink antigo quebrado (alvo em `skills/`) é recriado para `library/`. A
`guarda-barra-qualidade` sobe para 1.0.1 porque ganha `rewrite_pending` (FR-025).

**Rationale**: mantém o modelo por item da 008 (sem read-modify-write de manifesto compartilhado). O
Claude Code só carrega `.md`, então o JSON oculto não interfere.

**Alternatives considered**: um manifesto único `<projeto>/.claude/.praxisforge-published.json`.
Descartado porque cria um ponto de corrupção compartilhado e diverge do modelo por item das skills.

## R5. Contratos (JSON Schema)

**Decision**: um schema por tipo, versionado pelo nome:
- `command-frontmatter-v1.json`, `agent-frontmatter-v1.json`, `rule-frontmatter-v1.json`,
  `hook-frontmatter-v1.json` e `reference-frontmatter-v1.json`;
- o `skill-frontmatter-v1.json` existente ganha `metadata.references` e `metadata.rewrite_pending`.
  A mudança é aditiva, então continua v1.

Os campos comuns de `metadata` (`version`, `sources`, `authored`, `rewrite_pending`, `references`)
são iguais em todos os schemas.

**Rationale**: o Princípio II manda versionar por arquivo. Cada formato do Claude Code evolui separado.

## R6. Fonte "só ideias" (FR-022, FR-023)

**Decision**: o `source-schema-v3.json` remove `extract_policy`, `extract_scope`, `notice_preserved` e
`modified`, e mantém `license` obrigatório como informação. `schema_version: "2"` é recusado com
mensagem de conversão ("remova extract_policy/extract_scope e troque schema_version para 3"). Os 2
registros são editados à mão (clarificação 4). A regra da 008 que exigia fonte `summary`/`verbatim`
passa a ser só "ao menos uma fonte válida".

**Rationale**: com D1 = só ideias, os níveis de extração perdem sentido. A tabela de
`domain/license_policy.py` deixa de ser usada na validação de fontes.

**Fora de escopo**: `folders show/list` exibem a "política máxima" da licença (feature 006). Esse
indicador fica como está nesta feature e vai para o TODO para ser revisto (remover ou mudar o rótulo).

## R7. CLI

**Decision**:
- `praxisforge library validate [--type T] [<nome>]`: sem argumentos valida tudo; `--type`
  restringe; `<nome>` exige `--type`.
- `praxisforge library index`: gera `library/INDEX.md`.
- `praxisforge library publish (--type T <nome> | --all) --target <pasta-de-projeto> [--mode copy|symlink] [--prune]`:
  `--target global` sai com erro de uso.
- `praxisforge skills ...`: erro de uso (código 2) indicando o comando `library` equivalente.

O `scripts/publish-skills` é renomeado para `scripts/publish-library`.

**Rationale**: mantém o vocabulário e os códigos de saída da 008 (0 ok, 1 validação, 2 uso,
3 ambiente).

## R8. Desempenho (SC-004)

**Decision**: um único passe de leitura por item, com o índice de fontes carregado uma vez por
execução. Um teste de escala com 200 itens mistos deve ficar abaixo de 5 s, no mesmo molde do teste
de 50 skills da 008.

## R9. Constituição

**Decision**: emenda **MAJOR, v4.0.0**:
- **Princípio VI** redefinido: acervo `library/` com seis tipos, publicação só em pastas de projeto
  e fim do alvo global;
- **Princípio V**: "só ideias" são extraídas; a licença é registro obrigatório, mas deixa de graduar
  a extração;
- **Princípio II**: o texto "registros versionados vivem em `src/data`" continua válido.

ADRs: `0011-acervo-library.md` (estrutura, tipos, publicação, marcador) e `0012-fontes-so-ideias.md`
(fim dos níveis de extração).
