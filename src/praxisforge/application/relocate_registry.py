# -*- coding: utf-8 -*-
"""
NOME: relocate_registry.py
TITULO: Caso de uso — realocar o registro de pastas para o local fora do repositório
DATA: 24/09/2026 14:35
MODIFICADO: 24/09/2026 14:35
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports, praxisforge.application.logging_events
HISTÓRICO:
    - 24/09/2026 14:35: criação (T030, feature 007) — faz test_relocate_registry.py passar
STATUS: DEV
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import FolderRegistryRepository, RegistryFileMover
from praxisforge.domain.errors import NothingToRelocateError, RegistryAlreadyExistsError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RelocationResult:
    """Resultado da realocação: destino e quantidade de pastas movidas."""

    target: Path
    folders: int


def relocate_registry(
    source: FolderRegistryRepository,
    target: FolderRegistryRepository,
    mover: RegistryFileMover,
    *,
    source_path: Path,
    target_path: Path,
) -> RelocationResult:
    """
    Valida a origem e move o arquivo do registro para o destino, sem sobrescrever.

    :param source: repositório do registro de origem (valida no load).
    :type source: FolderRegistryRepository
    :param target: repositório do destino (só para saber se já existe).
    :type target: FolderRegistryRepository
    :param mover: porta que move o arquivo.
    :type mover: RegistryFileMover
    :param source_path: arquivo de origem.
    :type source_path: Path
    :param target_path: arquivo de destino.
    :type target_path: Path
    :return: destino e quantidade de pastas.
    :rtype: RelocationResult
    :raises RegistryAlreadyExistsError: destino já existe.
    :raises RegistryFileNotFoundError: origem ausente.
    :raises RegistryMigrationRequiredError: origem no formato v1.
    :raises ContractValidationError: origem inválida.
    :raises NothingToRelocateError: origem sem pastas.
    :raises RegistryRelocationError: falha de I/O ao mover (origem intacta).
    """
    if target.exists():
        raise RegistryAlreadyExistsError(str(target_path))
    registro = source.load()
    quantidade = len(registro.list())
    if quantidade == 0:
        raise NothingToRelocateError()
    mover.move(source_path, target_path)
    log_event(
        logger,
        event="relocate_registry",
        alias="*",
        outcome=f"{quantidade} pastas movidas",
        error_type=None,
    )
    return RelocationResult(target=target_path, folders=quantidade)
