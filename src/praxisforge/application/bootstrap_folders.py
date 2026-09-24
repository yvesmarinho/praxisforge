# -*- coding: utf-8 -*-
"""
NOME: bootstrap_folders.py
TITULO: Caso de uso — gerar o registro inicial de pastas a partir de uma pasta-raiz
DATA: 22/09/2026 18:15
MODIFICADO: 23/09/2026 16:59
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports,
        praxisforge.application.resolve_folder_path
HISTÓRICO:
    - 22/09/2026 18:15: criação (T018) — faz test_bootstrap_folders.py passar
    - 22/09/2026 18:40: existing_at_start / skip de ignore (T024, US2)
    - 23/09/2026 16:59: alias <raiz>__<sub>, idempotência por caminho (T031, feature 005)
STATUS: DEV
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import FolderLocator, FolderRegistryRepository, RootFolderProbe
from praxisforge.application.resolve_folder_path import ItemFailure
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    FolderPathInvalidError,
    FolderPathUnreadableError,
    InvalidAliasError,
    NestedFolderPathError,
    PathAlreadyRegisteredError,
)
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry

logger = logging.getLogger(__name__)

_DESCRICAO_PADRAO = "Pasta descoberta pelo bootstrap; sem README para extrair descrição"
_CONTENT_TYPE_PADRAO = "unclassified"
_NAO_ALFANUMERICO = re.compile(r"[^a-z0-9_]")
_ALIAS_MAX = 63
_SEPARADOR = "__"


@dataclass(frozen=True)
class BootstrapReport:
    """Resultado de uma execução do bootstrap sobre uma pasta-raiz."""

    registered: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    skipped_ignored: list[str] = field(default_factory=list)
    failures: list[ItemFailure] = field(default_factory=list)


def slugificar(nome: str) -> str:
    """
    Normaliza um nome de pasta (regra da feature 003 + prefixo "p" da feature 005).

    :param nome: nome da pasta.
    :type nome: str
    :return: minúsculas, espaço/hífen → "_", demais fora de [a-z0-9_] removidos;
        vazio ou iniciado por dígito recebe o prefixo "p".
    :rtype: str

    :Example:

    >>> slugificar("Meu-Repo")
    'meu_repo'
    >>> slugificar("9-lives")
    'p9_lives'
    """
    slug = nome.lower().replace(" ", "_").replace("-", "_")
    slug = _NAO_ALFANUMERICO.sub("", slug)
    if not slug or slug[0].isdigit():
        slug = f"p{slug}"
    return slug


def _alias_candidato(prefixo: str, sub: str, numero: int) -> str:
    """
    Monta "<prefixo>__<sub>[_N]" truncando só a parte da subpasta para caber em 63.

    :param prefixo: nome normalizado da pasta-raiz.
    :type prefixo: str
    :param sub: nome normalizado da subpasta.
    :type sub: str
    :param numero: 1 para sem sufixo; 2, 3, ... para "_2", "_3", ...
    :type numero: int
    :return: alias com no máximo 63 caracteres.
    :rtype: str

    :Example:

    >>> _alias_candidato("forks", "graphify", 2)
    'forks__graphify_2'
    """
    sufixo = f"_{numero}" if numero > 1 else ""
    espaco = _ALIAS_MAX - len(prefixo) - len(_SEPARADOR) - len(sufixo)
    return f"{prefixo}{_SEPARADOR}{sub[: max(espaco, 1)]}{sufixo}"


def _alias_livre(prefixo: str, sub: str, ocupados: set[str]) -> str:
    """Primeiro alias candidato que não está em `ocupados` (FR-007)."""
    numero = 1
    while True:
        alias = _alias_candidato(prefixo, sub, numero)
        if alias not in ocupados:
            return alias
        numero += 1


def bootstrap_folders(
    repository: FolderRegistryRepository,
    probe: RootFolderProbe,
    root: Path,
    *,
    locator: FolderLocator,
) -> BootstrapReport:
    """
    Varre `root` e registra as subpastas de primeiro nível ainda não registradas.

    O alias é sempre "<raiz>__<subpasta>" (normalizados), com sufixo numérico quando já
    ocupado e truncamento para caber em 63 caracteres (FR-007). A identidade é o caminho
    canônico: subpasta cujo caminho já está no registro é "existente" (ou "ignorada"),
    independentemente do alias (FR-006). A raiz nunca é registrada (FR-017). O bootstrap
    nunca atribui `status: ignore`.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param probe: porta de inspeção da pasta-raiz (listar subpastas, ler README/LICENSE).
    :type probe: RootFolderProbe
    :param root: pasta-raiz a varrer.
    :type root: Path
    :param locator: porta que canoniza o caminho de cada subpasta.
    :type locator: FolderLocator
    :return: relatório com pastas registradas, puladas (existentes/ignoradas) e falhas.
    :rtype: BootstrapReport
    :raises InvalidRootPathError: `root` inexistente, não é diretório, ou sem permissão.
    """
    registry = (
        repository.load() if repository.exists() else FolderRegistry(schema_version="2", folders={})
    )
    prefixo = slugificar(root.resolve().name or root.name)
    subpastas = sorted(probe.list_subfolders(root), key=lambda p: p.name)

    registered: list[str] = []
    skipped_existing: list[str] = []
    skipped_ignored: list[str] = []
    failures: list[ItemFailure] = []

    for subpasta in subpastas:
        try:
            caminho = str(locator.canonicalize(subpasta.name, str(subpasta)))
        except (FolderPathInvalidError, FolderPathUnreadableError) as error:
            failures.append(
                ItemFailure(
                    alias=subpasta.name, error_type=type(error).__name__, message=str(error)
                )
            )
            continue
        existente = registry.find_by_path(caminho)
        if existente is not None:
            if existente.status is CurationStatus.IGNORE:
                skipped_ignored.append(existente.alias.value)
            else:
                skipped_existing.append(existente.alias.value)
            continue
        alias_str = _alias_livre(prefixo, slugificar(subpasta.name), set(registry.folders))
        try:
            alias = Alias(alias_str)
        except InvalidAliasError as error:  # pragma: no cover - prefixo "p" garante o formato
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
            path=caminho,
        )
        try:
            registry = registry.add(folder)
        except (PathAlreadyRegisteredError, NestedFolderPathError) as error:
            failures.append(
                ItemFailure(alias=alias_str, error_type=type(error).__name__, message=str(error))
            )
            continue
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
