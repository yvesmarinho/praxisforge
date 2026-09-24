<!-- Criado em: 24/09/2026 11:25 -->
<!-- Modificado em: 24/09/2026 11:25 -->

# Specification Quality Checklist: Registro de pastas fora do repositório

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 24/09/2026
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Caminhos (`~/.config`, `$XDG_CONFIG_HOME`, `--registry`, `PRAXISFORGE_REGISTRY`) são parte do contrato de uso definido pela constituição v3.0.0, não escolha de implementação.
- Decisões tomadas como padrão (sem clarificação): migração como comando da CLI que só move o arquivo; `PRAXISFORGE_REGISTRY` vazia é ignorada; aviso de registro antigo só quando ele não está vazio.
