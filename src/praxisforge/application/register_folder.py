# -*- coding: utf-8 -*-
"""
NOME: register_folder.py
TITULO: Caso de uso — registrar uma pasta a curar (idempotente)
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.dto, praxisforge.application.ports
HISTÓRICO:
    - 22/09/2026 09:45: criação (T035) — faz tests/unit/application/test_register_folder.py passar
    - 23/09/2026 16:54: path canonizado via FolderLocator (T024, feature 005)
STATUS: DEV
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from praxisforge.application.dto import RegisterFolderInput
from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import FolderLocator, FolderRegistryRepository
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    AliasAlreadyRegisteredError,
    NestedFolderPathError,
    PathAlreadyRegisteredError,
)
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegisterFolderResult:
    """Resultado do caso de uso register_folder."""

    outcome: str  # "registrado" ou "inalterado"


def register_folder(
    repository: FolderRegistryRepository,
    data: RegisterFolderInput,
    *,
    locator: FolderLocator,
) -> RegisterFolderResult:
    """
    Registra uma pasta; idempotente se os dados forem idênticos aos já registrados.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param data: entrada validada (já passou pelo DTO pydantic).
    :type data: RegisterFolderInput
    :param locator: porta que canoniza e confere o caminho informado.
    :type locator: FolderLocator
    :return: resultado com `outcome` "registrado" ou "inalterado".
    :rtype: RegisterFolderResult
    :raises AliasAlreadyRegisteredError: alias já registrado com dados diferentes.
    :raises PathAlreadyRegisteredError: caminho já usado por outra pasta.
    :raises NestedFolderPathError: caminho dentro de (ou contendo) outra pasta.
    :raises FolderPathInvalidError: caminho inexistente ou não é pasta.
    :raises FolderPathUnreadableError: sem permissão de listar/entrar.
    """
    registry = (
        repository.load() if repository.exists() else FolderRegistry(schema_version="2", folders={})
    )
    last_scanned: datetime | None = None
    caminho = locator.canonicalize(data.alias, data.path)
    folder = Folder(
        alias=Alias(data.alias),
        description=data.description,
        content_type=data.content_type,
        license=data.license,
        last_scanned=last_scanned,
        status=CurationStatus.from_str(data.status or "not_scanned"),
        path=str(caminho),
    )
    existing = registry.folders.get(data.alias)
    try:
        updated_registry = registry.add(folder)
    except (
        AliasAlreadyRegisteredError,
        PathAlreadyRegisteredError,
        NestedFolderPathError,
    ) as error:
        log_event(
            logger,
            event="register_folder",
            alias=data.alias,
            outcome="falha",
            error_type=type(error).__name__,
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
