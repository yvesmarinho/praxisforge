# -*- coding: utf-8 -*-
"""
NOME: validate_skills.py
TITULO: Caso de uso — validar skills (forma do SKILL.md + proveniência das fontes), em lote
DATA: 24/09/2026 16:54
MODIFICADO: 25/09/2026 13:05
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports, praxisforge.application.validate_sources
HISTÓRICO:
    - 24/09/2026 16:54: criação (T018, feature 008) — faz test_validate_skills.py passar
    - 25/09/2026 13:05: fontes v3 só ideias — qualquer fonte válida serve (T042, feature 009)
STATUS: DEV
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import ContractValidator, SkillRepository, SourceReader
from praxisforge.application.validate_sources import validate_sources
from praxisforge.domain.errors import (
    ContractValidationError,
    InvalidSkillError,
    PraxisForgeError,
    Violation,
)
from praxisforge.domain.skill import Skill

logger = logging.getLogger(__name__)

_SCHEMA = "skill-frontmatter-v1"


@dataclass(frozen=True)
class SkillFailure:
    """Falha de uma skill: nome, tipo da exceção e um motivo por violação."""

    name: str
    error_type: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SkillValidationReport:
    """Skills válidas (entidades) e falhas por skill, na ordem pedida."""

    ok: list[Skill]
    failures: list[SkillFailure]


@dataclass
class _IndiceDeFontes:
    """Slug → arquivos; cada fonte é avaliada uma única vez por lote."""

    reader: SourceReader
    validator: ContractValidator
    por_slug: dict[str, list[Path]]
    cache: dict[str, Violation | str] = field(default_factory=dict)

    def politica(self, slug: str) -> Violation | str:
        """Política da fonte válida, ou a violação que impede usá-la."""
        if slug not in self.cache:
            self.cache[slug] = self._avaliar(slug)
        return self.cache[slug]

    def _avaliar(self, slug: str) -> Violation | str:
        arquivos = self.por_slug.get(slug, [])
        if not arquivos:
            return Violation("metadata.sources", f"fonte '{slug}' não encontrada")
        if len(arquivos) > 1:
            return Violation("metadata.sources", f"slug ambíguo '{slug}' (mais de uma categoria)")
        report = validate_sources(self.reader, self.validator, arquivos)
        if report.failures:
            return Violation(
                "metadata.sources", f"fonte '{slug}' inválida: {report.failures[0].message}"
            )
        return "ok"


def _violacoes_de_proveniencia(skill: Skill, indice: _IndiceDeFontes) -> list[Violation]:
    # só ideias (feature 009): toda fonte válida serve; não há mais nível de extração
    violacoes: list[Violation] = []
    for slug in skill.sources:
        resultado = indice.politica(slug)
        if isinstance(resultado, Violation):
            violacoes.append(resultado)
    return violacoes


def _validar_uma(
    repository: SkillRepository,
    validator: ContractValidator,
    indice: _IndiceDeFontes,
    name: str,
) -> Skill:
    documento = repository.load(name)
    violacoes: list[Violation] = []
    skill: Skill | None = None
    try:
        skill = Skill.from_parts(
            name, documento.frontmatter, documento.references, documento.missing_references
        )
    except InvalidSkillError as error:
        violacoes.extend(error.violations)
    try:
        validator.validate(documento.frontmatter, schema_name=_SCHEMA)
    except ContractValidationError as error:
        ja_citados = {v.field for v in violacoes}
        violacoes.extend(v for v in error.violations if v.field not in ja_citados)
    if skill is not None:
        violacoes.extend(_violacoes_de_proveniencia(skill, indice))
    if violacoes or skill is None:
        raise InvalidSkillError(name, violacoes)
    return skill


def validate_skills(
    repository: SkillRepository,
    validator: ContractValidator,
    source_reader: SourceReader,
    source_paths: Sequence[Path],
    names: Sequence[str] | None,
) -> SkillValidationReport:
    """
    Valida as skills pedidas (forma e proveniência); a falha de uma não interrompe o lote.

    :param repository: porta de leitura das skills.
    :type repository: SkillRepository
    :param validator: validação contra `skill-frontmatter-v1` e `source-schema-v2`.
    :type validator: ContractValidator
    :param source_reader: leitura do frontmatter das fontes.
    :type source_reader: SourceReader
    :param source_paths: todos os registros de fonte (`src/data/sources/**/*.md`).
    :type source_paths: Sequence[Path]
    :param names: skills pedidas; None = todas.
    :type names: Sequence[str] | None
    :return: skills válidas e falhas por skill.
    :rtype: SkillValidationReport
    """
    por_slug: dict[str, list[Path]] = {}
    for path in sorted(source_paths):
        por_slug.setdefault(path.stem, []).append(path)
    indice = _IndiceDeFontes(reader=source_reader, validator=validator, por_slug=por_slug)
    pedidas = list(names) if names is not None else repository.list_names()
    ok: list[Skill] = []
    failures: list[SkillFailure] = []
    for name in pedidas:
        try:
            ok.append(_validar_uma(repository, validator, indice, name))
        except InvalidSkillError as error:
            motivos = tuple(f"{v.field}: {v.reason}" for v in error.violations)
            failures.append(SkillFailure(name, type(error).__name__, motivos))
        except PraxisForgeError as error:
            failures.append(SkillFailure(name, type(error).__name__, (str(error),)))
    log_event(
        logger,
        event="validate_skills",
        alias="*",
        outcome=f"{len(ok)} ok, {len(failures)} com falha",
        error_type=None,
    )
    return SkillValidationReport(ok=ok, failures=failures)
