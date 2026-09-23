# -*- coding: utf-8 -*-
"""
NOME: migrate_registry.py
TITULO: Caso de uso — migrar o registro de pastas do formato v1 para o v2 (caminho absoluto)
DATA: 23/09/2026 17:02
MODIFICADO: 23/09/2026 17:02
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports,
        praxisforge.application.bootstrap_folders (regra de normalização de nomes)
HISTÓRICO:
    - 23/09/2026 17:02: criação (T035, feature 005-caminho-absoluto-registro)
STATUS: DEV
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from praxisforge.application.bootstrap_folders import slugificar
from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import (
    FolderLocator,
    FolderRegistryRepository,
    LegacyPathSource,
    RootFolderProbe,
)
from praxisforge.application.resolve_folder_path import ItemFailure
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    FolderPathInvalidError,
    FolderPathUnreadableError,
    NestedFolderPathError,
    PathAlreadyRegisteredError,
    PraxisForgeError,
    UnsupportedSchemaVersionError,
)
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MigrationReport:
    """Resultado da migração v1 → v2."""

    migrated: list[str] = field(default_factory=list)
    pending: list[ItemFailure] = field(default_factory=list)
    removed_roots: list[str] = field(default_factory=list)
    written: bool = False
    already_current: bool = False


def migrate_registry(
    repository: FolderRegistryRepository,
    legacy: LegacyPathSource,
    locator: FolderLocator,
    *,
    probe: RootFolderProbe,
    root: Path | None,
) -> MigrationReport:
    """
    Converte um registro v1 em v2, obtendo o caminho de cada pasta (FR-010, FR-011, FR-014).

    Ordem de busca do caminho: (1) variável antiga do alias; (2) subpasta de `root` cujo nome
    normalizado é igual ao alias (0 ou >1 candidatos → pendência). Entradas cujo caminho é
    ancestral de outras são removidas (FR-017). Grava o registro v2 **somente** se não houver
    pendência (atômico); registro já em v2 não é alterado (idempotente). Aliases e demais
    campos são preservados (FR-015).

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param legacy: porta das variáveis antigas por alias.
    :type legacy: LegacyPathSource
    :param locator: porta que canoniza e confere caminhos.
    :type locator: FolderLocator
    :param probe: porta que lista as subpastas da raiz.
    :type probe: RootFolderProbe
    :param root: pasta-raiz onde procurar subpastas (opcional).
    :type root: Path | None
    :return: relatório com migradas, pendentes e raízes removidas.
    :rtype: MigrationReport
    :raises RegistryFileNotFoundError: registro ausente.
    :raises UnsupportedSchemaVersionError: versão diferente de "1" e "2".
    :raises InvalidRootPathError: `root` inexistente ou ilegível.
    """
    documento = repository.load_raw()
    versao = documento.get("schema_version")
    if versao == "2":
        _log("já no formato atual")
        return MigrationReport(already_current=True)
    if versao != "1":
        raise UnsupportedSchemaVersionError(
            found=versao if isinstance(versao, str) else None, supported=("1", "2")
        )
    entradas = documento.get("folders") or {}
    if not isinstance(entradas, dict):
        entradas = {}
    subpastas = probe.list_subfolders(root) if root is not None else []
    if root is not None:
        subpastas = [*subpastas, root]  # a própria raiz pode estar registrada (FR-017)

    pending: list[ItemFailure] = []
    caminhos: dict[str, str] = {}
    for alias in sorted(entradas):
        try:
            caminhos[alias] = _localizar(alias, legacy, locator, subpastas)
        except _PendenciaError as pendencia:
            pending.append(pendencia.falha)

    removed_roots = sorted(
        alias
        for alias, caminho in caminhos.items()
        if any(_ancestral(caminho, outro) for chave, outro in caminhos.items() if chave != alias)
    )
    registry = FolderRegistry(schema_version="2", folders={})
    migrated: list[str] = []
    for alias, caminho in caminhos.items():
        if alias in removed_roots:
            continue
        try:
            registry = registry.add(_folder(alias, entradas[alias], caminho))
        except (PathAlreadyRegisteredError, NestedFolderPathError) as error:
            pending.append(ItemFailure(alias, type(error).__name__, str(error)))
            continue
        except (PraxisForgeError, KeyError, TypeError, ValueError) as error:
            pending.append(ItemFailure(alias, type(error).__name__, f"entrada inválida: {error}"))
            continue
        migrated.append(alias)

    pending.sort(key=lambda falha: falha.alias)
    written = not pending
    if written:
        repository.save(registry)
    _log(
        f"{len(migrated)} migradas, {len(pending)} pendentes, {len(removed_roots)} raízes removidas"
    )
    return MigrationReport(
        migrated=migrated, pending=pending, removed_roots=removed_roots, written=written
    )


class _PendenciaError(Exception):
    """Sinaliza, internamente, uma pasta cujo caminho não pôde ser determinado."""

    def __init__(self, falha: ItemFailure) -> None:
        super().__init__(falha.message)
        self.falha = falha


def _localizar(
    alias: str, legacy: LegacyPathSource, locator: FolderLocator, subpastas: list[Path]
) -> str:
    """Obtém o caminho canônico de uma pasta antiga (variável → raiz)."""
    bruto = legacy.lookup(alias)
    if bruto is None:
        candidatos = [sub for sub in subpastas if slugificar(sub.name) == alias]
        if not candidatos:
            raise _PendenciaError(
                ItemFailure(alias, "PathNotFound", "caminho não encontrado (variável nem raiz)")
            )
        if len(candidatos) > 1:
            raise _PendenciaError(
                ItemFailure(alias, "AmbiguousPath", f"caminho ambíguo: {len(candidatos)} subpastas")
            )
        bruto = str(candidatos[0])
    try:
        return str(locator.canonicalize(alias, bruto))
    except (FolderPathInvalidError, FolderPathUnreadableError) as error:
        raise _PendenciaError(ItemFailure(alias, type(error).__name__, str(error))) from error


def _ancestral(caminho: str, outro: str) -> bool:
    """True se `caminho` contém `outro` (comparação por componentes, sem maiúsculas)."""
    pai = [p for p in caminho.casefold().split("/") if p]
    filho = [p for p in outro.casefold().split("/") if p]
    return len(pai) < len(filho) and filho[: len(pai)] == pai


def _folder(alias: str, entrada: Mapping[str, object], caminho: str) -> Folder:
    """Reconstrói a entidade a partir da entrada v1, acrescentando o caminho."""
    last_scanned_raw = entrada.get("last_scanned")
    commit = entrada.get("last_curated_commit")
    return Folder(
        alias=Alias(alias),
        description=str(entrada["description"]),
        content_type=str(entrada["content_type"]),
        license=str(entrada["license"]),
        last_scanned=datetime.fromisoformat(str(last_scanned_raw)) if last_scanned_raw else None,
        status=CurationStatus.from_str(str(entrada["status"])),
        path=caminho,
        last_curated_commit=str(commit) if commit is not None else None,
    )


def _log(outcome: str) -> None:
    log_event(logger, event="migrate_registry", alias="*", outcome=outcome, error_type=None)
