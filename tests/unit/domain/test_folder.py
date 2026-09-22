# -*- coding: utf-8 -*-
"""
NOME: test_folder.py
TITULO: Testes de falha — entidade Folder (invariantes em __post_init__)
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 16:37
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.folder
HISTÓRICO:
    - 22/09/2026 09:45: criação (T008)
    - 22/09/2026 17:32: +caso unknown/ignore (T003, feature 003-bootstrap-registro-pastas)
STATUS: DEV
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    FutureScanDateError,
    InvalidFolderError,
    UnknownLicenseRequiresPendingError,
)
from praxisforge.domain.folder import Folder


def _make(**overrides: object) -> Folder:
    fields: dict[str, object] = {
        "alias": Alias("github_forks"),
        "description": "Forks de repositórios de referência",
        "content_type": "repository_forks",
        "license": "unknown",
        "last_scanned": None,
        "status": CurationStatus.PENDING,
    }
    fields.update(overrides)
    return Folder(**fields)  # type: ignore[arg-type]


def test_descricao_vazia_levanta_erro() -> None:
    """Descrição vazia é inválida."""
    with pytest.raises(InvalidFolderError):
        _make(description="")


def test_descricao_muito_longa_levanta_erro() -> None:
    """Descrição com 501 caracteres excede o limite de 500."""
    with pytest.raises(InvalidFolderError):
        _make(description="a" * 501)


def test_content_type_fora_do_slug_levanta_erro() -> None:
    """content_type fora do formato slug é inválido."""
    with pytest.raises(InvalidFolderError):
        _make(content_type="Repository Forks")


def test_licenca_vazia_levanta_erro() -> None:
    """Licença vazia é inválida."""
    with pytest.raises(InvalidFolderError):
        _make(license="")


def test_licenca_unknown_com_status_diferente_de_pending_levanta_erro() -> None:
    """Licença 'unknown' com status 'not_scanned' continua inválido (regressão)."""
    with pytest.raises(UnknownLicenseRequiresPendingError):
        _make(license="unknown", status=CurationStatus.NOT_SCANNED)


def test_licenca_unknown_com_status_scanned_levanta_erro() -> None:
    """Regressão: licença 'unknown' com status 'scanned' continua inválido (feature 003)."""
    with pytest.raises(UnknownLicenseRequiresPendingError):
        _make(license="unknown", status=CurationStatus.SCANNED)


def test_licenca_unknown_com_status_ignore_eh_aceito() -> None:
    """Licença 'unknown' com status 'ignore' é aceito (invariante relaxada, FR-011)."""
    folder = _make(license="unknown", status=CurationStatus.IGNORE)
    assert folder.status is CurationStatus.IGNORE
    assert folder.license == "unknown"


def test_not_scanned_com_last_scanned_preenchido_levanta_erro() -> None:
    """Status 'not_scanned' exige last_scanned nulo."""
    now = datetime(2026, 9, 21, tzinfo=ZoneInfo("America/Sao_Paulo"))
    with pytest.raises(InvalidFolderError):
        _make(
            license="MIT",
            status=CurationStatus.NOT_SCANNED,
            last_scanned=now,
        )


def test_last_scanned_futuro_levanta_erro() -> None:
    """last_scanned no futuro é inválido."""
    futuro = datetime.now(ZoneInfo("America/Sao_Paulo")) + timedelta(days=1)
    with pytest.raises(FutureScanDateError):
        _make(license="MIT", status=CurationStatus.SCANNED, last_scanned=futuro)


def test_last_scanned_sem_timezone_levanta_erro() -> None:
    """last_scanned sem timezone (naive) é inválido."""
    naive = datetime(2026, 9, 21, 15, 55, 0)  # noqa: DTZ001
    with pytest.raises(InvalidFolderError):
        _make(license="MIT", status=CurationStatus.SCANNED, last_scanned=naive)


def test_caso_feliz_valido() -> None:
    """Um Folder válido é construído sem levantar exceção (acompanha os testes de falha acima)."""
    folder = _make()
    assert folder.alias.value == "github_forks"
    assert folder.status is CurationStatus.PENDING
