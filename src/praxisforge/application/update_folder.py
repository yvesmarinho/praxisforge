# -*- coding: utf-8 -*-
"""
NOME: update_folder.py
TITULO: Caso de uso — atualizar status, última varredura e/ou licença (atômico)
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 12:08
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.dto, praxisforge.application.ports
HISTÓRICO:
    - 22/09/2026 09:45: criação (T037) — faz tests/unit/application/test_update_folder.py passar
    - 23/09/2026 12:08: grava last_curated_commit ao marcar curated (T021, feature 004)
STATUS: DEV
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from praxisforge.application.dto import UpdateFolderInput
from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import (
    FolderRegistryRepository,
    GitContentInspector,
    PathResolver,
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
    resolver: PathResolver,
    inspector: GitContentInspector,
) -> UpdateFolderResult:
    """
    Atualiza os campos informados de uma pasta, atomicamente.

    Quando o status resultante é `curated`, resolve o caminho real da pasta e grava o
    HEAD atual em `last_curated_commit` (FR-001); pasta não-git mantém o valor anterior
    (FR-002, FR-016). Qualquer outro status não consulta o git e preserva a versão
    gravada como histórico (FR-010).

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param data: entrada validada (só os campos informados são aplicados).
    :type data: UpdateFolderInput
    :param resolver: porta de resolução alias → caminho real.
    :type resolver: PathResolver
    :param inspector: porta de inspeção do conteúdo versionado.
    :type inspector: GitContentInspector
    :return: a pasta atualizada e se o HEAD foi gravado.
    :rtype: UpdateFolderResult
    :raises FolderNotFoundError: alias não registrado.
    :raises FutureScanDateError: `last_scanned` no futuro.
    :raises UnknownLicenseRequiresPendingError: licença `unknown` com status != pending.
    :raises FolderPathNotConfiguredError: marcar curated sem caminho configurado (FR-003).
    :raises FolderPathInvalidError: marcar curated com caminho inválido (FR-003).
    :raises FolderPathUnreadableError: marcar curated com caminho ilegível (FR-003).
    :raises ContentInspectionError: falha do git ao ler o HEAD (FR-009).
    """
    registry = repository.load()
    status = CurationStatus.from_str(data.status) if data.status is not None else None
    last_scanned = datetime.fromisoformat(data.last_scanned) if data.last_scanned else None
    head_recorded: bool | None = None
    try:
        updated_registry = registry.update(
            data.alias, status=status, last_scanned=last_scanned, license=data.license
        )
        if updated_registry.get(data.alias).status is CurationStatus.CURATED:
            head = _head_commit(data.alias, resolver, inspector)
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


def _head_commit(alias: str, resolver: PathResolver, inspector: GitContentInspector) -> str | None:
    """
    Resolve o caminho da pasta e lê o HEAD, anexando o alias a falhas do inspector.

    :param alias: alias da pasta.
    :type alias: str
    :param resolver: porta de resolução alias → caminho real.
    :type resolver: PathResolver
    :param inspector: porta de inspeção do conteúdo versionado.
    :type inspector: GitContentInspector
    :return: hash do HEAD ou None (não-git / sem commits).
    :rtype: str | None
    :raises ContentInspectionError: falha do git, com o alias preenchido.
    """
    path = resolver.resolve(alias)
    try:
        return inspector.head_commit(path)
    except ContentInspectionError as error:
        raise ContentInspectionError(alias, error.reason) from error
