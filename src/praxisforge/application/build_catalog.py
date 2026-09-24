# -*- coding: utf-8 -*-
"""
NOME: build_catalog.py
TITULO: Caso de uso — gerar o catálogo de skills (skills/README.md) determinístico
DATA: 24/09/2026 16:54
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.skill, praxisforge.application.validate_skills
HISTÓRICO:
    - 24/09/2026 16:54: criação (T025, feature 008) — faz test_build_catalog.py passar
STATUS: DEV
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import (
    CatalogWriter,
    ContractValidator,
    SkillRepository,
    SourceReader,
)
from praxisforge.application.validate_skills import SkillFailure, validate_skills
from praxisforge.domain.skill import Skill

logger = logging.getLogger(__name__)

_CABECALHO = (
    "<!-- Arquivo gerado por `praxisforge skills catalog` — não editar à mão. -->\n"
    "\n"
    "# Catálogo de skills\n"
    "\n"
    "Skills versionadas em `skills/`. Para criar uma nova, parta de `skills/_template/`.\n"
    "\n"
)


@dataclass(frozen=True)
class CatalogResult:
    """Skills catalogadas (ordem alfabética) e skills omitidas por serem inválidas."""

    skills: list[str]
    omitted: list[SkillFailure]


def _celula(texto: str) -> str:
    return " ".join(texto.split()).replace("|", "\\|")


def render_catalog(skills: Sequence[Skill]) -> str:
    """
    Monta o Markdown do catálogo, sem data de geração (determinístico).

    :param skills: skills válidas, em qualquer ordem.
    :type skills: Sequence[Skill]
    :return: conteúdo completo de `skills/README.md`.
    :rtype: str
    """
    if not skills:
        return _CABECALHO + "Nenhuma skill cadastrada ainda.\n"
    linhas = [
        "| Skill | Propósito | Versão | Caminho | Fontes |",
        "|---|---|---|---|---|",
    ]
    for skill in sorted(skills, key=lambda s: s.name):
        fontes = ", ".join(sorted(skill.sources)) if skill.sources else "autoral"
        linhas.append(
            f"| {skill.name} | {_celula(skill.description)} | {skill.version} "
            f"| `skills/{skill.name}/` | {fontes} |"
        )
    return _CABECALHO + "\n".join(linhas) + "\n"


def build_catalog(
    repository: SkillRepository,
    validator: ContractValidator,
    source_reader: SourceReader,
    source_paths: Sequence[Path],
    writer: CatalogWriter,
) -> CatalogResult:
    """
    Valida todas as skills, grava o catálogo só com as válidas e informa as omitidas.

    :param repository: porta de leitura das skills.
    :type repository: SkillRepository
    :param validator: validação dos contratos.
    :type validator: ContractValidator
    :param source_reader: leitura das fontes.
    :type source_reader: SourceReader
    :param source_paths: registros de fonte disponíveis.
    :type source_paths: Sequence[Path]
    :param writer: gravação atômica do catálogo.
    :type writer: CatalogWriter
    :return: skills catalogadas e omitidas.
    :rtype: CatalogResult
    :raises CatalogWriteError: falha ao gravar; o catálogo anterior permanece.
    """
    report = validate_skills(repository, validator, source_reader, source_paths, None)
    writer.write(render_catalog(report.ok))
    nomes = sorted(skill.name for skill in report.ok)
    log_event(
        logger,
        event="build_catalog",
        alias="*",
        outcome=f"{len(nomes)} skills, {len(report.failures)} omitidas",
        error_type=None,
    )
    return CatalogResult(skills=nomes, omitted=report.failures)
