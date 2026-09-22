# -*- coding: utf-8 -*-
"""
NOME: folder.py
TITULO: Entidade Folder — pasta a curar, com invariantes de negócio
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 16:36
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.alias, praxisforge.domain.curation_status, praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 09:45: criação (T020) — faz tests/unit/domain/test_folder.py passar
    - 22/09/2026 17:41: invariante relaxada (T008, feature 003-bootstrap-registro-pastas)
STATUS: DEV
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    FutureScanDateError,
    InvalidFolderError,
    UnknownLicenseRequiresPendingError,
)

_CONTENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,62}$")


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
    :raises InvalidFolderError: quando uma invariante é violada.
    :raises UnknownLicenseRequiresPendingError: licença `unknown` com status != pending.
    :raises FutureScanDateError: `last_scanned` no futuro.
    """

    alias: Alias
    description: str
    content_type: str
    license: str  # noqa: A003 - nome do domínio, não da builtin
    last_scanned: datetime | None
    status: CurationStatus

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
