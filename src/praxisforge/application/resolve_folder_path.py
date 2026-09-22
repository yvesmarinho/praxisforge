# -*- coding: utf-8 -*-
"""
NOME: resolve_folder_path.py
TITULO: Casos de uso — resolver alias → caminho real, individualmente e em lote
DATA: 22/09/2026 10:10
MODIFICADO: 22/09/2026 10:03
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports
HISTÓRICO:
    - 22/09/2026 10:10: criação (T047) — faz test_resolve_folder_path.py passar
STATUS: DEV
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import FolderRegistryRepository, PathResolver

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
    repository: FolderRegistryRepository, resolver: PathResolver, alias: str
) -> Path:
    """
    Resolve o caminho real de um único alias.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param resolver: porta de resolução de caminho (ambiente).
    :type resolver: PathResolver
    :param alias: alias a resolver.
    :type alias: str
    :return: caminho real, absoluto e legível.
    :rtype: Path
    :raises FolderNotFoundError: alias não registrado (ambiente não é consultado).
    :raises FolderPathNotConfiguredError: variável ausente/vazia.
    :raises FolderPathInvalidError: caminho relativo, com `..`, inexistente ou não é diretório.
    :raises FolderPathUnreadableError: sem permissão de leitura.
    """
    registry = repository.load()
    registry.get(alias)  # garante que o alias existe antes de consultar o ambiente
    path = resolver.resolve(alias)
    log_event(logger, event="resolve_folder_path", alias=alias, outcome="ok", error_type=None)
    return path


def resolve_all_folder_paths(
    repository: FolderRegistryRepository, resolver: PathResolver
) -> BatchReport:
    """
    Resolve o caminho real de todos os aliases registrados; falha de um não afeta os demais.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param resolver: porta de resolução de caminho (ambiente).
    :type resolver: PathResolver
    :return: relatório com aliases resolvidos e falhas por item.
    :rtype: BatchReport
    """
    registry = repository.load()
    ok: dict[str, Path] = {}
    failures: list[ItemFailure] = []
    for folder in registry.list():
        alias = folder.alias.value
        try:
            ok[alias] = resolver.resolve(alias)
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
