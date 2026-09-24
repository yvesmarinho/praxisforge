# -*- coding: utf-8 -*-
"""
NOME: scan_folders.py
TITULO: Casos de uso — varrer uma pasta registrada e varrer todas em lote (com detecção de
        aliases duplicados)
DATA: 22/09/2026 12:45
MODIFICADO: 24/09/2026 09:35
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports,
        praxisforge.application.resolve_folder_path, praxisforge.application.logging_events
HISTÓRICO:
    - 22/09/2026 12:45: criação (T005/T011/T017) — faz test_scan_folders.py passar
    - 22/09/2026 19:15: pular pastas ignore no lote (T032, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:15: verificação de conteúdo, ContentCheck (T028-T029, T035, feature 004)
    - 23/09/2026 16:55: caminho do registro via FolderLocator (T025, feature 005)
    - 24/09/2026 09:35: lote carrega/grava o registro uma única vez (desempenho em O(n))
STATUS: DEV
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import (
    FolderLocator,
    FolderRegistryRepository,
    GitContentInspector,
)
from praxisforge.application.resolve_folder_path import ItemFailure
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import ContentInspectionError
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry

logger = logging.getLogger(__name__)


class ContentCheck(Enum):
    """Resultado da verificação de conteúdo de uma pasta na varredura (feature 004)."""

    NOT_APPLICABLE = "not_applicable"
    NOT_GIT = "not_git"
    BASELINE_RECORDED = "baseline_recorded"
    UNCHANGED = "unchanged"
    REVERTED = "reverted"

    def label_pt_br(self) -> str:
        """
        Rótulo exibido na CLI.

        :return: rótulo em pt-BR.
        :rtype: str

        :Example:

        >>> ContentCheck.UNCHANGED.label_pt_br()
        'sem mudança'
        """
        return _CONTENT_CHECK_LABELS[self]


_CONTENT_CHECK_LABELS = {
    ContentCheck.NOT_APPLICABLE: "-",
    ContentCheck.NOT_GIT: "não verificado (não é repositório git)",
    ContentCheck.BASELINE_RECORDED: "referência registrada",
    ContentCheck.UNCHANGED: "sem mudança",
    ContentCheck.REVERTED: "mudou — revertida para em curadoria",
}


@dataclass(frozen=True)
class ScanResult:
    """Resultado de uma varredura individual bem-sucedida."""

    alias: str
    status: CurationStatus
    last_scanned: datetime
    content_check: ContentCheck = ContentCheck.NOT_APPLICABLE


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

    @property
    def reverted(self) -> list[str]:
        """
        Aliases revertidos de curated para in_curation nesta varredura.

        :return: aliases com `ContentCheck.REVERTED`, na ordem do lote.
        :rtype: list[str]
        """
        return [r.alias for r in self.ok if r.content_check is ContentCheck.REVERTED]


def _verificar_conteudo(
    folder: Folder, caminho: Path, inspector: GitContentInspector
) -> tuple[ContentCheck, str | None]:
    """
    Decide o efeito da verificação de conteúdo (só consulta o git para pasta curada).

    :param folder: pasta registrada (estado antes da varredura).
    :type folder: Folder
    :param caminho: caminho real já resolvido.
    :type caminho: Path
    :param inspector: porta de inspeção do conteúdo versionado.
    :type inspector: GitContentInspector
    :return: resultado da verificação e o hash a gravar como baseline (ou None).
    :rtype: tuple[ContentCheck, str | None]
    :raises ContentInspectionError: falha do git, com o alias preenchido (FR-009).
    """
    if folder.status is not CurationStatus.CURATED:
        return ContentCheck.NOT_APPLICABLE, None
    alias = folder.alias.value
    try:
        head = inspector.head_commit(caminho)
        if head is None:
            return ContentCheck.NOT_GIT, None
        if folder.last_curated_commit is None:
            # legado curado antes da feature 004: grava o HEAD como referência (FR-014)
            return ContentCheck.BASELINE_RECORDED, head
        if inspector.changed_since(caminho, folder.last_curated_commit):
            return ContentCheck.REVERTED, None
    except ContentInspectionError as error:
        raise ContentInspectionError(alias, error.reason) from error
    return ContentCheck.UNCHANGED, None


def _aplicar_varredura(
    registry: FolderRegistry,
    folder: Folder,
    caminho: Path,
    inspector: GitContentInspector,
) -> tuple[FolderRegistry, ScanResult]:
    """
    Verifica o conteúdo e aplica o efeito da varredura ao registro em memória.

    A persistência fica com o chamador. Se a verificação falhar, o registro não é alterado
    (status, hash e last_scanned intactos).
    """
    alias = folder.alias.value
    content_check, baseline = _verificar_conteudo(folder, caminho, inspector)
    last_scanned = datetime.now(UTC)
    if folder.status is CurationStatus.NOT_SCANNED:
        novo_status: CurationStatus | None = CurationStatus.SCANNED
    elif content_check is ContentCheck.REVERTED:
        novo_status = CurationStatus.IN_CURATION
    else:
        novo_status = None
    updated_registry = registry.update(
        alias, status=novo_status, last_scanned=last_scanned, last_curated_commit=baseline
    )
    if content_check is not ContentCheck.NOT_APPLICABLE:
        log_event(
            logger,
            event="content_check",
            alias=alias,
            outcome=content_check.value,
            error_type=None,
        )
    return updated_registry, ScanResult(
        alias=alias,
        status=updated_registry.get(alias).status,
        last_scanned=last_scanned,
        content_check=content_check,
    )


def scan_folder(
    repository: FolderRegistryRepository,
    locator: FolderLocator,
    alias: str,
    *,
    inspector: GitContentInspector,
) -> ScanResult:
    """
    Varre uma única pasta registrada: confirma que o caminho resolve e atualiza o registro.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param locator: porta que confere o caminho registrado no disco.
    :type locator: FolderLocator
    :param alias: alias a varrer.
    :type alias: str
    :param inspector: porta de inspeção do conteúdo versionado (feature 004).
    :type inspector: GitContentInspector
    :return: resultado da varredura (status resultante, timestamp e verificação de conteúdo).
    :rtype: ScanResult
    :raises FolderNotFoundError: alias não registrado (ambiente não é consultado).
    :raises FolderPathInvalidError: caminho relativo, com `..`, inexistente ou não é diretório.
    :raises FolderPathUnreadableError: sem permissão de leitura.
    :raises ContentInspectionError: falha do git em pasta curada; nada é persistido.
    """
    # garante que o alias existe antes de consultar o disco
    registry = repository.load()
    folder = registry.get(alias)
    try:
        caminho = locator.check(alias, Path(folder.path))
        updated_registry, resultado = _aplicar_varredura(registry, folder, caminho, inspector)
        repository.save(updated_registry)
    except Exception as error:
        log_event(
            logger,
            event="scan_folder",
            alias=alias,
            outcome="falha",
            error_type=type(error).__name__,
        )
        raise
    log_event(logger, event="scan_folder", alias=alias, outcome="ok", error_type=None)
    return resultado


def scan_all_folders(
    repository: FolderRegistryRepository,
    locator: FolderLocator,
    *,
    inspector: GitContentInspector,
) -> ScanBatchReport:
    """
    Varre todos os aliases registrados; falha de um não afeta os demais.

    Também detecta, entre os aliases resolvidos com sucesso, grupos cujo caminho real é
    idêntico (mesmo diretório registrado sob dois ou mais aliases).

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param locator: porta que confere o caminho registrado no disco.
    :type locator: FolderLocator
    :param inspector: porta de inspeção do conteúdo versionado (feature 004).
    :type inspector: GitContentInspector
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
            caminho = locator.check(alias, Path(folder.path))
            registry, resultado = _aplicar_varredura(registry, folder, caminho, inspector)
        except Exception as error:  # noqa: BLE001 - agrega falha por item, não interrompe o lote
            failures.append(
                ItemFailure(alias=alias, error_type=type(error).__name__, message=str(error))
            )
            continue
        caminhos_por_alias[alias] = caminho
        ok.append(resultado)

    if ok:
        # uma única escrita ao fim do lote: regravar por pasta tornava o lote O(n²)
        repository.save(registry)

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
