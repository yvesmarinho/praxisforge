# -*- coding: utf-8 -*-
"""
NOME: test_register_folder.py
TITULO: Testes de falha — caso de uso register_folder (repositório fake)
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:56
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.register_folder
HISTÓRICO:
    - 22/09/2026 09:45: criação (T029)
STATUS: DEV
"""

import logging

import pytest

from praxisforge.application.dto import RegisterFolderInput
from praxisforge.application.ports import FolderRegistryRepository
from praxisforge.application.register_folder import register_folder
from praxisforge.domain.errors import AliasAlreadyRegisteredError, RegistryUnavailableError
from praxisforge.domain.folder_registry import FolderRegistry


class _FakeRepository(FolderRegistryRepository):
    def __init__(self, registry: FolderRegistry | None = None, fail: bool = False) -> None:
        self._registry = registry or FolderRegistry(schema_version="1", folders={})
        self._fail = fail
        self.saved: FolderRegistry | None = None

    def load(self) -> FolderRegistry:
        if self._fail:
            raise RegistryUnavailableError("indisponível")
        return self._registry

    def load_raw(self) -> dict[str, object]:  # pragma: no cover - não usado neste teste
        raise NotImplementedError

    def save(self, registry: FolderRegistry) -> None:
        self.saved = registry
        self._registry = registry

    def exists(self) -> bool:
        return True


def _input(**overrides: object) -> RegisterFolderInput:
    fields: dict[str, object] = {
        "alias": "exemplo",
        "description": "Pasta de teste",
        "content_type": "documents",
        "license": "MIT",
        "status": "not_scanned",
    }
    fields.update(overrides)
    return RegisterFolderInput(**fields)  # type: ignore[arg-type]


def test_novo_alias_grava() -> None:
    """Registrar um alias novo grava no repositório."""
    repo = _FakeRepository()
    result = register_folder(repo, _input())
    assert result.outcome == "registrado"
    assert repo.saved is not None
    assert repo.saved.get("exemplo").alias.value == "exemplo"


def test_dados_identicos_resultado_unchanged_sem_gravar() -> None:
    """Registrar o mesmo alias com dados idênticos não grava de novo (unchanged)."""
    repo = _FakeRepository()
    register_folder(repo, _input())
    repo.saved = None  # reseta para detectar nova gravação
    result = register_folder(repo, _input())
    assert result.outcome == "inalterado"
    assert repo.saved is None


def test_dados_diferentes_levanta_erro_e_nada_gravado() -> None:
    """Registrar o mesmo alias com dados diferentes levanta erro e não grava."""
    repo = _FakeRepository()
    register_folder(repo, _input())
    repo.saved = None
    with pytest.raises(AliasAlreadyRegisteredError):
        register_folder(repo, _input(description="Outra descrição"))
    assert repo.saved is None


def test_repositorio_indisponivel_propaga_erro() -> None:
    """RegistryUnavailableError do repositório é propagado."""
    repo = _FakeRepository(fail=True)
    with pytest.raises(RegistryUnavailableError):
        register_folder(repo, _input())


def test_log_estruturado_sem_caminho_absoluto(caplog: pytest.LogCaptureFixture) -> None:
    """O caso de uso emite log estruturado (evento, alias, resultado) sem caminho absoluto."""
    repo = _FakeRepository()
    with caplog.at_level(logging.INFO):
        register_folder(repo, _input())
    assert caplog.records
    for record in caplog.records:
        assert "/home/" not in record.message
