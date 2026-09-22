# -*- coding: utf-8 -*-
"""
NOME: test_validate_registry.py
TITULO: Testes de falha — caso de uso validate_registry (fakes)
DATA: 22/09/2026 10:30
MODIFICADO: 22/09/2026 10:10
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.validate_registry
HISTÓRICO:
    - 22/09/2026 10:30: criação (T051)
STATUS: DEV
"""

from collections.abc import Mapping

import pytest

from praxisforge.application.ports import ContractValidator, FolderRegistryRepository
from praxisforge.application.validate_registry import validate_registry
from praxisforge.domain.errors import (
    ContractValidationError,
    RegistryFileNotFoundError,
    UnsupportedSchemaVersionError,
    Violation,
)
from praxisforge.domain.folder_registry import FolderRegistry


class _FakeRepository(FolderRegistryRepository):
    def __init__(self, raw: Mapping[str, object], exists: bool = True) -> None:
        self._raw = raw
        self._exists = exists

    def load(self) -> FolderRegistry:  # pragma: no cover - não usado por validate_registry
        raise NotImplementedError

    def load_raw(self) -> Mapping[str, object]:
        if not self._exists:
            raise RegistryFileNotFoundError
        return self._raw

    def save(self, registry: FolderRegistry) -> None:  # pragma: no cover
        raise NotImplementedError

    def exists(self) -> bool:
        return self._exists


class _FakeValidator(ContractValidator):
    def __init__(self, invalid_folders: set[str] | None = None) -> None:
        self._invalid = invalid_folders or set()

    def validate(self, document: Mapping[str, object], schema_name: str) -> None:
        version = document.get("schema_version")
        if version != "1":
            raise UnsupportedSchemaVersionError(
                found=version if isinstance(version, str) else None, supported=("1",)
            )
        # simula validação por item quando o documento é o wrapper {alias: entry}
        folders = document.get("folders")
        if isinstance(folders, dict):
            for alias in folders:
                if alias in self._invalid:
                    raise ContractValidationError([Violation(field="license", reason="inválida")])


def _valid_folder() -> dict[str, object]:
    return {
        "description": "d",
        "content_type": "docs",
        "license": "MIT",
        "last_scanned": None,
        "status": "not_scanned",
    }


def test_lote_com_100_pastas_1_invalida_processa_as_99(tmp_path: object) -> None:
    """100 pastas com 1 inválida ⇒ 99 ok + 1 falha, sem levantar (SC-004)."""
    folders = {f"pasta{i}": _valid_folder() for i in range(100)}
    raw = {"schema_version": "1", "folders": folders}
    repo = _FakeRepository(raw)
    validator = _FakeValidator(invalid_folders={"pasta0"})
    report = validate_registry(repo, validator)
    assert len(report.ok) == 99
    assert len(report.failures) == 1
    assert report.failures[0].alias == "pasta0"


def test_versao_nao_suportada_do_registro_inteiro_levanta() -> None:
    """schema_version não suportada no documento inteiro levanta (não é falha por item)."""
    raw = {"schema_version": "2", "folders": {}}
    repo = _FakeRepository(raw)
    validator = _FakeValidator()
    with pytest.raises(UnsupportedSchemaVersionError):
        validate_registry(repo, validator)


def test_registro_ausente_levanta() -> None:
    """Registro ausente levanta RegistryFileNotFoundError."""
    repo = _FakeRepository({}, exists=False)
    validator = _FakeValidator()
    with pytest.raises(RegistryFileNotFoundError):
        validate_registry(repo, validator)


def test_registro_vazio_eh_ok() -> None:
    """Registro com folders: {} é válido (0 ok, 0 falhas)."""
    raw = {"schema_version": "1", "folders": {}}
    repo = _FakeRepository(raw)
    validator = _FakeValidator()
    report = validate_registry(repo, validator)
    assert report.ok == []
    assert report.failures == []
