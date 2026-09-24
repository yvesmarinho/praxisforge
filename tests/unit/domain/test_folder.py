# -*- coding: utf-8 -*-
"""
NOME: test_folder.py
TITULO: Testes de falha — entidade Folder (invariantes em __post_init__)
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 16:47
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.folder
HISTÓRICO:
    - 22/09/2026 09:45: criação (T008)
    - 22/09/2026 17:32: +caso unknown/ignore (T003, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:04: +last_curated_commit (T004, feature 004)
    - 23/09/2026 16:47: path obrigatório (T004, feature 005)
STATUS: DEV
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    FutureScanDateError,
    InvalidCommitHashError,
    InvalidFolderError,
    InvalidFolderPathError,
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
        "path": "/srv/pastas/github_forks",
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


def test_last_curated_commit_default_eh_none() -> None:
    """Campo opcional: omitido vale None (FR-012)."""
    assert _make().last_curated_commit is None


@pytest.mark.parametrize("status", list(CurationStatus))
def test_last_curated_commit_valido_em_qualquer_status(status: CurationStatus) -> None:
    """A versão gravada é histórico: aceita em qualquer status (FR-010)."""
    last_scanned = None if status is CurationStatus.NOT_SCANNED else _agora()
    folder = _make(
        license="MIT", status=status, last_scanned=last_scanned, last_curated_commit="b" * 64
    )
    assert folder.last_curated_commit == "b" * 64


@pytest.mark.parametrize("valor", ["", "A" * 40, "a" * 39, "a" * 41, "z" * 40, "a" * 40 + "\n"])
def test_last_curated_commit_malformado_levanta_erro(valor: str) -> None:
    """Hash fora do formato SHA-1/SHA-256 minúsculo é rejeitado (FR-011)."""
    with pytest.raises(InvalidCommitHashError):
        _make(last_curated_commit=valor)


def _agora() -> datetime:
    return datetime.now(ZoneInfo("America/Sao_Paulo")) - timedelta(minutes=1)


# --- feature 005: caminho absoluto ----------------------------------------------------


@pytest.mark.parametrize(
    "valor",
    ["", "relativo/pasta", "~/pasta", "/srv/../etc", "/srv/pasta/", "/srv/./pasta", "."],
    ids=["vazio", "relativo", "til", "ponto_ponto", "barra_final", "ponto", "so_ponto"],
)
def test_path_fora_da_forma_canonica_levanta_erro(valor: str) -> None:
    """path precisa ser absoluto e canônico na forma (FR-001, FR-002)."""
    with pytest.raises(InvalidFolderPathError):
        _make(path=valor)


@pytest.mark.parametrize("valor", ["/", "/srv/pastas/meu repo", "/srv/pastas/ação", "/a"])
def test_path_absoluto_valido_eh_aceito(valor: str) -> None:
    """Espaços, acentos e a raiz do sistema são aceitos."""
    assert _make(path=valor).path == valor


def test_path_eh_obrigatorio() -> None:
    """Folder sem path não pode ser construída."""
    fields: dict[str, object] = {
        "alias": Alias("github_forks"),
        "description": "d",
        "content_type": "repository_forks",
        "license": "MIT",
        "last_scanned": None,
        "status": CurationStatus.NOT_SCANNED,
    }
    with pytest.raises(TypeError):
        Folder(**fields)  # type: ignore[arg-type]
