# -*- coding: utf-8 -*-
"""
NOME: curation_state.py
TITULO: Estado da curadoria de uma pasta — reconciliação incremental e situação
DATA: 25/09/2026 15:08
MODIFICADO: 25/09/2026 14:54
VERSÃO: 0.1.0
DEPEND: (nenhuma — stdlib apenas; camada Domain)
HISTÓRICO:
    - 25/09/2026 15:08: criação (T024, T028, feature 010) — faz test_curation_state.py passar
STATUS: DEV
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from types import MappingProxyType

from praxisforge.domain.curation_artifact import (
    ArtifactKind,
    Manifest,
    Stage,
    is_final,
    validate_relative_path,
)
from praxisforge.domain.errors import InvalidCurationArtifactError

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ArtifactState:
    """Estado de um artefato curável: último hash, etapa, veredito, falha e tentativas."""

    kind: ArtifactKind
    sha256: str
    stage: Stage
    verdict: str | None = None
    last_error: str | None = None
    attempts: int = 0

    def __post_init__(self) -> None:
        if not _SHA256.match(self.sha256):
            raise InvalidCurationArtifactError("sha256 do estado fora do formato")
        if self.attempts < 0:
            raise InvalidCurationArtifactError("tentativas negativas")


@dataclass(frozen=True)
class CurationState:
    """
    Estado da curadoria de uma pasta: só artefatos curáveis (exclusões ficam no manifesto).

    :raises InvalidCurationArtifactError: data sem fuso ou caminho inválido.
    """

    alias: str
    conventions_version: str
    updated_at: datetime
    artifacts: Mapping[str, ArtifactState]

    def __post_init__(self) -> None:
        if self.updated_at.tzinfo is None:
            raise InvalidCurationArtifactError("updated_at sem fuso horário")
        for path in self.artifacts:
            validate_relative_path(path)
        ordenado = dict(sorted(self.artifacts.items()))
        object.__setattr__(self, "artifacts", MappingProxyType(ordenado))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CurationState):
            return NotImplemented
        return (
            self.alias == other.alias
            and self.conventions_version == other.conventions_version
            and self.updated_at == other.updated_at
            and dict(self.artifacts) == dict(other.artifacts)
        )

    __hash__ = None  # type: ignore[assignment]


class Situation(Enum):
    """Situação da curadoria de uma pasta (FR-017)."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    NOT_INVENTORIED = "not_inventoried"

    def label_pt_br(self) -> str:
        """
        Rótulo exibido na CLI.

        :Example:

        >>> Situation.NOT_INVENTORIED.label_pt_br()
        'sem inventário'
        """
        return {
            Situation.COMPLETE: "completa",
            Situation.INCOMPLETE: "incompleta",
            Situation.NOT_INVENTORIED: "sem inventário",
        }[self]


def situation(state: CurationState | None) -> Situation:
    """
    Completa só quando todo artefato está em etapa final (FR-018).

    :param state: estado da pasta, ou None se nunca inventariada.
    :type state: CurationState | None
    :return: situação da pasta.
    :rtype: Situation
    """
    if state is None:
        return Situation.NOT_INVENTORIED
    if all(is_final(s.stage, s.verdict) for s in state.artifacts.values()):
        return Situation.COMPLETE
    return Situation.INCOMPLETE


def stage_counts(state: CurationState) -> dict[Stage, int]:
    """
    Total de artefatos por etapa, com todas as etapas presentes (zeros incluídos).

    :param state: estado da pasta.
    :type state: CurationState
    :return: contagem na ordem de `Stage`.
    :rtype: dict[Stage, int]
    """
    contagem = dict.fromkeys(Stage, 0)
    for artefato in state.artifacts.values():
        contagem[artefato.stage] += 1
    return contagem


def reconcile(previous: CurationState | None, manifest: Manifest, now: datetime) -> CurationState:
    """
    Aplica um novo manifesto ao estado anterior (FR-015, FR-016).

    Novo → pendente; hash ou tipo diferente → pendente (veredito e falha limpos, tentativas
    mantidas); inalterado → mantém; ausente → removido (fica no estado); removido que
    reaparece → pendente.

    :param previous: estado anterior (None no primeiro inventário).
    :type previous: CurationState | None
    :param manifest: manifesto recém-gerado.
    :type manifest: Manifest
    :param now: instante da reconciliação (com fuso).
    :type now: datetime
    :return: novo estado.
    :rtype: CurationState
    :raises InvalidCurationArtifactError: estado anterior de outro alias.
    """
    anteriores: Mapping[str, ArtifactState] = {}
    if previous is not None:
        if previous.alias != manifest.alias:
            raise InvalidCurationArtifactError(
                f"estado de '{previous.alias}' aplicado a '{manifest.alias}'"
            )
        anteriores = previous.artifacts
    novos: dict[str, ArtifactState] = {}
    for artefato in manifest.artifacts:
        antigo = anteriores.get(artefato.path)
        if antigo is None:
            novos[artefato.path] = ArtifactState(artefato.kind, artefato.sha256, Stage.PENDING)
        elif (
            antigo.sha256 != artefato.sha256
            or antigo.kind is not artefato.kind
            or antigo.stage is Stage.REMOVED
        ):
            novos[artefato.path] = replace(
                antigo,
                kind=artefato.kind,
                sha256=artefato.sha256,
                stage=Stage.PENDING,
                verdict=None,
                last_error=None,
            )
        else:
            novos[artefato.path] = antigo
    for path, antigo in anteriores.items():
        if path not in novos:
            novos[path] = replace(antigo, stage=Stage.REMOVED)
    return CurationState(manifest.alias, manifest.conventions_version, now, novos)
