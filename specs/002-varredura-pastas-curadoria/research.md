<!-- Criado em: 22/09/2026 11:56 -->
<!-- Modificado em: 22/09/2026 11:49 -->

# Research: Varredura das Pastas Registradas

Nenhum `NEEDS CLARIFICATION` restou no Technical Context — a feature reaproveita integralmente a
stack, os contratos e as portas da feature 001. As decisões abaixo documentam escolhas de design
feitas ao mapear os requisitos para o código existente.

## Decisão 1 — Onde vive a lógica de varredura

- **Decision**: novo módulo `application/scan_folders.py` com duas funções,
  `scan_folder(repository, resolver, alias)` e `scan_all_folders(repository, resolver)`, no
  mesmo padrão dos casos de uso já existentes (`update_folder.py`, `resolve_folder_path.py`).
- **Rationale**: varrer é uma orquestração — resolver o caminho (porta `PathResolver`) e depois
  persistir a mudança de estado (`FolderRegistry.update()` + `FolderRegistryRepository.save()`) —
  sem nenhuma regra nova de Domain; a Application é a camada correta por definição (constituição
  I). Reaproveitar as portas existentes evita qualquer novo adapter de Infrastructure.
- **Alternatives considered**: colocar a lógica dentro de `resolve_folder_path.py` (rejeitado —
  responsabilidades diferentes: resolver caminho é read-only, varrer persiste estado; misturar
  quebraria a coesão do módulo existente e obrigaria os testes de resolução a mockar persistência
  sem necessidade).

## Decisão 2 — Como decidir se o status avança

- **Decision**: `scan_folder` chama `FolderRegistry.update(alias, last_scanned=agora)` sempre;
  quando o status atual é `CurationStatus.NOT_SCANNED`, passa também `status=CurationStatus.SCANNED`.
  Para qualquer outro status (`SCANNED`, `IN_CURATION`, `CURATED`, `PENDING`), `status` não é
  passado — `FolderRegistry.update()` já preserva o valor atual quando o parâmetro é `None`.
- **Rationale**: reaproveita 100% da lógica atômica e das invariantes já testadas em
  `folder_registry.py` (ex.: licença `unknown` ⇒ status `PENDING` continua garantido pelo
  `Folder.__post_init__`, mesmo durante uma varredura — FR-002/edge case "pasta pendente").
- **Alternatives considered**: criar um novo método `FolderRegistry.mark_scanned()` dedicado
  (rejeitado — duplicaria a lógica atômica de `update()` sem ganho real; `update()` já é genérico
  o bastante).

## Decisão 3 — Isolamento de falha no lote

- **Decision**: `scan_all_folders` segue exatamente o padrão de `resolve_all_folder_paths` —
  itera `registry.list()`, tenta `scan_folder` por alias dentro de um `try/except Exception`
  (comentado `# noqa: BLE001`, mesma justificativa: agregação de falha por item, não interrupção
  do lote), e devolve um relatório dataclass com `ok` (lista de resultados) e `failures` (lista de
  `ItemFailure`, reaproveitando a dataclass já existente em `resolve_folder_path.py`).
- **Rationale**: constituição IV exige exatamente esse padrão (lote não derruba por item); a
  dataclass `ItemFailure` já existe e tem o formato certo (alias, error_type, message) —
  reaproveitá-la evita duplicação.
- **Alternatives considered**: levantar um `ExceptionGroup` (rejeitado — não é o padrão já
  estabelecido no código, quebraria a consistência com `resolve_folder_path.py` e
  `validate_registry.py`).

## Decisão 4 — Detecção de aliases duplicados

- **Decision**: dentro de `scan_all_folders`, depois de resolver o caminho real de cada alias que
  teve sucesso (`Path` já normalizado por `EnvPathResolver.resolve()`, que usa `Path.resolve(strict=True)`
  e portanto já segue links simbólicos), agrupar os aliases por caminho real
  (`dict[Path, list[str]]`) e reportar como grupo duplicado qualquer entrada com mais de um alias.
  O resultado é uma lista de `DuplicateAliasGroup(real_path_hash, aliases)` — **sem** expor o
  caminho absoluto em texto plano no relatório (FR-010/SC-004): o agrupamento usa o `Path` só
  internamente para comparar igualdade; a saída pública carrega apenas os aliases agrupados.
- **Rationale**: a resolução de caminho já é feita para atualizar `last_scanned` de cada pasta —
  reaproveitar esse mesmo resultado (em vez de resolver de novo) evita uma segunda leitura de
  filesystem por pasta e mantém a varredura determinística em uma única passada.
- **Alternatives considered**: comparar os valores brutos das variáveis de ambiente
  (`PRAXISFORGE_FOLDER_<ALIAS>`) em vez do caminho resolvido (rejeitado — não cobre o caso mais
  comum do edge case da spec, dois caminhos textualmente diferentes que resolvem para o mesmo
  diretório real via link simbólico).

## Decisão 5 — Novo subcomando CLI

- **Decision**: adicionar `folders scan <alias>` (varredura individual, posicional opcional) e
  `folders scan --all` (varredura em lote), como grupo mutuamente exclusivo obrigatório
  (`add_mutually_exclusive_group(required=True)`) — exatamente o mesmo padrão já usado por
  `folders resolve` em `cli.py:96-99` (`resolve_group.add_argument("alias", nargs="?", ...)` +
  `--all`).
- **Rationale**: mantém a superfície de CLI 100% consistente com `folders resolve` já existente;
  a Presentation continua sem regra de negócio, só converte argv → chamada do caso de uso →
  mensagem amigável (mesmo padrão de exit codes 0/1/2/3 já estabelecido).
- **Alternatives considered**: dois subcomandos separados (`folders scan` e `folders scan-all`)
  (rejeitado — introduziria uma convenção divergente da já estabelecida por `folders resolve`
  para o mesmo tipo de operação individual-vs-lote).

**Output**: todas as decisões técnicas resolvidas; nenhum `NEEDS CLARIFICATION` restante.
