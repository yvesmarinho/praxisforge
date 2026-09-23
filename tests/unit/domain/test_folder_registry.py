# -*- coding: utf-8 -*-
"""
NOME: test_folder_registry.py
TITULO: Testes de falha — agregado FolderRegistry
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 12:04
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.folder_registry
HISTÓRICO:
    - 22/09/2026 09:45: criação (T009)
    - 23/09/2026 12:04: +update(last_curated_commit) (T005, feature 004)
STATUS: DEV
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    AliasAlreadyRegisteredError,
    FolderNotFoundError,
    InvalidCommitHashError,
    UnsupportedSchemaVersionError,
)
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry


def _folder(alias: str = "github_forks", **overrides: object) -> Folder:
    fields: dict[str, object] = {
        "alias": Alias(alias),
        "description": "Forks de repositórios de referência",
        "content_type": "repository_forks",
        "license": "unknown",
        "last_scanned": None,
        "status": CurationStatus.PENDING,
    }
    fields.update(overrides)
    return Folder(**fields)  # type: ignore[arg-type]


def test_add_novo_alias() -> None:
    """add registra um alias novo no agregado."""
    registry = FolderRegistry(schema_version="1", folders={})
    updated = registry.add(_folder())
    assert updated.get("github_forks").alias.value == "github_forks"


def test_add_identico_eh_no_op() -> None:
    """add com os mesmos dados de um alias já registrado é idempotente (no-op)."""
    registry = FolderRegistry(schema_version="1", folders={})
    registry = registry.add(_folder())
    same = registry.add(_folder())
    assert same.get("github_forks") == registry.get("github_forks")


def test_add_com_dados_diferentes_levanta_erro_sem_alterar() -> None:
    """add com dados diferentes para um alias existente levanta erro e não altera o agregado."""
    registry = FolderRegistry(schema_version="1", folders={})
    registry = registry.add(_folder())
    with pytest.raises(AliasAlreadyRegisteredError):
        registry.add(_folder(description="Outra descrição"))
    assert registry.get("github_forks").description == "Forks de repositórios de referência"


def test_get_inexistente_levanta_erro() -> None:
    """get de alias inexistente levanta FolderNotFoundError."""
    registry = FolderRegistry(schema_version="1", folders={})
    with pytest.raises(FolderNotFoundError):
        registry.get("inexistente")


def test_update_atomico_de_status_last_scanned_licenca() -> None:
    """update aplica status, last_scanned e license em conjunto, atomicamente."""
    registry = FolderRegistry(schema_version="1", folders={})
    registry = registry.add(_folder())
    now = datetime(2026, 9, 21, 15, 55, tzinfo=ZoneInfo("America/Sao_Paulo"))
    updated = registry.update(
        "github_forks", status=CurationStatus.SCANNED, last_scanned=now, license="MIT"
    )
    folder = updated.get("github_forks")
    assert folder.status is CurationStatus.SCANNED
    assert folder.last_scanned == now
    assert folder.license == "MIT"


def test_update_com_mudanca_invalida_nao_altera_nada() -> None:
    """Uma mudança que violaria invariantes não altera o agregado (atômico)."""
    registry = FolderRegistry(schema_version="1", folders={})
    registry = registry.add(_folder())
    with pytest.raises(Exception):  # noqa: B017 - qualquer erro semântico do domínio
        registry.update("github_forks", status=CurationStatus.SCANNED)  # licença ainda unknown
    assert registry.get("github_forks").status is CurationStatus.PENDING


def test_update_alias_inexistente_levanta_erro() -> None:
    """update de alias inexistente levanta FolderNotFoundError."""
    registry = FolderRegistry(schema_version="1", folders={})
    with pytest.raises(FolderNotFoundError):
        registry.update("inexistente", status=CurationStatus.SCANNED)


def test_schema_version_diferente_de_1_levanta_erro() -> None:
    """schema_version diferente de '1' levanta UnsupportedSchemaVersionError."""
    with pytest.raises(UnsupportedSchemaVersionError):
        FolderRegistry(schema_version="2", folders={})


def test_list_ordenado_por_alias() -> None:
    """list devolve as pastas ordenadas por alias."""
    registry = FolderRegistry(schema_version="1", folders={})
    registry = registry.add(_folder(alias="zebra"))
    registry = registry.add(_folder(alias="abelha"))
    aliases = [folder.alias.value for folder in registry.list()]
    assert aliases == ["abelha", "zebra"]


def _registry_curado(commit: str | None = "a" * 40) -> FolderRegistry:
    agora = datetime(2026, 9, 22, 10, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    folder = _folder(
        license="MIT",
        status=CurationStatus.CURATED,
        last_scanned=agora,
        last_curated_commit=commit,
    )
    return FolderRegistry(schema_version="1", folders={}).add(folder)


def test_update_grava_last_curated_commit_quando_informado() -> None:
    """update aplica o hash informado."""
    updated = _registry_curado(None).update("github_forks", last_curated_commit="c" * 40)
    assert updated.get("github_forks").last_curated_commit == "c" * 40


def test_update_sem_hash_mantem_valor_atual() -> None:
    """Omitir o hash preserva o valor anterior."""
    updated = _registry_curado().update("github_forks", license="Apache-2.0")
    assert updated.get("github_forks").last_curated_commit == "a" * 40


def test_update_de_status_preserva_hash_como_historico() -> None:
    """Sair de curated sem informar hash mantém a versão gravada (FR-010)."""
    updated = _registry_curado().update("github_forks", status=CurationStatus.IN_CURATION)
    folder = updated.get("github_forks")
    assert folder.status is CurationStatus.IN_CURATION
    assert folder.last_curated_commit == "a" * 40


def test_update_com_hash_invalido_nao_altera_nada() -> None:
    """Atualização atômica: hash inválido não altera o agregado."""
    registry = _registry_curado()
    with pytest.raises(InvalidCommitHashError):
        registry.update(
            "github_forks", status=CurationStatus.IN_CURATION, last_curated_commit="xyz"
        )
    assert registry.get("github_forks").status is CurationStatus.CURATED
    assert registry.get("github_forks").last_curated_commit == "a" * 40
