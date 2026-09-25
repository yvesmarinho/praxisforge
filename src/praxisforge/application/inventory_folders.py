# -*- coding: utf-8 -*-
"""
NOME: inventory_folders.py
TITULO: Casos de uso — inventário de curadoria de uma pasta registrada e de todas (lote)
DATA: 25/09/2026 15:18
MODIFICADO: 25/09/2026 14:56
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports, praxisforge.application.logging_events
HISTÓRICO:
    - 25/09/2026 15:18: criação (T019, T029, T031, feature 010) — faz test_inventory_folders.py
      passar
STATUS: DEV
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import (
    ConventionsSource,
    CurationStore,
    FolderLocator,
    FolderRegistryRepository,
    FolderWalk,
    FolderWalker,
    WalkedFile,
)
from praxisforge.application.resolve_folder_path import ItemFailure
from praxisforge.domain.curation_artifact import (
    Artifact,
    ArtifactKind,
    ExcludedEntry,
    ExclusionReason,
    Manifest,
    Stage,
)
from praxisforge.domain.curation_conventions import Conventions
from praxisforge.domain.curation_state import Situation, reconcile, situation
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.folder import Folder

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True)
class InventoryResult:
    """Resumo do inventário de uma pasta."""

    alias: str
    artifacts: int
    pending: int
    removed: int
    excluded: int
    situation: Situation


@dataclass(frozen=True)
class InventoryReport:
    """Resultado do inventário em lote: pastas ok, falhas por pasta e puladas (`ignore`)."""

    ok: list[InventoryResult]
    failures: list[ItemFailure]
    skipped: list[str] = field(default_factory=list)


def _ancestrais(path: str) -> list[str]:
    partes = path.split("/")[:-1]
    return ["/".join(partes[: i + 1]) for i in range(len(partes))]


def _hash_diretorio(diretorio: str, membros: list[WalkedFile]) -> str:
    linhas = "".join(f"{m.path[len(diretorio) + 1 :]}\0{m.sha256}\n" for m in membros)
    return hashlib.sha256(linhas.encode("utf-8")).hexdigest()


def build_manifest(alias: str, walk: FolderWalk, conventions: Conventions) -> Manifest:
    """
    Classifica a varredura: diretórios de cima para baixo (o mais externo é dono da
    subárvore), depois arquivos; `.md` sem regra → `unknown`; outro texto → `uncurated`.

    :param alias: alias da pasta.
    :type alias: str
    :param walk: arquivos aceitos e exclusões da varredura.
    :type walk: FolderWalk
    :param conventions: convenções de classificação.
    :type conventions: Conventions
    :return: manifesto determinístico.
    :rtype: Manifest
    """
    nomes_por_dir: dict[str, set[str]] = {}
    for arquivo in walk.files:
        partes = arquivo.path.rsplit("/", 1)
        if len(partes) == 2:
            nomes_por_dir.setdefault(partes[0], set()).add(partes[1])
        for ancestral in _ancestrais(arquivo.path):
            nomes_por_dir.setdefault(ancestral, set())

    donos: dict[str, ArtifactKind] = {}
    for diretorio in sorted(nomes_por_dir, key=lambda d: (d.count("/"), d)):
        if any(a in donos for a in _ancestrais(f"{diretorio}/x")):
            continue
        kind = conventions.classify_directory(diretorio, frozenset(nomes_por_dir[diretorio]))
        if kind is not None:
            donos[diretorio] = kind

    membros: dict[str, list[WalkedFile]] = {d: [] for d in donos}
    artefatos: list[Artifact] = []
    excluidos: list[ExcludedEntry] = list(walk.excluded)
    for arquivo in walk.files:
        dono = next((a for a in _ancestrais(arquivo.path) if a in donos), None)
        if dono is not None:
            membros[dono].append(arquivo)
            continue
        kind = conventions.classify_file(arquivo.path)
        if kind is None and arquivo.path.lower().endswith(".md"):
            kind = ArtifactKind.UNKNOWN
        if kind is None:
            excluidos.append(ExcludedEntry(arquivo.path, ExclusionReason.UNCURATED, False))
            continue
        artefatos.append(Artifact(arquivo.path, kind, arquivo.size, arquivo.sha256, 1))

    for diretorio, arquivos in membros.items():
        ordenados = sorted(arquivos, key=lambda m: m.path)
        artefatos.append(
            Artifact(
                path=diretorio,
                kind=donos[diretorio],
                size=sum(m.size for m in ordenados),
                sha256=_hash_diretorio(diretorio, ordenados),
                files=len(ordenados),
            )
        )
    return Manifest(alias, conventions.version, tuple(artefatos), tuple(excluidos))


def _inventariar(
    folder: Folder,
    locator: FolderLocator,
    walker: FolderWalker,
    conventions: Conventions,
    store: CurationStore,
    now: datetime,
) -> InventoryResult:
    alias = folder.alias.value
    caminho = locator.check(alias, Path(folder.path))
    with store.lock(alias):
        anterior = store.load_state(alias)
        manifesto = build_manifest(alias, walker.walk(caminho), conventions)
        estado = reconcile(anterior, manifesto, now)
        store.save(manifesto, estado)
    etapas = [s.stage for s in estado.artifacts.values()]
    return InventoryResult(
        alias=alias,
        artifacts=len(manifesto.artifacts),
        pending=etapas.count(Stage.PENDING),
        removed=etapas.count(Stage.REMOVED),
        excluded=len(manifesto.excluded),
        situation=situation(estado),
    )


def inventory_folder(
    repository: FolderRegistryRepository,
    locator: FolderLocator,
    walker: FolderWalker,
    conventions: ConventionsSource,
    store: CurationStore,
    alias: str,
    *,
    now: datetime | None = None,
) -> InventoryResult:
    """
    Inventaria uma pasta registrada e reconcilia com o estado anterior (FR-001, FR-015).

    :param repository: registro de pastas.
    :param locator: confere o caminho registrado no disco.
    :param walker: varredura somente leitura.
    :param conventions: fonte das convenções de classificação.
    :param store: persistência de manifesto e estado.
    :param alias: alias a inventariar.
    :param now: instante (padrão: agora em America/Sao_Paulo).
    :return: resumo do inventário.
    :rtype: InventoryResult
    :raises FolderNotFoundError: alias não registrado.
    :raises ConventionsMissingError: convenções ausentes.
    :raises CurationLockedError: outra execução no mesmo alias.
    :raises CurationStateCorruptError: estado anterior inválido (não é sobrescrito).
    """
    folder = repository.load().get(alias)
    convencoes = conventions.load()
    try:
        resultado = _inventariar(
            folder, locator, walker, convencoes, store, now or datetime.now(_TZ)
        )
    except Exception as error:
        log_event(logger, "inventory_folder", alias, "falha", type(error).__name__)
        raise
    log_event(logger, "inventory_folder", alias, "ok", None)
    return resultado


def inventory_all(
    repository: FolderRegistryRepository,
    locator: FolderLocator,
    walker: FolderWalker,
    conventions: ConventionsSource,
    store: CurationStore,
    *,
    now: datetime | None = None,
) -> InventoryReport:
    """
    Inventaria todas as pastas, exceto `ignore`; a falha de uma não impede as outras (FR-020).

    :return: relatório com pastas ok, falhas e puladas.
    :rtype: InventoryReport
    :raises ConventionsMissingError: convenções ausentes (nenhuma pasta é tocada).
    """
    registry = repository.load()
    convencoes = conventions.load()
    instante = now or datetime.now(_TZ)
    ok: list[InventoryResult] = []
    failures: list[ItemFailure] = []
    skipped: list[str] = []
    for folder in registry.list():
        alias = folder.alias.value
        if folder.status is CurationStatus.IGNORE:
            skipped.append(alias)
            continue
        try:
            ok.append(_inventariar(folder, locator, walker, convencoes, store, instante))
        except Exception as error:  # noqa: BLE001 - agrega falha por item, não interrompe o lote
            log_event(logger, "inventory_folder", alias, "falha", type(error).__name__)
            failures.append(
                ItemFailure(alias=alias, error_type=type(error).__name__, message=str(error))
            )
            continue
        log_event(logger, "inventory_folder", alias, "ok", None)
    return InventoryReport(ok=ok, failures=failures, skipped=skipped)
