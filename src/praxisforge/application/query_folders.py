# -*- coding: utf-8 -*-
"""
NOME: query_folders.py
TITULO: Casos de uso — listar e consultar pastas registradas
DATA: 22/09/2026 09:45
MODIFICADO: 24/09/2026 10:57
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports
HISTÓRICO:
    - 22/09/2026 09:45: criação (T036) — faz tests/unit/application/test_query_folders.py passar
    - 24/09/2026 10:57: folder_policy — política máxima derivada da licença (T025, feature 006)
STATUS: DEV
"""

import logging
from dataclasses import dataclass

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import FolderRegistryRepository
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.folder import Folder
from praxisforge.domain.license_policy import ExtractPolicy, is_classified, max_policy

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FolderPolicy:
    """Política máxima de extração de uma pasta, derivada da licença (não persistida)."""

    maximum: ExtractPolicy
    classified: bool


def folder_policy(folder: Folder) -> FolderPolicy:
    """
    Política máxima de extração da pasta, considerando escopo de código (pior caso).

    :param folder: pasta registrada.
    :type folder: Folder
    :return: nível máximo e se a licença está classificada na tabela.
    :rtype: FolderPolicy
    """
    return FolderPolicy(
        maximum=max_policy(folder.license), classified=is_classified(folder.license)
    )


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
