<!-- Criado em: 28/09/2026 16:31 -->
<!-- Modificado em: 28/09/2026 16:38 -->

# ADR 0014: Triagem de curadoria com LLM sem ferramentas, com staging fora do repositório

## Status

Aceito (28/09/2026). Feature 011-triagem-llm, segunda etapa da curadoria automatizada (debate
`docs/debates/curadoria-automatizada.md`). Depende da 010 (inventário); a revisão e a promoção
ficam para a 012.

## Contexto

O inventário da 010 deixa 5.658 artefatos pendentes nas 18 pastas reais. Ler tudo à mão não é
viável, e o conteúdo vem de repositórios de terceiros, que podem trazer instruções escritas para
manipular um agente (*prompt injection*). O acervo é público e só pode receber **ideias**, nunca
texto literal, tradução ou paráfrase próxima (Princípio V).

## Decisão

- **Modelo sem ferramentas (K4)**: `claude -p` com `--tools ""`, `--strict-mcp-config` e MCP
  vazio, `--setting-sources ""` (sem hooks nem permissões do usuário),
  `--disable-slash-commands`, `--no-session-persistence`, `--system-prompt` próprio e
  `--output-format json` + `--json-schema`. O prompt vai pelo stdin. O processo roda num
  diretório temporário vazio, removido ao fim, e o ambiente passa por uma lista de permissão.
  Provas com o CLI real (28/09/2026): a única ferramenta disponível é `StructuredOutput`, e a
  tentativa de `touch PWNED` não tem efeito. `--bare` foi rejeitado porque desliga o login da
  assinatura.
- **Falha fechada**: versão do CLI fora da faixa testada (`>=2.1.283,<2.2`) ou flag de isolamento
  recusado → nenhuma chamada, exit 3. Ampliar a faixa exige o teste `live` de isolamento.
- **Validação dupla, só a local vale**: o schema vai para o CLI sem `$schema`/`$id` (o validador
  do CLI recusa o metaschema draft 2020-12) e sem `allOf`/`anyOf`/`oneOf` na raiz (a API não
  aceita), com tipos explícitos em todo nó (modo estrito do CLI). A resposta é validada de novo no
  código com o schema completo, antes de virar domínio. As três restrições foram achadas nas
  primeiras chamadas reais (`docs/bugs/2026-09-28-cli-recusa-metaschema-2020-12.md`).
- **Veredito em campo próprio** no `state.json` **v2** (`triage`), lido também em v1. O
  `verdict` da 010 continua sendo o veredito da revisão (012).
- **Rascunhos em área global** `curation/_drafts/<id>.json`, com lock próprio: uma fusão pode
  atingir o rascunho de outra pasta. O `draft_id` é o SHA-256 (16 hex) de `alias\0caminho` da 1ª
  origem; nenhum campo da resposta do modelo entra em nome de arquivo. Diretórios `0700`,
  arquivos `0600`, link simbólico recusado.
- **Contexto só do repositório**: `library/INDEX.md`, até 3 itens do mesmo tipo escolhidos por
  Jaccard (sem modelo), o índice dos rascunhos pendentes (só id, tipo, nome e descrição,
  delimitado como não confiável) e `prompts/curation/criteria.md`. Limites fixos (índices 64 KiB,
  itens 96 KiB, artefato 256 KiB), sem truncar o artefato.
- **Prompts versionados** em `prompts/curation/`; a impressão digital do conjunto vai em cada
  veredito e rascunho, e mudá-la reabre o que ainda não foi revisado.
- **Similaridade em duas camadas**: esqueleto estrutural (títulos, listas, tabelas, código,
  passos, em faixas; independente de idioma) com limiar 0,7, e um juiz (modelo barato, sem
  ferramentas). Rascunho sinalizado é regenerado uma vez; se continuar sinalizado, é gravado com
  alerta.
- **Teto por execução**: 1 chamada reservada para a triagem e 4 para o rascunho (rascunho, juiz e
  uma regeneração com novo juiz). Sem orçamento para o rascunho, a lacuna fica `triaged` e a
  próxima execução só rascunha. A retomada é rodar o mesmo comando (exit 4 no teto).

## Consequências

- Nenhum arquivo é escrito fora de `curation/`, qualquer que seja o conteúdo ou a resposta (teste
  de injeção com snapshot do diretório).
- **Limitações medidas**:
  - A camada estrutural pega cópia e tradução direta, mas não a adaptação: a
    `guarda-barra-qualidade` pontua 0,28, contra até 0,77 de uma síntese autoral. Ela virou caso
    de calibração do juiz, que a sinalizou em 5 de 6 execuções com o Haiku. O juiz não é
    determinístico; a rede de segurança é a regeneração mais a revisão humana na 012.
  - Uma injeção pode distorcer um veredito `covered`/`out_of_scope` sem executar nada. Mitigação:
    item citado conferido no catálogo real e justificativa auditável.
- Custo medido: cerca de US$ 0,005 por chamada ao Haiku com system prompt próprio (cerca de 5
  vezes menos que com o padrão do Claude Code).

## Alternativas rejeitadas

- API da Anthropic direta (rejeitada no C1 do debate: o CLI usa a assinatura).
- Staging dentro do repositório (`curation/<alias>/`, E1): o repositório é público.
- Rascunho sempre sob demanda: o curador escolheu rascunho automático na clarificação.
- Embeddings para similaridade: dependência nova e resultado não determinístico.
