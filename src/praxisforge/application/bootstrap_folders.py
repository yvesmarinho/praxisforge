# -*- coding: utf-8 -*-
"""
NOME: bootstrap_folders.py
TITULO: Caso de uso — gerar o registro inicial de pastas a partir de uma pasta-raiz
DATA: 22/09/2026 18:15
MODIFICADO: 22/09/2026 16:47
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports,
        praxisforge.application.resolve_folder_path
HISTÓRICO:
    - 22/09/2026 18:15: criação (T018) — faz test_bootstrap_folders.py passar
    - 22/09/2026 18:40: existing_at_start / skip de ignore (T024, US2)
STATUS: DEV
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import FolderRegistryRepository, RootFolderProbe
from praxisforge.application.resolve_folder_path import ItemFailure
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import AliasAlreadyRegisteredError, InvalidAliasError
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry

logger = logging.getLogger(__name__)

_DESCRICAO_PADRAO = "Pasta descoberta pelo bootstrap; sem README para extrair descrição"
_CONTENT_TYPE_PADRAO = "unclassified"
_NAO_ALFANUMERICO = re.compile(r"[^a-z0-9_]")


@dataclass(frozen=True)
class BootstrapReport:
    """Resultado de uma execução do bootstrap sobre uma pasta-raiz."""

    registered: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    skipped_ignored: list[str] = field(default_factory=list)
    failures: list[ItemFailure] = field(default_factory=list)


def _slugificar(nome: str) -> str:
    """Transforma o nome de uma subpasta em candidato a alias (research.md, Decisão 4)."""
    slug = nome.lower().replace(" ", "_").replace("-", "_")
    return _NAO_ALFANUMERICO.sub("", slug)


def bootstrap_folders(
    repository: FolderRegistryRepository, probe: RootFolderProbe, root: Path
) -> BootstrapReport:
    """
    Varre `root` e registra como novas as subpastas de primeiro nível ainda não conhecidas.

    Pastas cujo alias já existia no registro no início da execução não são alteradas
    (FR-004); dentre essas, as marcadas `status: ignore` são contadas separadamente
    (FR-005). O bootstrap nunca atribui `status: ignore` a nenhuma pasta (FR-012).

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param probe: porta de inspeção da pasta-raiz (listar subpastas, ler README/LICENSE).
    :type probe: RootFolderProbe
    :param root: pasta-raiz a varrer.
    :type root: Path
    :return: relatório com pastas registradas, puladas (existentes/ignoradas) e falhas.
    :rtype: BootstrapReport
    :raises InvalidRootPathError: `root` inexistente, não é diretório, ou sem permissão.
    """
    registry = (
        repository.load()
        if repository.exists()
        else FolderRegistry(schema_version="1", folders={})
    )
    existing_at_start = set(registry.folders)
    subpastas = sorted(probe.list_subfolders(root), key=lambda p: p.name)

    registered: list[str] = []
    skipped_existing: list[str] = []
    skipped_ignored: list[str] = []
    failures: list[ItemFailure] = []
    novos_nesta_execucao: set[str] = set()

    for subpasta in subpastas:
        alias_str = _slugificar(subpasta.name)
        if alias_str in existing_at_start:
            existente = registry.get(alias_str)
            if existente.status is CurationStatus.IGNORE:
                skipped_ignored.append(alias_str)
            else:
                skipped_existing.append(alias_str)
            continue
        if alias_str in novos_nesta_execucao:
            # Colisão entre duas subpastas novas nesta mesma execução (mesmo alias slugificado).
            # Reportada explicitamente aqui — não delegada a registry.add() — porque duas
            # subpastas com metadados computados idênticos (ex.: ambas sem README/LICENSE)
            # produziriam um Folder idêntico, e add() trataria isso como no-op idempotente em
            # vez de colisão real (research.md, Decisão 6).
            failures.append(
                ItemFailure(
                    alias=subpasta.name,
                    error_type=AliasAlreadyRegisteredError.__name__,
                    message=str(AliasAlreadyRegisteredError(alias_str)),
                )
            )
            continue
        try:
            alias = Alias(alias_str)
        except InvalidAliasError as error:
            failures.append(
                ItemFailure(
                    alias=subpasta.name, error_type=type(error).__name__, message=str(error)
                )
            )
            continue
        licenca = probe.detect_license(subpasta) or "unknown"
        descricao = probe.read_description(subpasta) or _DESCRICAO_PADRAO
        status = CurationStatus.PENDING if licenca == "unknown" else CurationStatus.NOT_SCANNED
        folder = Folder(
            alias=alias,
            description=descricao,
            content_type=_CONTENT_TYPE_PADRAO,
            license=licenca,
            last_scanned=None,
            status=status,
        )
        registry = registry.add(folder)
        novos_nesta_execucao.add(alias_str)
        registered.append(alias_str)

    if registered:
        repository.save(registry)

    log_event(
        logger,
        event="bootstrap_folders",
        alias="*",
        outcome=(
            f"{len(registered)} registradas, {len(skipped_existing)} já existentes, "
            f"{len(skipped_ignored)} ignoradas, {len(failures)} com falha"
        ),
        error_type=None,
    )
    return BootstrapReport(
        registered=registered,
        skipped_existing=skipped_existing,
        skipped_ignored=skipped_ignored,
        failures=failures,
    )
