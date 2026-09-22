# -*- coding: utf-8 -*-
"""
NOME: scan_folders.py
TITULO: Casos de uso — varrer uma pasta registrada e varrer todas em lote (com detecção de
        aliases duplicados)
DATA: 22/09/2026 12:45
MODIFICADO: 22/09/2026 16:45
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports,
        praxisforge.application.resolve_folder_path, praxisforge.application.logging_events
HISTÓRICO:
    - 22/09/2026 12:45: criação (T005/T011/T017) — faz test_scan_folders.py passar
    - 22/09/2026 19:15: pular pastas ignore no lote (T032, feature 003-bootstrap-registro-pastas)
STATUS: DEV
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import FolderRegistryRepository, PathResolver
from praxisforge.application.resolve_folder_path import ItemFailure
from praxisforge.domain.curation_status import CurationStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScanResult:
    """Resultado de uma varredura individual bem-sucedida."""

    alias: str
    status: CurationStatus
    last_scanned: datetime


@dataclass(frozen=True)
class DuplicateAliasGroup:
    """Grupo de dois ou mais aliases cujo caminho real resolvido é idêntico (não persistido)."""

    aliases: tuple[str, ...]


@dataclass(frozen=True)
class ScanBatchReport:
    """Resultado de uma varredura em lote: itens ok, falhas por item e aliases duplicados."""

    ok: list[ScanResult]
    failures: list[ItemFailure]
    duplicates: list[DuplicateAliasGroup] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)


def _aplicar_varredura(
    repository: FolderRegistryRepository, alias: str, status_atual: CurationStatus
) -> ScanResult:
    """Persiste o efeito de uma varredura bem-sucedida (caminho já confirmado resolvível)."""
    registry = repository.load()
    last_scanned = datetime.now(UTC)
    novo_status = CurationStatus.SCANNED if status_atual is CurationStatus.NOT_SCANNED else None
    updated_registry = registry.update(alias, status=novo_status, last_scanned=last_scanned)
    repository.save(updated_registry)
    return ScanResult(
        alias=alias, status=updated_registry.get(alias).status, last_scanned=last_scanned
    )


def scan_folder(
    repository: FolderRegistryRepository, resolver: PathResolver, alias: str
) -> ScanResult:
    """
    Varre uma única pasta registrada: confirma que o caminho resolve e atualiza o registro.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param resolver: porta de resolução de caminho (ambiente).
    :type resolver: PathResolver
    :param alias: alias a varrer.
    :type alias: str
    :return: resultado da varredura (status resultante e timestamp).
    :rtype: ScanResult
    :raises FolderNotFoundError: alias não registrado (ambiente não é consultado).
    :raises FolderPathNotConfiguredError: variável ausente/vazia.
    :raises FolderPathInvalidError: caminho relativo, com `..`, inexistente ou não é diretório.
    :raises FolderPathUnreadableError: sem permissão de leitura.
    """
    # garante que o alias existe antes de consultar o ambiente
    folder = repository.load().get(alias)
    try:
        resolver.resolve(alias)
    except Exception as error:
        log_event(
            logger,
            event="scan_folder",
            alias=alias,
            outcome="falha",
            error_type=type(error).__name__,
        )
        raise
    resultado = _aplicar_varredura(repository, alias, folder.status)
    log_event(logger, event="scan_folder", alias=alias, outcome="ok", error_type=None)
    return resultado


def scan_all_folders(
    repository: FolderRegistryRepository, resolver: PathResolver
) -> ScanBatchReport:
    """
    Varre todos os aliases registrados; falha de um não afeta os demais.

    Também detecta, entre os aliases resolvidos com sucesso, grupos cujo caminho real é
    idêntico (mesmo diretório registrado sob dois ou mais aliases).

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param resolver: porta de resolução de caminho (ambiente).
    :type resolver: PathResolver
    :return: relatório com pastas atualizadas, falhas por item e grupos duplicados.
    :rtype: ScanBatchReport
    """
    registry = repository.load()
    ok: list[ScanResult] = []
    failures: list[ItemFailure] = []
    ignored: list[str] = []
    caminhos_por_alias: dict[str, Path] = {}
    for folder in registry.list():
        alias = folder.alias.value
        if folder.status is CurationStatus.IGNORE:
            ignored.append(alias)
            continue
        try:
            caminho = resolver.resolve(alias)
        except Exception as error:  # noqa: BLE001 - agrega falha por item, não interrompe o lote
            failures.append(
                ItemFailure(alias=alias, error_type=type(error).__name__, message=str(error))
            )
            continue
        caminhos_por_alias[alias] = caminho
        resultado = _aplicar_varredura(repository, alias, folder.status)
        ok.append(resultado)

    grupos: dict[Path, list[str]] = {}
    for alias, caminho in caminhos_por_alias.items():
        grupos.setdefault(caminho, []).append(alias)
    duplicates = [
        DuplicateAliasGroup(aliases=tuple(sorted(aliases)))
        for aliases in grupos.values()
        if len(aliases) >= 2
    ]
    duplicates.sort(key=lambda grupo: grupo.aliases[0])

    log_event(
        logger,
        event="scan_all_folders",
        alias="*",
        outcome=f"{len(ok)} ok, {len(failures)} com falha, {len(duplicates)} grupo(s) duplicado(s)",
        error_type=None,
    )
    return ScanBatchReport(ok=ok, failures=failures, duplicates=duplicates, ignored=ignored)
