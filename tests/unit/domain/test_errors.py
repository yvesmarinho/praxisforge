# -*- coding: utf-8 -*-
"""
NOME: test_errors.py
TITULO: Testes de falha — hierarquia de exceções semânticas do Domain
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 16:37
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 09:45: criação (T005) — hierarquia de data-model.md
    - 22/09/2026 17:36: +InvalidRootPathError (T005, feature 003-bootstrap-registro-pastas)
STATUS: DEV
"""

import pytest

from praxisforge.domain.errors import (
    AliasAlreadyRegisteredError,
    ContractValidationError,
    FolderNotFoundError,
    FolderPathInvalidError,
    FolderPathNotConfiguredError,
    FolderPathUnreadableError,
    FutureScanDateError,
    InvalidAliasError,
    InvalidFolderError,
    InvalidRootPathError,
    PraxisForgeError,
    RegistryFileNotFoundError,
    RegistryUnavailableError,
    UnknownLicenseRequiresPendingError,
    UnsupportedSchemaVersionError,
    Violation,
)


@pytest.mark.parametrize(
    "exc_class",
    [
        ContractValidationError,
        UnsupportedSchemaVersionError,
        InvalidAliasError,
        InvalidFolderError,
        UnknownLicenseRequiresPendingError,
        FutureScanDateError,
        AliasAlreadyRegisteredError,
        FolderNotFoundError,
        RegistryUnavailableError,
        RegistryFileNotFoundError,
        FolderPathNotConfiguredError,
        FolderPathInvalidError,
        FolderPathUnreadableError,
        InvalidRootPathError,
    ],
)
def test_todas_derivam_de_praxisforge_error(exc_class: type[Exception]) -> None:
    """Toda exceção semântica do domínio deriva de PraxisForgeError."""
    assert issubclass(exc_class, PraxisForgeError)


def test_unsupported_schema_version_deriva_de_contract_validation() -> None:
    """UnsupportedSchemaVersionError é um caso específico de ContractValidationError."""
    assert issubclass(UnsupportedSchemaVersionError, ContractValidationError)


def test_registry_file_not_found_deriva_de_registry_unavailable() -> None:
    """RegistryFileNotFoundError é um caso específico de RegistryUnavailableError."""
    assert issubclass(RegistryFileNotFoundError, RegistryUnavailableError)


def test_invalid_folder_subtipos() -> None:
    """UnknownLicenseRequiresPendingError e FutureScanDateError derivam de InvalidFolderError."""
    assert issubclass(UnknownLicenseRequiresPendingError, InvalidFolderError)
    assert issubclass(FutureScanDateError, InvalidFolderError)


def test_violation_carrega_campo_e_motivo() -> None:
    """Violation é um par (campo, motivo)."""
    violation = Violation(field="license", reason="valor 'invalido' não é SPDX nem 'unknown'")
    assert violation.field == "license"
    assert "SPDX" in violation.reason


def test_contract_validation_error_carrega_lista_de_violations() -> None:
    """ContractValidationError carrega a lista completa de violações do documento."""
    violations = [
        Violation(field="status", reason="valor fora do conjunto permitido"),
        Violation(field="license", reason="campo ausente"),
    ]
    error = ContractValidationError(violations)
    assert list(error.violations) == violations


def test_unsupported_schema_version_informa_encontrada_e_suportadas() -> None:
    """UnsupportedSchemaVersionError expõe a versão encontrada e as suportadas."""
    error = UnsupportedSchemaVersionError(found="2", supported=("1",))
    assert error.found == "2"
    assert error.supported == ("1",)


@pytest.mark.parametrize(
    "make_error",
    [
        lambda: ContractValidationError([Violation(field="x", reason="y")]),
        lambda: UnsupportedSchemaVersionError(found="2", supported=("1",)),
        lambda: InvalidAliasError("alias inválido: 'Exemplo'"),
        lambda: AliasAlreadyRegisteredError("exemplo"),
        lambda: FolderNotFoundError("exemplo"),
        lambda: RegistryFileNotFoundError(),
        lambda: FolderPathNotConfiguredError("github_forks"),
        lambda: FolderPathInvalidError("github_forks", reason="caminho relativo"),
        lambda: FolderPathUnreadableError("github_forks"),
    ],
)
def test_mensagens_nao_contem_caminho_absoluto(make_error: object) -> None:
    """Nenhuma mensagem de exceção semântica contém caminho absoluto do sistema."""
    error = make_error()  # type: ignore[operator]
    message = str(error)
    assert "/home/" not in message
    assert "/Users/" not in message


def test_invalid_root_path_error_cita_root_e_motivo() -> None:
    """InvalidRootPathError(root, reason) cita a raiz e o motivo (exceção de FR-014)."""
    raiz = "/tmp/raiz-inexistente"  # noqa: S108 - só usado como texto, nunca criado/acessado
    error = InvalidRootPathError(raiz, reason="não existe")
    assert issubclass(InvalidRootPathError, PraxisForgeError)
    message = str(error)
    assert raiz in message
    assert "não existe" in message
