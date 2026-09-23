# -*- coding: utf-8 -*-
"""
NOME: resolve_folder_path.py
TITULO: Casos de uso — resolver alias → caminho real, individualmente e em lote
DATA: 22/09/2026 10:10
MODIFICADO: 23/09/2026 16:55
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports
HISTÓRICO:
    - 22/09/2026 10:10: criação (T047) — faz test_resolve_folder_path.py passar
    - 23/09/2026 16:55: caminho do registro via FolderLocator (T025, feature 005)
STATUS: DEV
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import FolderLocator, FolderRegistryRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ItemFailure:
    """Falha de um item específico dentro de uma operação em lote."""

    alias: str
    error_type: str
    message: str


@dataclass(frozen=True)
class BatchReport:
    """Resultado de uma operação em lote: itens ok e falhas por item."""

    ok: dict[str, Path]
    failures: list[ItemFailure]


def resolve_folder_path(
    repository: FolderRegistryRepository, locator: FolderLocator, alias: str
) -> Path:
    """
    Resolve o caminho real de um único alias.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param locator: porta que confere o caminho registrado no disco.
    :type locator: FolderLocator
    :param alias: alias a resolver.
    :type alias: str
    :return: caminho real, absoluto e legível.
    :rtype: Path
    :raises FolderNotFoundError: alias não registrado (disco não é consultado).
    :raises FolderPathInvalidError: pasta movida/apagada ou não é diretório.
    :raises FolderPathUnreadableError: sem permissão de leitura.
    """
    registry = repository.load()
    folder = registry.get(alias)  # garante que o alias existe antes de consultar o disco
    path = locator.check(alias, Path(folder.path))
    log_event(logger, event="resolve_folder_path", alias=alias, outcome="ok", error_type=None)
    return path


def resolve_all_folder_paths(
    repository: FolderRegistryRepository, locator: FolderLocator
) -> BatchReport:
    """
    Resolve o caminho real de todos os aliases registrados; falha de um não afeta os demais.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param locator: porta que confere o caminho registrado no disco.
    :type locator: FolderLocator
    :return: relatório com aliases resolvidos e falhas por item.
    :rtype: BatchReport
    """
    registry = repository.load()
    ok: dict[str, Path] = {}
    failures: list[ItemFailure] = []
    for folder in registry.list():
        alias = folder.alias.value
        try:
            ok[alias] = locator.check(alias, Path(folder.path))
        except Exception as error:  # noqa: BLE001 - agrega falha por item, não interrompe o lote
            failures.append(
                ItemFailure(alias=alias, error_type=type(error).__name__, message=str(error))
            )
    log_event(
        logger,
        event="resolve_all_folder_paths",
        alias="*",
        outcome=f"{len(ok)} ok, {len(failures)} com falha",
        error_type=None,
    )
    return BatchReport(ok=ok, failures=failures)
