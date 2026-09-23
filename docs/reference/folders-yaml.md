<!-- Criado em: 22/09/2026 16:40 -->
<!-- Modificado em: 23/09/2026 12:17 -->

# Referência — `src/data/folders.yaml`

Registro versionado das pastas externas a curar. É o único artefato de dados da feature 001
(`001-registro-pastas-curadoria`), lido/escrito exclusivamente através da CLI `praxisforge folders
*` — nunca editado à mão em uso normal (edição manual é possível, mas cada mudança deve continuar
passando por `folders validate` antes de commitar).

## Onde vive e o que ele é

- **Caminho padrão**: `src/data/folders.yaml` (configurável via `--registry <caminho>` em
  qualquer subcomando da CLI).
- **Contrato**: `schemas/folders-schema-v1.json` (JSON Schema Draft 2020-12), validado com
  `jsonschema[format]` — dois pontos de validação: ao carregar (`folders show`/`list`/`scan`/
  `resolve`/`update`/`bootstrap`) e via `folders validate` (varre o arquivo inteiro item a item).
- **O que ele NÃO contém**: nenhum caminho absoluto do sistema de arquivos. O caminho real de cada
  pasta vem de uma variável de ambiente (`PRAXISFORGE_FOLDER_<ALIAS>`), nunca do YAML — é assim
  que o arquivo pode ser versionado no git sem vazar detalhes da máquina de quem o edita.

## Estrutura do arquivo

```yaml
folders:
  <alias>:
    description: <string, 1-500 caracteres>
    content_type: <slug>
    license: <string>
    last_scanned: <data ISO 8601 com timezone, ou null>
    status: <not_scanned | scanned | in_curation | curated | pending | ignore>
    last_curated_commit: <hash SHA-1/SHA-256, opcional — feature 004>
schema_version: "1"
```

### Campo raiz `schema_version`

- **Tipo**: string, valor fixo `"1"` (única versão suportada hoje).
- Mudança breaking no formato exige um novo schema com major incrementado
  (`schemas/folders-schema-v2.json`) — nunca alterar o significado de um campo existente dentro
  da v1 (constituição II).

### Campo raiz `folders`

- **Tipo**: objeto — cada chave é um **alias**, cada valor é uma pasta registrada.
- Nome da chave (alias) validado pelo padrão `^[a-z][a-z0-9_]{1,62}$`: minúsculas, começa com
  letra, só letras/dígitos/`_`, 2 a 63 caracteres.
- O alias é o único vínculo entre este arquivo e o caminho real: a variável de ambiente
  correspondente é sempre `PRAXISFORGE_FOLDER_<ALIAS_EM_MAIÚSCULO>`.

### Campos de cada pasta (objeto `folder`)

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `description` | string (1-500 caracteres) | sim | Texto livre descrevendo o conteúdo da pasta. |
| `content_type` | string, padrão `^[a-z][a-z0-9_-]{1,62}$` | sim | Slug do tipo de conteúdo (ex.: `repository_forks`, `documents`). Livre, sem lista fechada de valores no schema atual. |
| `license` | string, mínimo 1 caractere | sim | Identificador de licença (ex.: `MIT`, `Apache-2.0`) ou o valor especial `unknown` quando ainda não determinada. |
| `last_scanned` | string ISO 8601 *com* timezone, ou `null` | sim (pode ser `null`) | Data/hora da última varredura bem-sucedida (`folders scan`). `null` até a primeira varredura. |
| `status` | enum: `not_scanned`, `scanned`, `in_curation`, `curated`, `pending`, `ignore` | sim | Estado de curadoria — ver seção "Status" abaixo. |
| `last_curated_commit` | string, 40 ou 64 hex minúsculos (`^[0-9a-f]{40}([0-9a-f]{24})?$`) | não | Hash do commit revisado na última curadoria (feature 004). Gravado ao marcar `curated`; mantido como histórico nos demais status; chave omitida quando ausente. |

`additionalProperties: false` em ambos os níveis (raiz e por pasta) — nenhum campo fora dessa
lista é aceito; o schema rejeita tanto campos desconhecidos quanto campos faltando.

## Status (`status`)

| Valor | Rótulo pt-BR | Significado |
|---|---|---|
| `not_scanned` | não varrida | Registrada, nunca confirmada por `folders scan`. `last_scanned` obrigatoriamente `null` nesse status. |
| `scanned` | varrida | Caminho confirmado acessível ao menos uma vez. |
| `in_curation` | em curadoria | Alguém está ativamente avaliando o conteúdo (transição manual, via `folders update --status in_curation`). |
| `curated` | curada | Conteúdo já avaliado e processado. |
| `pending` | pendente | Aguardando decisão — hoje, sempre porque `license` é `unknown` (ver invariante abaixo). |
| `ignore` | ignorada | Curador decidiu excluir permanentemente esta pasta de bootstrap/varredura futuros. Só aplicado manualmente via `folders update --status ignore` (feature 003) — nunca atribuído automaticamente. |

## Invariantes validadas pelo contrato

O schema aplica duas regras condicionais (`allOf`/`if`/`then`) além dos tipos de campo:

1. **Licença desconhecida trava o status**: se `license == "unknown"`, então `status` **deve** ser
   `pending` **ou** `ignore` (feature 003 — relaxamento aditivo da invariante original, que só
   admitia `pending`). Não é possível, por exemplo, ter `license: unknown` com `status: scanned`
   — o sistema recusa (`UnknownLicenseRequiresPendingError` na camada de aplicação, antes mesmo de
   chegar à validação de schema).
2. **Pasta nunca varrida não tem data**: se `status == "not_scanned"`, então `last_scanned` deve
   ser `null`. Uma pasta só ganha uma data real depois de passar por `folders scan` pelo menos
   uma vez (o que, nesse momento, já avança automaticamente o status para `scanned` se ele ainda
   era `not_scanned` — ver `docs/guides/operar-cli-praxisforge.md`).

## Exemplo real (estado atual do projeto)

```yaml
folders:
  github_forks:
    content_type: repository_forks
    description: Forks de repositórios de referência sobre engenharia de agentes
    last_scanned: '2026-09-22T15:46:38.646069+00:00'
    license: unknown
    status: pending
schema_version: '1'
```

Leitura desse exemplo: existe 1 pasta registrada (`github_forks`), já foi varrida (tem
`last_scanned`), mas continua `pending` porque a licença ainda não foi determinada — resolver isso
exige `folders update github_forks --license <licença real>` manualmente.

## Como o arquivo é lido e escrito

- **Leitura**: `infrastructure/yaml_folder_registry.py` usa um `yaml.SafeLoader` customizado
  (`NoTimestampSafeLoader`) que **não** converte `last_scanned` automaticamente em `datetime` —
  o valor fica como string ISO 8601 até ser explicitamente convertido pela camada de aplicação.
  Isso evita ambiguidade de fuso horário na desserialização.
- **Escrita**: sempre atômica — grava em arquivo temporário (`tempfile.mkstemp`) e substitui via
  `os.replace`, nunca escreve parcialmente por cima do arquivo original. Serializado com
  `yaml.safe_dump(sort_keys=True, allow_unicode=True)` — por isso as chaves de cada pasta sempre
  aparecem em ordem alfabética, independente da ordem em que os campos foram informados na CLI.
- **Validação em duas etapas**: ao carregar, o documento bruto é validado contra o JSON Schema
  (`schema_version` primeiro, depois cada pasta) antes de ser reconstruído como entidades de
  domínio (`Folder`/`FolderRegistry`), que reforçam as mesmas invariantes de novo no
  `__post_init__` — nenhum dado inválido sobrevive às duas camadas.

## Detecção de mudança de conteúdo (feature 004)

Desde a feature `004-deteccao-mudanca-conteudo`, a limitação descrita abaixo foi resolvida:

- `folders update <alias> --status curated` grava o HEAD da pasta git em `last_curated_commit`.
- `folders scan` compara, para cada pasta `curated` com hash, o conteúdo **da própria pasta** entre
  o hash gravado e o HEAD atual; se mudou, o status volta para `in_curation` (hash mantido).
- Pasta `curated` sem hash (legado) recebe o HEAD atual como referência na primeira varredura.
- Pastas fora de repositório git continuam fora do mecanismo. Ver
  [ADR 0005](../decisions/0005-deteccao-mudanca-por-git-cli.md).

## Limitação conhecida (histórico, resolvida na feature 004): mudança de conteúdo não era detectada

Hoje **nenhum campo deste arquivo reflete se o conteúdo da pasta mudou desde a última
curadoria**. `last_scanned` só confirma que o caminho continua acessível (`folders scan`) — não
compara conteúdo, não calcula hash, não olha commits. Uma pasta `curated` (curada) pode ganhar
novos commits/arquivos e o `status` permanece `curated` indefinidamente, como se nada tivesse
mudado.

**Comportamento planejado** (feature futura, ainda sem número/spec formal): quando o conteúdo de
uma pasta git mudar em relação ao commit HEAD registrado na última curadoria, o sistema deve
reverter automaticamente o `status` de `curated` para `in_curation`, forçando nova revisão antes
de voltar a ser considerada curada. A detecção é por hash do commit HEAD (só funciona para pastas
que são repositórios git — outras pastas ficam fora desse mecanismo até uma decisão futura). Isso
exigirá um campo novo na entidade (ex.: `last_curated_commit_hash`) e portanto uma nova versão do
schema (`schemas/folders-schema-v2.json` ou aditiva, a depender da decisão de `/speckit-plan`
quando essa feature for especificada).

## Referências

- Schema: [`schemas/folders-schema-v1.json`](../../schemas/folders-schema-v1.json)
- Entidades de domínio: `src/praxisforge/domain/folder.py`, `folder_registry.py`,
  `curation_status.py`
- Como operar via CLI: [`docs/guides/operar-cli-praxisforge.md`](../guides/operar-cli-praxisforge.md)
- Decisões de arquitetura: [`docs/architecture/overview.md`](../architecture/overview.md)
