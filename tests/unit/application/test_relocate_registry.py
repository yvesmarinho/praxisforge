# -*- coding: utf-8 -*-
"""
NOME: test_relocate_registry.py
TITULO: Testes de falha — caso de uso relocate_registry (fakes)
DATA: 24/09/2026 14:34
MODIFICADO: 24/09/2026 14:34
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.relocate_registry
HISTÓRICO:
    - 24/09/2026 14:34: criação (T024, US3, feature 007)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.application.ports import FolderRegistryRepository, RegistryFileMover
from praxisforge.application.relocate_registry import relocate_registry
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    ContractValidationError,
    NothingToRelocateError,
    RegistryAlreadyExistsError,
    RegistryFileNotFoundError,
    RegistryMigrationRequiredError,
    RegistryRelocationError,
    Violation,
)
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry

ORIGEM = Path("/repo/src/data/folders.yaml")
DESTINO = Path("/cfg/praxisforge/folders.yaml")


def _registro(n: int) -> FolderRegistry:
    registro = FolderRegistry(schema_version="2", folders={})
    for i in range(n):
        registro = registro.add(
            Folder(
                alias=Alias(f"pasta_{i}"),
                description="d",
                content_type="documents",
                license="MIT",
                last_scanned=None,
                status=CurationStatus.NOT_SCANNED,
                path=f"/srv/pastas/p{i}",
            )
        )
    return registro


class _Repo(FolderRegistryRepository):
    def __init__(
        self, registro: FolderRegistry | None = None, erro: Exception | None = None
    ) -> None:
        self._registro = registro
        self._erro = erro

    def load(self) -> FolderRegistry:
        if self._erro is not None:
            raise self._erro
        if self._registro is None:
            raise RegistryFileNotFoundError(str(ORIGEM))
        return self._registro

    def load_raw(self) -> dict[str, object]:  # pragma: no cover
        raise NotImplementedError

    def save(self, registry: FolderRegistry) -> None:  # pragma: no cover
        raise AssertionError("relocate não grava pelo repositório")

    def exists(self) -> bool:
        return self._registro is not None


class _Mover(RegistryFileMover):
    def __init__(self, erro: Exception | None = None) -> None:
        self.chamadas: list[tuple[Path, Path]] = []
        self._erro = erro

    def move(self, source: Path, target: Path) -> None:
        self.chamadas.append((source, target))
        if self._erro is not None:
            raise self._erro


def _relocar(origem: _Repo, destino: _Repo, mover: _Mover) -> object:
    return relocate_registry(origem, destino, mover, source_path=ORIGEM, target_path=DESTINO)


def test_destino_existente_recusa_sem_mover() -> None:
    """Já existe registro no destino → RegistryAlreadyExistsError, nada muda."""
    mover = _Mover()
    with pytest.raises(RegistryAlreadyExistsError) as info:
        _relocar(_Repo(_registro(2)), _Repo(_registro(1)), mover)
    assert info.value.location == str(DESTINO)
    assert mover.chamadas == []


@pytest.mark.parametrize(
    "erro",
    [
        RegistryFileNotFoundError(str(ORIGEM)),
        RegistryMigrationRequiredError(),
        ContractValidationError([Violation(field="folders", reason="inválido")]),
    ],
)
def test_origem_ausente_v1_ou_invalida_recusa_sem_mover(erro: Exception) -> None:
    """Falhas de leitura/validação da origem propagam e o mover não é chamado (FR-010)."""
    mover = _Mover()
    with pytest.raises(type(erro)):
        _relocar(_Repo(erro=erro), _Repo(), mover)
    assert mover.chamadas == []


def test_origem_ausente_sem_erro_explicito() -> None:
    """Origem inexistente → RegistryFileNotFoundError citando a origem."""
    with pytest.raises(RegistryFileNotFoundError) as info:
        _relocar(_Repo(), _Repo(), _Mover())
    assert info.value.location == str(ORIGEM)


def test_origem_sem_pastas_recusa() -> None:
    """Registro de origem vazio → NothingToRelocateError, sem mover."""
    mover = _Mover()
    with pytest.raises(NothingToRelocateError):
        _relocar(_Repo(_registro(0)), _Repo(), mover)
    assert mover.chamadas == []


def test_caso_valido_move_uma_vez_e_conta_pastas() -> None:
    """Origem válida + destino livre → move e informa a quantidade de pastas."""
    mover = _Mover()
    resultado = _relocar(_Repo(_registro(3)), _Repo(), mover)
    assert mover.chamadas == [(ORIGEM, DESTINO)]
    assert resultado.target == DESTINO  # type: ignore[attr-defined]
    assert resultado.folders == 3  # type: ignore[attr-defined]


def test_falha_do_mover_propaga() -> None:
    """Falha de I/O do adapter chega como RegistryRelocationError (FR-013)."""
    with pytest.raises(RegistryRelocationError):
        _relocar(_Repo(_registro(1)), _Repo(), _Mover(RegistryRelocationError("disco cheio")))
