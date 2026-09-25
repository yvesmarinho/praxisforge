<!-- Criado em: 25/09/2026 12:40 -->
<!-- Modificado em: 25/09/2026 12:40 -->

# ADR 0012: Das fontes só se extraem ideias

## Status

Aceito (25/09/2026). Substitui a graduação por licença do [ADR 0007](0007-politica-de-extracao-por-licenca.md).
Origem: debate `docs/debates/curadoria-automatizada.md` (D1); constituição v4.0.0 (Princípio V).

## Contexto

A feature 006 graduava a extração pela licença (`link` < `summary` < `verbatim`). A primeira
curadoria automatizável mostrou dois problemas: um LLM tende a produzir paráfrase próxima (obra
derivada) mesmo quando pedido para sintetizar, e tradução é obra derivada. A `guarda-barra-qualidade`
é um caso real: tradução adaptada de uma skill MIT.

## Decisão

- O acervo contém só **síntese autoral de ideias**: nenhum trecho literal, tradução ou paráfrase
  próxima, qualquer que seja a licença.
- A licença continua **obrigatória** no registro de fonte, como informação e rastreabilidade.
- `source-schema-v3.json` remove `extract_policy`, `extract_scope`, `notice_preserved` e `modified`.
  Registros v1/v2 são recusados com instrução de conversão; os 2 registros existentes são convertidos
  à mão (sem comando permanente).
- Itens anteriores à regra que sejam derivados recebem `metadata.rewrite_pending: true`
  (informativo, não bloqueia publicação) e são reescritos na refação das curadorias (feature 012).

## Alternativas descartadas

- Manter os três níveis (ideias, derivada, literal): exige avaliar licença por item e aviso por
  derivada; o curador escolheu a regra mais simples e segura.

## Consequências

- A tabela `domain/license_policy.py` deixa de governar fontes; a "política máxima" exibida em
  `folders show/list` fica para revisão (TODO).
- A detecção de similaridade (feature 011) passa a ser a salvaguarda contra derivada acidental.
