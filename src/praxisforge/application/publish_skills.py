# -*- coding: utf-8 -*-
"""
NOME: publish_skills.py
TITULO: Caso de uso — publicar skills válidas (idempotente, regra de versão, órfãs/prune)
DATA: 24/09/2026 16:52
MODIFICADO: 24/09/2026 16:51
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports, praxisforge.application.validate_skills
HISTÓRICO:
    - 24/09/2026 16:52: criação (T035, feature 008) — faz test_publish_skills.py passar
STATUS: DEV
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import (
    ContractValidator,
    PublishedState,
    SkillPublisher,
    SkillRepository,
    SourceReader,
)
from praxisforge.application.validate_skills import validate_skills
from praxisforge.domain.errors import (
    ForeignSkillDestinationError,
    PraxisForgeError,
    SkillPublicationError,
    SkillVersionNotBumpedError,
)
from praxisforge.domain.skill import Skill

logger = logging.getLogger(__name__)

MODES = ("copy", "symlink")


@dataclass(frozen=True)
class PublishOutcome:
    """Resultado por skill: publicada, atualizada, inalterada ou recusada (com motivo)."""

    name: str
    status: str
    reason: str = ""
    error_type: str | None = None


@dataclass(frozen=True)
class PublishReport:
    """Resultados por skill, órfãs encontradas e órfãs removidas."""

    outcomes: list[PublishOutcome]
    orphans: list[str]
    removed: list[str]

    @property
    def environment_failure(self) -> bool:
        """Houve falha de gravação (exit 3)."""
        return any(o.error_type == SkillPublicationError.__name__ for o in self.outcomes)

    @property
    def refused(self) -> bool:
        """Alguma skill foi recusada (exit 1)."""
        return any(o.status == "recusada" for o in self.outcomes)


def _recusa(name: str, error: PraxisForgeError) -> PublishOutcome:
    return PublishOutcome(name, "recusada", str(error), type(error).__name__)


def _publicar_uma(
    repository: SkillRepository,
    publisher: SkillPublisher,
    dest_root: Path,
    skill: Skill,
    mode: str,
) -> PublishOutcome:
    estado: PublishedState = publisher.inspect(dest_root, skill.name)
    if estado.kind == "foreign":
        raise ForeignSkillDestinationError(skill.name, str(dest_root / skill.name))
    if mode == "symlink":
        if estado.kind == "symlink":
            return PublishOutcome(skill.name, "inalterada")
        publisher.publish_symlink(dest_root, skill.name)
        return PublishOutcome(skill.name, "publicada" if estado.kind == "absent" else "atualizada")
    content_hash = repository.content_hash(skill.name)
    if estado.kind == "copy":
        if estado.content_sha256 == content_hash:
            return PublishOutcome(skill.name, "inalterada")
        if estado.version == skill.version:
            raise SkillVersionNotBumpedError(skill.name, skill.version)
    publisher.publish_copy(dest_root, skill.name, skill.version, content_hash)
    return PublishOutcome(skill.name, "publicada" if estado.kind == "absent" else "atualizada")


def publish_skills(
    repository: SkillRepository,
    validator: ContractValidator,
    source_reader: SourceReader,
    source_paths: Sequence[Path],
    publisher: SkillPublisher,
    dest_root: Path,
    names: Sequence[str] | None,
    *,
    mode: str = "copy",
    prune: bool = False,
) -> PublishReport:
    """
    Valida e publica as skills pedidas; a falha de uma não interrompe o lote.

    Troca de modo (cópia ↔ symlink) entre destinos nossos sempre publica, sem regra de versão.

    :param repository: porta de leitura das skills.
    :type repository: SkillRepository
    :param validator: validação dos contratos.
    :type validator: ContractValidator
    :param source_reader: leitura das fontes.
    :type source_reader: SourceReader
    :param source_paths: registros de fonte disponíveis.
    :type source_paths: Sequence[Path]
    :param publisher: porta de publicação.
    :type publisher: SkillPublisher
    :param dest_root: pasta `.claude/skills` de destino.
    :type dest_root: Path
    :param names: skills pedidas; None = todas (e cálculo de órfãs).
    :type names: Sequence[str] | None
    :param mode: `copy` ou `symlink`.
    :type mode: str
    :param prune: remove órfãs nossas (só com `names=None`).
    :type prune: bool
    :return: resultado por skill, órfãs e removidas.
    :rtype: PublishReport
    :raises ValueError: modo desconhecido (erro da fronteira).
    """
    if mode not in MODES:
        raise ValueError(f"modo de publicação desconhecido: {mode}")
    report = validate_skills(repository, validator, source_reader, source_paths, names)
    outcomes = [
        PublishOutcome(f.name, "recusada", "; ".join(f.reasons), f.error_type)
        for f in report.failures
    ]
    for skill in report.ok:
        try:
            outcomes.append(_publicar_uma(repository, publisher, dest_root, skill, mode))
        except PraxisForgeError as error:
            outcomes.append(_recusa(skill.name, error))
    outcomes.sort(key=lambda o: o.name)

    orphans: list[str] = []
    removed: list[str] = []
    if names is None:
        existentes = set(repository.list_names())
        orphans = [n for n in publisher.list_published(dest_root) if n not in existentes]
        if prune:
            for orfa in orphans:
                try:
                    publisher.remove(dest_root, orfa)
                    removed.append(orfa)
                except PraxisForgeError as error:
                    outcomes.append(_recusa(orfa, error))
    for outcome in outcomes:
        log_event(
            logger,
            event="publish_skill",
            alias=outcome.name,
            outcome=outcome.status,
            error_type=outcome.error_type,
        )
    return PublishReport(outcomes=outcomes, orphans=orphans, removed=removed)
