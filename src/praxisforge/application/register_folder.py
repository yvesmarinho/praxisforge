# -*- coding: utf-8 -*-
"""
NOME: register_folder.py
TITULO: Caso de uso — registrar uma pasta a curar (idempotente)
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:55
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.dto, praxisforge.application.ports
HISTÓRICO:
    - 22/09/2026 09:45: criação (T035) — faz tests/unit/application/test_register_folder.py passar
STATUS: DEV
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from praxisforge.application.dto import RegisterFolderInput
from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import FolderRegistryRepository
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import AliasAlreadyRegisteredError
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegisterFolderResult:
    """Resultado do caso de uso register_folder."""

    outcome: str  # "registrado" ou "inalterado"


def register_folder(
    repository: FolderRegistryRepository, data: RegisterFolderInput
) -> RegisterFolderResult:
    """
    Registra uma pasta; idempotente se os dados forem idênticos aos já registrados.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param data: entrada validada (já passou pelo DTO pydantic).
    :type data: RegisterFolderInput
    :return: resultado com `outcome` "registrado" ou "inalterado".
    :rtype: RegisterFolderResult
    :raises AliasAlreadyRegisteredError: alias já registrado com dados diferentes.
    """
    registry = (
        repository.load() if repository.exists() else FolderRegistry(schema_version="1", folders={})
    )
    last_scanned: datetime | None = None
    folder = Folder(
        alias=Alias(data.alias),
        description=data.description,
        content_type=data.content_type,
        license=data.license,
        last_scanned=last_scanned,
        status=CurationStatus.from_str(data.status or "not_scanned"),
    )
    existing = registry.folders.get(data.alias)
    try:
        updated_registry = registry.add(folder)
    except AliasAlreadyRegisteredError:
        log_event(
            logger,
            event="register_folder",
            alias=data.alias,
            outcome="falha",
            error_type="AliasAlreadyRegisteredError",
        )
        raise
    if existing == folder:
        log_event(
            logger, event="register_folder", alias=data.alias, outcome="inalterado", error_type=None
        )
        return RegisterFolderResult(outcome="inalterado")
    repository.save(updated_registry)
    log_event(
        logger, event="register_folder", alias=data.alias, outcome="registrado", error_type=None
    )
    return RegisterFolderResult(outcome="registrado")
