<!-- Criado em: 22/09/2026 11:32 -->
<!-- Modificado em: 22/09/2026 11:32 -->

# CI: Dependency Review bloqueado por vulnerabilidade transitiva do `nltk`

## Contexto

PR #11 (`001-registro-pastas-curadoria` → `main`). Job `Review Dependencies`
(`.github/workflows/dependency-review.yml`, `actions/dependency-review-action@v5`,
`fail-on-severity: moderate`) falhou.

## Erro

```
uv.lock » nltk@3.10.3 – NLTK: Model-artifact APIs bypass pathsec and touch
files outside allowed roots (high severity)
↪ https://github.com/advisories/GHSA-8mgp-746c-j5xp
##[error]Dependency review detected vulnerable packages.
```

## Causa raiz

`nltk` não é dependência direta do projeto — é transitiva de `safety`
(adicionado às dev deps em T003/T069 para `make security`, exigido pela
constituição):

```
nltk v3.10.3
└── safety v3.8.1
    └── praxisforge v0.1.0 (group: dev)
```

A advisory (CVE-2026-81726, CVSS 7.0) afeta `TransitionParser.train/parse`,
`AveragedPerceptron.save/load` e `save_maxent_params` do NLTK — APIs de
treino/persistência de modelo que usam `open()` bruto em vez de helpers
`pathsec`-aware, permitindo leitura/escrita fora da raiz permitida quando o
caminho do modelo é controlado por um chamador não confiável.

`first_patched_version` da advisory é `null` (22/09/2026) — nenhuma versão
corrigida do `nltk` existe ainda.

## Análise de risco

O praxisforge nunca importa `nltk` nem chama qualquer API de modelo dele; é
uma dependência transitiva de uma ferramenta de dev (`safety`) que não expõe
essas APIs ao nosso código em runtime ou testes. A superfície de ataque
descrita na advisory (chamador controla o caminho do modelo sob enforcement
de `pathsec`) não existe neste projeto.

## Correção

`allow-ghsas: GHSA-8mgp-746c-j5xp` adicionado ao step `Dependency Review` em
`.github/workflows/dependency-review.yml`, com comentário explicando o
racional (dependência transitiva inatingível, sem patch disponível). O gate
continua bloqueante (`fail-on-severity: moderate`) para qualquer outra
vulnerabilidade — só esta GHSA específica é permitida.

## Acompanhamento

- Revisar este allowlist quando uma versão corrigida do `nltk` ou do `safety`
  (removendo a dependência de `nltk`) estiver disponível — remover a entrada
  de `allow-ghsas` nesse momento.
- `make security` local roda `safety check` (comando deprecado, mas ainda
  funcional); sem impacto desta correção, que é só do gate de CI do PR.
