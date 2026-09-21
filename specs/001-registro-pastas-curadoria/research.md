<!-- Criado em: 21/09/2026 15:59 -->
<!-- Modificado em: 21/09/2026 16:00 -->

# Research — 001-registro-pastas-curadoria

Nenhum `NEEDS CLARIFICATION` restou na spec ou no Technical Context. Esta pesquisa registra as
decisões técnicas e as premissas da spec que este plano fixa.

## D1. Domain sem pydantic; pydantic só na fronteira

- **Decisão**: entidades e value objects do Domain são `dataclass(frozen=True)` + `enum` da
  stdlib, com invariantes em `__post_init__` levantando exceções semânticas. Pydantic fica na
  Application (`dto.py`) para validar a entrada dos casos de uso e a CLI.
- **Racional**: a constituição (I) proíbe libs externas no Domain; a regra global também. A
  validação estrita da entrada continua obrigatória (II) — ocorre antes de chegar ao Domain.
- **Alternativas**: pydantic no Domain (viola I); validação manual espalhada (viola II).

## D2. Validação em duas etapas

- **Decisão**: (1) JSON Schema valida o documento YAML/frontmatter e devolve **todas** as
  violações (`iter_errors`, FR-009); (2) a construção das entidades garante invariantes que o
  schema não expressa (alias único, licença desconhecida ⇒ `pending`).
- **Racional**: o schema é o contrato versionado publicado; o Domain protege regras de negócio.
- **Alternativas**: só pydantic (não gera contrato versionado reutilizável por
  `check-jsonschema`); só JSON Schema (não cobre unicidade nem regras entre campos).

## D3. Modelo do alias e variável de ambiente

- **Decisão**: alias `^[a-z][a-z0-9_]{1,62}$` (minúsculas). Variável de ambiente
  `PRAXISFORGE_FOLDER_<ALIAS EM MAIÚSCULAS>` (ex.: `PRAXISFORGE_FOLDER_GITHUB_FORKS`).
- **Racional**: só minúsculas elimina a colisão por caixa (FR-003); o formato mapeia 1:1 para
  nome de variável de ambiente válido; segue o exemplo do objetivo-init.
- **Alternativas**: aceitar hífen/maiúsculas (exige normalização e gera colisões).

## D4. Segurança do caminho resolvido

- **Decisão**: o valor da variável deve ser absoluto, sem segmento `..`; após `Path.resolve()`
  deve existir, ser diretório e legível. Link simbólico é seguido e o **caminho real** é
  validado. Caminho relativo, com `..`, inexistente ou ilegível ⇒ `FolderPathInvalidError`.
- **Racional**: a spec (edge case) pede recusa de relativo e `..`; "link simbólico para fora da
  área esperada" não define "área esperada" — como o material bruto fica por definição fora do
  repo (V), não há raiz permitida a impor. Fica registrado como **premissa desta fase**; se for
  necessária uma raiz permitida, vira feature futura.
- **Alternativas**: restringir a uma raiz configurada (over-engineering para único curador).

## D5. Escrita do registro: atômica, determinística, sem preservar comentários

- **Decisão**: `PyYAML` (`safe_load`/`safe_dump`, `sort_keys` por alias, `allow_unicode`);
  escrita em arquivo temporário no mesmo diretório + `os.replace`. Comentários no YAML **não**
  são preservados (arquivo gerenciado pela ferramenta; cabeçalho `_meta`/aviso gerado).
- **Racional**: idempotência e diffs estáveis no git (FR-015); evita corrupção em falha no meio
  da escrita (FR-017).
- **Alternativas**: `ruamel.yaml` (preserva comentários, mas é dependência nova fora do
  conjunto-chave da constituição); reescrita direta (não atômica).

## D6. Idempotência do "registrar"

- **Decisão**: registrar alias já existente com **dados idênticos** ⇒ no-op reportado como
  "inalterado"; com dados **diferentes** ⇒ `AliasAlreadyRegisteredError` sem alterar nada.
- **Racional**: reconcilia US1-cenário 3 (recusar alias duplicado) com FR-015 (repetir o mesmo
  registro não altera o resultado).

## D7. Status de curadoria e tipo de conteúdo

- **Decisão**: `CurationStatus` = `not_scanned`, `scanned`, `in_curation`, `curated`, `pending`
  (valores de máquina em inglês, rótulos em pt-BR na CLI). `content_type`: string não vazia
  (slug `^[a-z][a-z0-9_-]{1,62}$`), conjunto aberto por ora.
- **Racional**: cumpre a premissa da spec (status definido no plano); tipo de conteúdo ainda não
  tem taxonomia — fechar cedo geraria migração de contrato.
- **Alternativas**: enum fechado de tipos (prematuro).

## D8. Licença

- **Decisão**: `license` = identificador SPDX ou o literal `unknown`. `unknown` ⇒ status
  obrigatoriamente `pending` (folders) e `extract_allowed=false` (sources).
- **Racional**: FR-010 e edge case "licença desconhecida".

## D9. Fontes (source-schema-v1)

- **Decisão**: frontmatter obrigatório: `schema_version`, `origin`, `date`, `license`,
  `relevance`, `status` (`active`|`pending`), `extract_allowed`. Esta feature entrega o
  **contrato e a validação** (`praxisforge sources validate`); a criação/curadoria das fontes
  é de feature posterior.
- **Racional**: FR-007/FR-010 exigem o contrato de fonte já nesta fase (objetivo-init, item de
  Fase 2).

## D10. Verificação de regras de dependência entre camadas

- **Decisão**: teste `pytest` em `tests/architecture/` que percorre os módulos com `ast` e
  aplica a matriz: `domain` → só stdlib e `praxisforge.domain`; `application` → domain;
  `infrastructure` → domain + application; `presentation` → application (+ infra apenas no
  ponto de composição `cli.py`); `domain` sem `logging`. Violação ⇒ falha citando módulo,
  import e regra (US4).
- **Racional**: sem dependência nova; atende SC-006 e roda no gate normal.
- **Alternativas**: `import-linter` (boa ferramenta, mas dependência extra fora da constituição;
  reavaliar se as regras crescerem).

## D11. CLI

- **Decisão**: `argparse` com subcomandos `folders add|list|show|update|validate|resolve` e
  `sources validate`; entrypoint `praxisforge` em `[project.scripts]`. Códigos de saída: 0 ok,
  1 falha de validação/negócio, 2 uso incorreto, 3 falha de ambiente. Saída para usuário em
  stdout; erros em stderr; logs estruturados via `logging` (não `print` fora da CLI).
- **Racional**: zero dependência nova; presentation fina, sem regra de negócio.
- **Alternativas**: `click`/`typer` (dependência nova sem necessidade real).

## D12. Logs estruturados

- **Decisão**: `logging` com formatter JSON em `infrastructure/logging_setup.py`; campos
  `event`, `alias`, `outcome`, `error_type`; **nunca** caminho absoluto, segredo ou conteúdo.
  Domain não faz log; Application/Infrastructure logam nas fronteiras.
- **Racional**: FR-016, constituição I e IV.

## D13. Lote com falha por item

- **Decisão**: `validate_registry` devolve `BatchReport` (itens ok + lista de `ItemFailure`
  com alias, tipo do erro e mensagem); nunca levanta por falha de item, só por falha do
  registro inteiro (arquivo ausente/corrompido/versão não suportada).
- **Racional**: FR-006, SC-004 e constituição IV.

## D14. Datas e localização

- **Decisão**: `last_scanned` em ISO 8601 com offset (`2026-09-21T15:55:00-03:00`), timezone
  `America/Sao_Paulo` ao gerar; validado como não futuro; exibição na CLI em `DD/MM/AAAA HH:MM`.
- **Racional**: regra global de localização; FR-011.

## D15. Documentação exigida

- **Decisão**: criar `docs/architecture/overview.md` e ADRs em `docs/decisions/` (mínimo:
  domínio sem pydantic; registro YAML sem preservação de comentários; verificação de camadas por
  AST) como parte das tasks.
- **Racional**: constituição (Restrições Adicionais).
