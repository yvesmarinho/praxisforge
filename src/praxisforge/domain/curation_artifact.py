# -*- coding: utf-8 -*-
"""
NOME: curation_artifact.py
TITULO: Entidades do inventário de curadoria — tipos, etapas, artefato, exclusão e manifesto
DATA: 25/09/2026 14:56
MODIFICADO: 25/09/2026 14:51
VERSÃO: 0.1.0
DEPEND: (nenhuma — stdlib apenas; camada Domain)
HISTÓRICO:
    - 25/09/2026 14:56: criação (T008, feature 010) — faz test_curation_artifact.py passar
STATUS: DEV
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar

from praxisforge.domain.errors import InvalidCurationArtifactError, PraxisForgeError

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_E = TypeVar("_E", bound="_FromStr")


class _FromStr(Enum):
    @classmethod
    def from_str(cls: type[_E], value: str) -> _E:
        """
        Converte o valor serializado no membro do enum.

        :param value: valor serializado (ex.: `"pending"`).
        :type value: str
        :return: membro correspondente.
        :raises PraxisForgeError: valor desconhecido.

        :Example:

        >>> Stage.from_str("pending") is Stage.PENDING
        True
        """
        try:
            return cls(value)
        except ValueError as error:
            raise PraxisForgeError(f"{cls.__name__} desconhecido: {value!r}") from error


class ArtifactKind(_FromStr):
    """Tipo de um artefato de curadoria encontrado numa pasta."""

    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    HOOK = "hook"
    RULE = "rule"
    REFERENCE = "reference"
    PROJECT_INSTRUCTION = "project_instruction"
    UNKNOWN = "unknown"


class Stage(_FromStr):
    """Etapa de um artefato no ciclo de curadoria (010 atribui só PENDING e REMOVED)."""

    PENDING = "pending"
    TRIAGED = "triaged"
    DRAFTED = "drafted"
    REVIEWED = "reviewed"
    PROMOTED = "promoted"
    FAILED = "failed"
    DISCARDED = "discarded"
    REMOVED = "removed"


class ExclusionReason(_FromStr):
    """Motivo pelo qual um arquivo ou diretório ficou fora da curadoria (FR-005, FR-006)."""

    FIXED_DIR = "fixed_dir"
    GITIGNORE = "gitignore"
    TOO_LARGE = "too_large"
    BINARY = "binary"
    SYMLINK_OUTSIDE = "symlink_outside"
    SYMLINK_DIR = "symlink_dir"
    UNREADABLE = "unreadable"
    UNCURATED = "uncurated"


_FINAL_STAGES = (Stage.PROMOTED, Stage.DISCARDED, Stage.REMOVED)


def is_final(stage: Stage, verdict: str | None) -> bool:
    """
    Diz se a etapa encerra a curadoria do artefato (FR-018).

    :param stage: etapa atual.
    :type stage: Stage
    :param verdict: veredito da revisão (None enquanto não houver).
    :type verdict: str | None
    :return: True para promovido, descartado, removido ou revisado com veredito aceito.
    :rtype: bool

    :Example:

    >>> is_final(Stage.REVIEWED, "accepted"), is_final(Stage.PENDING, None)
    (True, False)
    """
    if stage in _FINAL_STAGES:
        return True
    return stage is Stage.REVIEWED and verdict == "accepted"


def validate_relative_path(path: str) -> None:
    """
    Garante caminho relativo POSIX, sem `..`, sem barra inicial ou final.

    :param path: caminho relativo à pasta inventariada.
    :type path: str
    :raises InvalidCurationArtifactError: caminho fora da forma exigida.

    :Example:

    >>> validate_relative_path("skills/x")
    """
    if not path or path.startswith("/") or path.endswith("/"):
        raise InvalidCurationArtifactError(f"caminho relativo inválido: {path!r}")
    if any(parte in ("", ".", "..") for parte in path.split("/")):
        raise InvalidCurationArtifactError(f"caminho relativo inválido: {path!r}")


@dataclass(frozen=True)
class Artifact:
    """
    Unidade de curadoria: arquivo ou diretório (skill, hook) com o hash do conteúdo.

    :param path: caminho relativo à pasta.
    :param kind: tipo do artefato.
    :param size: bytes (soma dos arquivos, se diretório).
    :param sha256: impressão do conteúdo.
    :param files: arquivos cobertos (≥ 1).
    """

    path: str
    kind: ArtifactKind
    size: int
    sha256: str
    files: int

    def __post_init__(self) -> None:
        validate_relative_path(self.path)
        if self.size < 0:
            raise InvalidCurationArtifactError(f"{self.path}: tamanho negativo")
        if self.files < 1:
            raise InvalidCurationArtifactError(f"{self.path}: nenhum arquivo coberto")
        if not _SHA256.match(self.sha256):
            raise InvalidCurationArtifactError(f"{self.path}: sha256 fora do formato")


@dataclass(frozen=True)
class ExcludedEntry:
    """Arquivo ou diretório fora da curadoria, com o motivo (fica só no manifesto)."""

    path: str
    reason: ExclusionReason
    is_dir: bool

    def __post_init__(self) -> None:
        validate_relative_path(self.path)


@dataclass(frozen=True)
class Manifest:
    """
    Resultado determinístico do inventário de uma pasta (sem data — FR-007).

    Artefatos e exclusões são ordenados por caminho; caminho de artefato repetido é recusado.
    """

    alias: str
    conventions_version: str
    artifacts: tuple[Artifact, ...]
    excluded: tuple[ExcludedEntry, ...]

    def __post_init__(self) -> None:
        caminhos = [artefato.path for artefato in self.artifacts]
        if len(set(caminhos)) != len(caminhos):
            raise InvalidCurationArtifactError("caminho de artefato repetido no manifesto")
        object.__setattr__(self, "artifacts", tuple(sorted(self.artifacts, key=lambda a: a.path)))
        object.__setattr__(self, "excluded", tuple(sorted(self.excluded, key=lambda e: e.path)))
