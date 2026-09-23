# -*- coding: utf-8 -*-
"""
NOME: update_folder.py
TITULO: Caso de uso — atualizar status, última varredura e/ou licença (atômico)
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 16:55
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.dto, praxisforge.application.ports
HISTÓRICO:
    - 22/09/2026 09:45: criação (T037) — faz tests/unit/application/test_update_folder.py passar
    - 23/09/2026 12:08: grava last_curated_commit ao marcar curated (T021, feature 004)
    - 23/09/2026 16:55: FolderLocator; --path (T024, feature 005)
STATUS: DEV
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from praxisforge.application.dto import UpdateFolderInput
from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import (
    FolderLocator,
    FolderRegistryRepository,
    GitContentInspector,
)
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import ContentInspectionError
from praxisforge.domain.folder import Folder

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UpdateFolderResult:
    """
    Resultado de `update_folder`.

    :param folder: a pasta já atualizada.
    :type folder: Folder
    :param head_recorded: ao marcar `curated`: True se o HEAD foi gravado, False se a pasta
        não é repositório git (ou não tem commits); None quando o status resultante não é
        `curated` (git não consultado).
    :type head_recorded: bool | None
    """

    folder: Folder
    head_recorded: bool | None


def update_folder(
    repository: FolderRegistryRepository,
    data: UpdateFolderInput,
    *,
    locator: FolderLocator,
    inspector: GitContentInspector,
) -> UpdateFolderResult:
    """
    Atualiza os campos informados de uma pasta, atomicamente.

    Quando o curador marca `--status curated`, resolve o caminho real da pasta e grava o
    HEAD atual em `last_curated_commit` (FR-001); pasta não-git mantém o valor anterior
    (FR-002, FR-016). Qualquer outro status não consulta o git e preserva a versão
    gravada como histórico (FR-010).

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param data: entrada validada (só os campos informados são aplicados).
    :type data: UpdateFolderInput
    :param locator: porta que canoniza (`--path`) e confere o caminho registrado.
    :type locator: FolderLocator
    :param inspector: porta de inspeção do conteúdo versionado.
    :type inspector: GitContentInspector
    :return: a pasta atualizada e se o HEAD foi gravado.
    :rtype: UpdateFolderResult
    :raises FolderNotFoundError: alias não registrado.
    :raises FutureScanDateError: `last_scanned` no futuro.
    :raises UnknownLicenseRequiresPendingError: licença `unknown` com status != pending.
    :raises FolderPathInvalidError: `--path` inexistente, ou curated com pasta movida (FR-003).
    :raises FolderPathUnreadableError: marcar curated com caminho ilegível (FR-003).
    :raises ContentInspectionError: falha do git ao ler o HEAD (FR-009).
    """
    registry = repository.load()
    status = CurationStatus.from_str(data.status) if data.status is not None else None
    last_scanned = datetime.fromisoformat(data.last_scanned) if data.last_scanned else None
    head_recorded: bool | None = None
    try:
        novo_path = (
            str(locator.canonicalize(data.alias, data.path)) if data.path is not None else None
        )
        updated_registry = registry.update(
            data.alias,
            status=status,
            last_scanned=last_scanned,
            license=data.license,
            path=novo_path,
        )
        # só o ato explícito de marcar curated grava a versão (editar outro campo não)
        if status is CurationStatus.CURATED:
            head = _head_commit(updated_registry.get(data.alias), locator, inspector)
            head_recorded = head is not None
            if head is not None:
                updated_registry = updated_registry.update(data.alias, last_curated_commit=head)
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
    return UpdateFolderResult(folder=updated_registry.get(data.alias), head_recorded=head_recorded)


def _head_commit(
    folder: Folder, locator: FolderLocator, inspector: GitContentInspector
) -> str | None:
    """
    Confere o caminho da pasta e lê o HEAD, anexando o alias a falhas do inspector.

    :param folder: pasta já atualizada (caminho do registro).
    :type folder: Folder
    :param locator: porta que confere o caminho registrado.
    :type locator: FolderLocator
    :param inspector: porta de inspeção do conteúdo versionado.
    :type inspector: GitContentInspector
    :return: hash do HEAD ou None (não-git / sem commits).
    :rtype: str | None
    :raises ContentInspectionError: falha do git, com o alias preenchido.
    """
    alias = folder.alias.value
    path = locator.check(alias, Path(folder.path))
    try:
        return inspector.head_commit(path)
    except ContentInspectionError as error:
        raise ContentInspectionError(alias, error.reason) from error
