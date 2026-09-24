# -*- coding: utf-8 -*-
"""
NOME: test_query_folders.py
TITULO: Testes de falha — casos de uso list_folders e show_folder (repositório fake)
DATA: 22/09/2026 09:45
MODIFICADO: 24/09/2026 10:56
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.query_folders
HISTÓRICO:
    - 22/09/2026 09:45: criação (T030)
    - 24/09/2026 10:56: política máxima derivada da licença (T022, feature 006)
STATUS: DEV
"""

import logging

import pytest

from praxisforge.application.ports import FolderRegistryRepository
from praxisforge.application.query_folders import folder_policy, list_folders, show_folder
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import FolderNotFoundError
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry
from praxisforge.domain.license_policy import ExtractPolicy


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


def _registry() -> FolderRegistry:
    reg = FolderRegistry(schema_version="2", folders={})
    reg = reg.add(
        Folder(
            alias=Alias("github_forks"),
            description="Forks",
            content_type="repository_forks",
            license="unknown",
            last_scanned=None,
            status=CurationStatus.PENDING,
            path="/srv/pastas/github_forks",
        )
    )
    reg = reg.add(
        Folder(
            alias=Alias("outra"),
            description="Outra pasta",
            content_type="documents",
            license="MIT",
            last_scanned=None,
            status=CurationStatus.SCANNED,
            path="/srv/pastas/outra",
        )
    )
    return reg


def test_list_sem_filtro() -> None:
    """list_folders sem filtro devolve todas as pastas."""
    repo = _FakeRepository(_registry())
    resultado = list_folders(repo, status=None)
    assert {f.alias.value for f in resultado} == {"github_forks", "outra"}


def test_list_com_filtro_de_status() -> None:
    """list_folders com filtro devolve só as pastas com o status pedido."""
    repo = _FakeRepository(_registry())
    resultado = list_folders(repo, status="pending")
    assert [f.alias.value for f in resultado] == ["github_forks"]


def test_show_alias_existente() -> None:
    """show_folder de um alias existente devolve a pasta."""
    repo = _FakeRepository(_registry())
    folder = show_folder(repo, alias="github_forks")
    assert folder.alias.value == "github_forks"


def test_show_alias_inexistente_levanta_erro() -> None:
    """show_folder de um alias inexistente levanta FolderNotFoundError."""
    repo = _FakeRepository(_registry())
    with pytest.raises(FolderNotFoundError):
        show_folder(repo, alias="inexistente")


def test_saida_sem_caminho_absoluto() -> None:
    """Nenhum campo devolvido por list/show contém caminho absoluto."""
    repo = _FakeRepository(_registry())
    for folder in list_folders(repo, status=None):
        assert "/home/" not in folder.description


def test_log_estruturado_list_sem_caminho_absoluto(caplog: pytest.LogCaptureFixture) -> None:
    """list_folders emite log estruturado sem caminho absoluto."""
    repo = _FakeRepository(_registry())
    with caplog.at_level(logging.INFO):
        list_folders(repo, status=None)
    assert caplog.records
    for record in caplog.records:
        assert "/home/" not in record.message


def test_log_estruturado_show_sem_caminho_absoluto(caplog: pytest.LogCaptureFixture) -> None:
    """show_folder emite log estruturado sem caminho absoluto."""
    repo = _FakeRepository(_registry())
    with caplog.at_level(logging.INFO):
        show_folder(repo, alias="github_forks")
    assert caplog.records
    for record in caplog.records:
        assert "/home/" not in record.message


@pytest.mark.parametrize(
    ("licenca", "maxima", "classificada"),
    [
        ("MIT", ExtractPolicy.VERBATIM, True),
        ("unknown", ExtractPolicy.LINK, True),
        ("Elastic-2.0", ExtractPolicy.SUMMARY, True),
        ("MPL-2.0", ExtractPolicy.LINK, False),
    ],
)
def test_folder_policy_deriva_da_licenca(
    licenca: str, maxima: ExtractPolicy, classificada: bool
) -> None:
    """Política máxima derivada da licença da pasta, sem persistir nada (FR-013)."""
    status = CurationStatus.PENDING if licenca == "unknown" else CurationStatus.SCANNED
    folder = Folder(
        alias=Alias("pasta"),
        description="d",
        content_type="documents",
        license=licenca,
        last_scanned=None,
        status=status,
        path="/srv/pastas/pasta",
    )
    politica = folder_policy(folder)
    assert politica.maximum is maxima
    assert politica.classified is classificada
