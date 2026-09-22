# -*- coding: utf-8 -*-
"""
NOME: update_folder.py
TITULO: Caso de uso — atualizar status, última varredura e/ou licença (atômico)
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:55
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.dto, praxisforge.application.ports
HISTÓRICO:
    - 22/09/2026 09:45: criação (T037) — faz tests/unit/application/test_update_folder.py passar
STATUS: DEV
"""

import logging
from datetime import datetime

from praxisforge.application.dto import UpdateFolderInput
from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import FolderRegistryRepository
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.folder import Folder

logger = logging.getLogger(__name__)


def update_folder(repository: FolderRegistryRepository, data: UpdateFolderInput) -> Folder:
    """
    Atualiza os campos informados de uma pasta, atomicamente.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param data: entrada validada (só os campos informados são aplicados).
    :type data: UpdateFolderInput
    :return: a pasta já atualizada.
    :rtype: Folder
    :raises FolderNotFoundError: alias não registrado.
    :raises FutureScanDateError: `last_scanned` no futuro.
    :raises UnknownLicenseRequiresPendingError: licença `unknown` com status != pending.
    """
    registry = repository.load()
    status = CurationStatus.from_str(data.status) if data.status is not None else None
    last_scanned = datetime.fromisoformat(data.last_scanned) if data.last_scanned else None
    try:
        updated_registry = registry.update(
            data.alias, status=status, last_scanned=last_scanned, license=data.license
        )
    except Exception as error:
        log_event(
            logger,
            event="update_folder",
            alias=data.alias,
            outcome="falha",
            error_type=type(error).__name__,
        )
        raise
    repository.save(updated_registry)
    log_event(logger, event="update_folder", alias=data.alias, outcome="ok", error_type=None)
    return updated_registry.get(data.alias)
