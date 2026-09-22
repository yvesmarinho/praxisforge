<!-- Criado em: 22/09/2026 10:15 -->
<!-- Modificado em: 22/09/2026 10:12 -->

# ADR 0003: Verificação de regras de dependência entre camadas por AST

## Status

Aceito (22/09/2026)

## Contexto

A constituição (princípio I) exige regras de dependência entre camadas
verificáveis, não só documentadas. SC-006 exige 100% de detecção de violações.

## Decisão

`tests/architecture/layer_checker.py` percorre os módulos de `src/praxisforge/`
com `ast`, aplicando a matriz: `domain` → só stdlib e `praxisforge.domain` (sem
`logging`); `application` → domain + application; `infrastructure` → domain +
application + infrastructure; `presentation` → application + presentation.

**Exceção declarada**: `presentation/cli.py` (ponto de composição) pode
importar `praxisforge.infrastructure` — é o único lugar do sistema que instancia
os adapters concretos (Dependency Inversion). Nenhum outro módulo de
`presentation/` tem essa permissão.

`tests/architecture/test_layer_checker.py` valida o checker contra um pacote
sintético; `tests/architecture/test_layer_rules.py` aplica o checker ao código
real e exige zero violações.

## Achado real

O guarda pegou duas violações genuínas introduzidas durante a implementação
(Application → Infrastructure via `logging_setup`; `cli.py` → Domain
diretamente), corrigidas sem afrouxar a matriz (ver `docs/architecture/overview.md`).

## Alternativas descartadas

- `import-linter`: ferramenta madura, mas é uma dependência nova fora do
  conjunto-chave da constituição para um projeto com só quatro camadas e uma
  exceção. Reavaliar se as regras crescerem em complexidade.

## Consequências

- Zero dependência nova.
- O teste roda no gate normal (`make test`), sem etapa extra de CI.
- Precisa ser atualizado manualmente se a matriz de camadas mudar (ex.: nova
  exceção de composição).
