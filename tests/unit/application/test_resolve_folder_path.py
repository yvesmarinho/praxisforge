# -*- coding: utf-8 -*-
"""
NOME: test_resolve_folder_path.py
TITULO: Testes de falha — casos de uso resolve_folder_path e resolve_all_folder_paths
DATA: 22/09/2026 10:10
MODIFICADO: 22/09/2026 10:03
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.resolve_folder_path
HISTÓRICO:
    - 22/09/2026 10:10: criação (T042)
STATUS: DEV
"""

import logging
from pathlib import Path

import pytest

from praxisforge.application.ports import FolderRegistryRepository, PathResolver
from praxisforge.application.resolve_folder_path import (
    resolve_all_folder_paths,
    resolve_folder_path,
)
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    FolderNotFoundError,
    FolderPathNotConfiguredError,
)
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry


class _FakeRepository(FolderRegistryRepository):
    def __init__(self, registry: FolderRegistry) -> None:
        self._registry = registry

    def load(self) -> FolderRegistry:
        return self._registry

    def load_raw(self) -> dict[str, object]:  # pragma: no cover
        raise NotImplementedError

    def save(self, registry: FolderRegistry) -> None:  # pragma: no cover
        raise NotImplementedError

    def exists(self) -> bool:
        return True


class _FakeResolver(PathResolver):
    def __init__(self, paths: dict[str, Path], fail: dict[str, Exception] | None = None) -> None:
        self._paths = paths
        self._fail = fail or {}

    def resolve(self, alias: str) -> Path:
        if alias in self._fail:
            raise self._fail[alias]
        return self._paths[alias]


def _registry(*aliases: str) -> FolderRegistry:
    reg = FolderRegistry(schema_version="1", folders={})
    for alias in aliases:
        reg = reg.add(
            Folder(
                alias=Alias(alias),
                description="d",
                content_type="documents",
                license="MIT",
                last_scanned=None,
                status=CurationStatus.NOT_SCANNED,
            )
        )
    return reg


def test_alias_nao_registrado_levanta_folder_not_found_sem_consultar_ambiente() -> None:
    """Alias não registrado levanta FolderNotFoundError sem consultar o resolvedor."""
    repo = _FakeRepository(_registry())
    resolver = _FakeResolver({})
    with pytest.raises(FolderNotFoundError):
        resolve_folder_path(repo, resolver, alias="inexistente")


def test_resolve_all_devolve_batch_report_falha_de_um_nao_afeta_outros(tmp_path: Path) -> None:
    """resolve_all devolve BatchReport; falha de um alias não afeta os demais."""
    repo = _FakeRepository(_registry("aa", "bb"))
    resolver = _FakeResolver(
        {"aa": tmp_path},
        fail={"bb": FolderPathNotConfiguredError("bb")},
    )
    report = resolve_all_folder_paths(repo, resolver)
    assert report.ok == {"aa": tmp_path}
    assert len(report.failures) == 1
    assert report.failures[0].alias == "bb"


def test_log_estruturado_sem_caminho(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    """resolve_folder_path emite log estruturado sem caminho absoluto."""
    repo = _FakeRepository(_registry("aa"))
    resolver = _FakeResolver({"aa": tmp_path})
    with caplog.at_level(logging.INFO):
        resolve_folder_path(repo, resolver, alias="aa")
    assert caplog.records
    for record in caplog.records:
        assert str(tmp_path) not in record.message
