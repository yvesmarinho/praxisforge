# -*- coding: utf-8 -*-
"""
NOME: test_register_folder.py
TITULO: Testes de falha — caso de uso register_folder (repositório fake)
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 16:52
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.register_folder
HISTÓRICO:
    - 22/09/2026 09:45: criação (T029)
    - 23/09/2026 16:52: path obrigatório + FolderLocator (T019, feature 005)
STATUS: DEV
"""

import logging
from pathlib import Path

import pytest

from praxisforge.application.dto import RegisterFolderInput
from praxisforge.application.ports import FolderLocator, FolderRegistryRepository
from praxisforge.application.register_folder import RegisterFolderResult
from praxisforge.application.register_folder import register_folder as _register_folder
from praxisforge.domain.errors import AliasAlreadyRegisteredError, RegistryUnavailableError
from praxisforge.domain.folder_registry import FolderRegistry


class _FakeRepository(FolderRegistryRepository):
    def __init__(self, registry: FolderRegistry | None = None, fail: bool = False) -> None:
        self._registry = registry or FolderRegistry(schema_version="2", folders={})
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


class _FakeLocator(FolderLocator):
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    def canonicalize(self, alias: str, raw: str) -> Path:
        if self._error is not None:
            raise self._error
        return Path(raw.rstrip("/") or "/")

    def check(self, alias: str, path: Path) -> Path:  # pragma: no cover - não usado aqui
        return path


def register_folder(
    repo: FolderRegistryRepository, data: RegisterFolderInput
) -> RegisterFolderResult:
    """Casos anteriores à feature 005: locator aceita qualquer caminho."""
    return _register_folder(repo, data, locator=_FakeLocator())


def _input(**overrides: object) -> RegisterFolderInput:
    fields: dict[str, object] = {
        "alias": "exemplo",
        "description": "Pasta de teste",
        "content_type": "documents",
        "license": "MIT",
        "status": "not_scanned",
        "path": "/srv/pastas/exemplo",
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


# --- feature 005: caminho obrigatório (US1) --------------------------------------------


def test_path_e_obrigatorio_no_dto() -> None:
    """RegisterFolderInput sem path é inválido (FR-004)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RegisterFolderInput(  # type: ignore[call-arg]
            alias="exemplo", description="d", content_type="documents", license="MIT"
        )


def test_path_canonizado_e_gravado() -> None:
    """O caminho devolvido pelo locator é o gravado (FR-002)."""
    repo = _FakeRepository()
    _register_folder(repo, _input(path="/srv/pastas/exemplo/"), locator=_FakeLocator())
    assert repo.saved is not None
    assert repo.saved.get("exemplo").path == "/srv/pastas/exemplo"


def test_caminho_ja_registrado_cita_dono_e_nao_salva() -> None:
    """Mesmo caminho sob outro alias → PathAlreadyRegisteredError(owner) (FR-003)."""
    from praxisforge.domain.errors import PathAlreadyRegisteredError

    repo = _FakeRepository()
    register_folder(repo, _input())
    repo.saved = None
    with pytest.raises(PathAlreadyRegisteredError) as info:
        register_folder(repo, _input(alias="outro_alias", path="/SRV/pastas/EXEMPLO"))
    assert info.value.owner == "exemplo"
    assert repo.saved is None


def test_caminho_aninhado_nao_salva() -> None:
    """Pasta dentro de outra registrada → NestedFolderPathError (FR-003)."""
    from praxisforge.domain.errors import NestedFolderPathError

    repo = _FakeRepository()
    register_folder(repo, _input())
    repo.saved = None
    with pytest.raises(NestedFolderPathError):
        register_folder(repo, _input(alias="dentro", path="/srv/pastas/exemplo/sub"))
    assert repo.saved is None


def test_locator_recusa_caminho_nada_salvo() -> None:
    """Caminho inexistente/sem permissão → exceção do locator, nada salvo (FR-004)."""
    from praxisforge.domain.errors import FolderPathInvalidError

    repo = _FakeRepository()
    with pytest.raises(FolderPathInvalidError):
        _register_folder(
            repo,
            _input(),
            locator=_FakeLocator(error=FolderPathInvalidError("exemplo", "caminho inexistente")),
        )
    assert repo.saved is None
