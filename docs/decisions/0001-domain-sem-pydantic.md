<!-- Criado em: 22/09/2026 10:15 -->
<!-- Modificado em: 22/09/2026 10:12 -->

# ADR 0001: Domain sem pydantic; pydantic só na fronteira

## Status

Aceito (22/09/2026)

## Contexto

A constituição do projeto (princípio I — Arquitetura em Camadas) proíbe libs
externas no Domain. A entrada, porém, precisa de validação estrita (princípio II).

## Decisão

Entidades e value objects do Domain (`Alias`, `Folder`, `FolderRegistry`,
`SourceRecord`, `CurationStatus`) são `dataclass(frozen=True)` + `enum` da
stdlib, com invariantes em `__post_init__` levantando exceções semânticas.
`pydantic` fica só em `application/dto.py`, validando a entrada dos casos de
uso e da CLI antes de chegar ao Domain.

## Consequências

- Domain testável isoladamente, sem dependência de framework de validação.
- Validação acontece em duas camadas com propósitos distintos: DTO (forma) e
  Domain (invariantes de negócio).
- Duplicação pequena entre regras do DTO (ex.: padrão do alias) e do Domain —
  aceitável, pois protege a fronteira mesmo que o Domain seja usado
  diretamente por outro chamador no futuro.
