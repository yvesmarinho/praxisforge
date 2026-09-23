# -*- coding: utf-8 -*-
"""
NOME: folder.py
TITULO: Entidade Folder — pasta a curar, com invariantes de negócio
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 12:07
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.alias, praxisforge.domain.curation_status, praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 09:45: criação (T020) — faz tests/unit/domain/test_folder.py passar
    - 22/09/2026 17:41: invariante relaxada (T008, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:07: +last_curated_commit com validação de formato (T012, feature 004)
STATUS: DEV
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    FutureScanDateError,
    InvalidCommitHashError,
    InvalidFolderError,
    InvalidFolderPathError,
    UnknownLicenseRequiresPendingError,
)

_CONTENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,62}$")
_COMMIT_HASH_PATTERN = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")


@dataclass(frozen=True)
class Folder:
    """
    Entidade Folder — uma pasta registrada para curadoria.

    :param alias: identificador único (imutável após criação).
    :type alias: Alias
    :param description: descrição não vazia, até 500 caracteres.
    :type description: str
    :param content_type: slug `^[a-z][a-z0-9_-]{1,62}$`.
    :type content_type: str
    :param license: identificador SPDX ou o literal `"unknown"`.
    :type license: str
    :param last_scanned: data/hora da última varredura (com timezone) ou None.
    :type last_scanned: datetime | None
    :param status: status de curadoria.
    :type status: CurationStatus
    :param path: caminho absoluto canônico da pasta (feature 005): começa com "/", sem "~",
        sem segmentos "." / ".." e sem barra final.
    :type path: str
    :param last_curated_commit: hash do commit revisado na última curadoria (histórico) ou None.
    :type last_curated_commit: str | None
    :raises InvalidFolderError: quando uma invariante é violada.
    :raises UnknownLicenseRequiresPendingError: licença `unknown` com status != pending.
    :raises FutureScanDateError: `last_scanned` no futuro.
    :raises InvalidFolderPathError: `path` fora da forma absoluta canônica.
    :raises InvalidCommitHashError: `last_curated_commit` fora do formato SHA-1/SHA-256.
    """

    alias: Alias
    description: str
    content_type: str
    license: str  # noqa: A003 - nome do domínio, não da builtin
    last_scanned: datetime | None
    status: CurationStatus
    path: str
    last_curated_commit: str | None = None

    def __post_init__(self) -> None:
        if not self.description or len(self.description) > 500:
            raise InvalidFolderError(
                f"pasta '{self.alias}': descrição vazia ou maior que 500 caracteres"
            )
        if not _CONTENT_TYPE_PATTERN.match(self.content_type):
            raise InvalidFolderError(f"pasta '{self.alias}': content_type fora do formato slug")
        if not self.license:
            raise InvalidFolderError(f"pasta '{self.alias}': licença vazia")
        if self.license == "unknown" and self.status not in (
            CurationStatus.PENDING,
            CurationStatus.IGNORE,
        ):
            raise UnknownLicenseRequiresPendingError(str(self.alias))
        if self.status is CurationStatus.NOT_SCANNED and self.last_scanned is not None:
            raise InvalidFolderError(
                f"pasta '{self.alias}': status 'not_scanned' exige last_scanned nulo"
            )
        if self.last_scanned is not None:
            if self.last_scanned.tzinfo is None:
                raise InvalidFolderError(
                    f"pasta '{self.alias}': last_scanned sem timezone (offset obrigatório)"
                )
            if self.last_scanned > datetime.now(UTC):
                raise FutureScanDateError(str(self.alias))
        _validar_forma_do_path(str(self.alias), self.path)
        if self.last_curated_commit is not None and not _COMMIT_HASH_PATTERN.match(
            self.last_curated_commit
        ):
            raise InvalidCommitHashError(str(self.alias))


def _validar_forma_do_path(alias: str, path: str) -> None:
    """
    Valida só a forma do caminho (sem acessar o disco — constituição I).

    :param alias: alias da pasta (para a mensagem).
    :type alias: str
    :param path: caminho a validar.
    :type path: str
    :raises InvalidFolderPathError: vazio, relativo, com "~", "." / ".." ou barra final.

    :Example:

    >>> _validar_forma_do_path("repo", "/srv/pastas/repo")
    >>> _validar_forma_do_path("repo", "/")
    """
    if not isinstance(path, str) or not path.startswith("/"):
        raise InvalidFolderPathError(alias, "caminho precisa ser absoluto")
    if path == "/":
        return
    segmentos = path.split("/")[1:]
    if any(segmento in ("", ".", "..") for segmento in segmentos) or "~" in segmentos[0]:
        raise InvalidFolderPathError(alias, "caminho fora da forma canônica")
