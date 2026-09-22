# -*- coding: utf-8 -*-
"""
NOME: query_folders.py
TITULO: Casos de uso — listar e consultar pastas registradas
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:58
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports
HISTÓRICO:
    - 22/09/2026 09:45: criação (T036) — faz tests/unit/application/test_query_folders.py passar
STATUS: DEV
"""

import logging

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import FolderRegistryRepository
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.folder import Folder

logger = logging.getLogger(__name__)


def list_folders(repository: FolderRegistryRepository, status: str | None) -> list[Folder]:
    """
    Lista as pastas registradas, opcionalmente filtradas por status.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param status: valor de máquina do status a filtrar (ex.: `"pending"`); None lista todas.
    :type status: str | None
    :return: pastas ordenadas por alias.
    :rtype: list[Folder]
    :raises PraxisForgeError: `status` informado não é um valor conhecido.
    """
    registry = repository.load()
    folders = registry.list()
    if status is not None:
        wanted = CurationStatus.from_str(status)
        folders = [f for f in folders if f.status is wanted]
    log_event(logger, event="list_folders", alias="*", outcome="ok", error_type=None)
    return folders


def show_folder(repository: FolderRegistryRepository, alias: str) -> Folder:
    """
    Consulta todos os dados de uma pasta.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param alias: alias a consultar.
    :type alias: str
    :return: a pasta registrada.
    :rtype: Folder
    :raises FolderNotFoundError: alias não registrado.
    """
    registry = repository.load()
    try:
        folder = registry.get(alias)
    except Exception:
        log_event(
            logger,
            event="show_folder",
            alias=alias,
            outcome="falha",
            error_type="FolderNotFoundError",
        )
        raise
    log_event(logger, event="show_folder", alias=alias, outcome="ok", error_type=None)
    return folder
