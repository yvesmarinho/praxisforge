# -*- coding: utf-8 -*-
"""
NOME: test_update_folder.py
TITULO: Testes de falha — caso de uso update_folder (repositório fake)
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 16:43
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.update_folder
HISTÓRICO:
    - 22/09/2026 09:45: criação (T031)
    - 22/09/2026 19:00: +caso status ignore (T027, feature 003-bootstrap-registro-pastas)
STATUS: DEV
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from praxisforge.application.dto import UpdateFolderInput
from praxisforge.application.ports import FolderRegistryRepository
from praxisforge.application.update_folder import update_folder
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import FolderNotFoundError, UnknownLicenseRequiresPendingError
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry


class _FakeRepository(FolderRegistryRepository):
    def __init__(self, registry: FolderRegistry) -> None:
        self._registry = registry
        self.save_count = 0

    def load(self) -> FolderRegistry:
        return self._registry

    def load_raw(self) -> dict[str, object]:  # pragma: no cover
        raise NotImplementedError

    def save(self, registry: FolderRegistry) -> None:
        self._registry = registry
        self.save_count += 1

    def exists(self) -> bool:
        return True


def _registry() -> FolderRegistry:
    reg = FolderRegistry(schema_version="1", folders={})
    return reg.add(
        Folder(
            alias=Alias("github_forks"),
            description="Forks",
            content_type="repository_forks",
            license="unknown",
            last_scanned=None,
            status=CurationStatus.PENDING,
        )
    )


def test_atualiza_so_os_campos_informados() -> None:
    """update_folder altera só os campos informados, mantendo os demais."""
    repo = _FakeRepository(_registry())
    update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT"))
    folder = repo.load().get("github_forks")
    assert folder.license == "MIT"
    assert folder.description == "Forks"


def test_atomico_grava_uma_vez() -> None:
    """update_folder grava atomicamente (uma única escrita por chamada)."""
    repo = _FakeRepository(_registry())
    update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT"))
    assert repo.save_count == 1


def test_last_scanned_futuro_recusado() -> None:
    """last_scanned no futuro é recusado."""
    repo = _FakeRepository(_registry())
    futuro = (datetime.now(ZoneInfo("America/Sao_Paulo")) + timedelta(days=1)).isoformat()
    with pytest.raises(Exception):  # noqa: B017 - FutureScanDateError ou ValidationError do DTO
        update_folder(
            repo,
            UpdateFolderInput(alias="github_forks", license="MIT", last_scanned=futuro),
        )


def test_licenca_unknown_mantida_com_status_diferente_de_pending_recusada() -> None:
    """Tentar mudar status sem resolver a licença unknown é recusado."""
    repo = _FakeRepository(_registry())
    with pytest.raises(UnknownLicenseRequiresPendingError):
        update_folder(repo, UpdateFolderInput(alias="github_forks", status="scanned"))


def test_licenca_valida_e_novo_status_na_mesma_operacao_aceita() -> None:
    """Licença válida + novo status na mesma chamada é aceito (spec cenário 5)."""
    repo = _FakeRepository(_registry())
    update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT", status="scanned"))
    folder = repo.load().get("github_forks")
    assert folder.license == "MIT"
    assert folder.status is CurationStatus.SCANNED


def test_alias_inexistente_levanta_erro() -> None:
    """update_folder de alias inexistente levanta FolderNotFoundError."""
    repo = _FakeRepository(_registry())
    with pytest.raises(FolderNotFoundError):
        update_folder(repo, UpdateFolderInput(alias="inexistente", license="MIT"))


def test_repetir_mesmo_update_nao_altera_bytes_conceitualmente() -> None:
    """Repetir o mesmo update produz o mesmo estado final (idempotente em efeito)."""
    repo = _FakeRepository(_registry())
    update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT", status="scanned"))
    estado_1 = repo.load().get("github_forks")
    update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT", status="scanned"))
    estado_2 = repo.load().get("github_forks")
    assert estado_1 == estado_2


def test_log_estruturado_sem_caminho_absoluto(caplog: pytest.LogCaptureFixture) -> None:
    """update_folder emite log estruturado (evento, alias, resultado) sem caminho absoluto."""
    repo = _FakeRepository(_registry())
    with caplog.at_level(logging.INFO):
        update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT"))
    assert caplog.records
    for record in caplog.records:
        assert "/home/" not in record.message


def test_status_ignore_aceito_com_licenca_unknown() -> None:
    """update_folder aceita status='ignore' mesmo com licença unknown (FR-011)."""
    repo = _FakeRepository(_registry())
    update_folder(repo, UpdateFolderInput(alias="github_forks", status="ignore"))
    folder = repo.load().get("github_forks")
    assert folder.status is CurationStatus.IGNORE
    assert folder.license == "unknown"
