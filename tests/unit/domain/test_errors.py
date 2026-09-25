# -*- coding: utf-8 -*-
"""
NOME: test_errors.py
TITULO: Testes de falha — hierarquia de exceções semânticas do Domain
DATA: 22/09/2026 09:45
MODIFICADO: 25/09/2026 13:06
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 09:45: criação (T005) — hierarquia de data-model.md
    - 22/09/2026 17:36: +InvalidRootPathError (T005, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:04: +ContentInspectionError/InvalidCommitHashError (T003, feature 004)
    - 23/09/2026 16:47: exceções de caminho/migração (T003, feature 005)
    - 24/09/2026 10:51: exceções da política de extração (T003, feature 006)
    - 24/09/2026 14:30: exceções do registro fora do repositório (T002, feature 007)
    - 24/09/2026 16:40: exceções da biblioteca de skills (T003, feature 008)
    - 25/09/2026 13:06: mensagem de migração aponta o v3 (T041, feature 009)
STATUS: DEV
"""

import pytest

from praxisforge.domain.errors import (
    AliasAlreadyRegisteredError,
    ContentInspectionError,
    ContractValidationError,
    FolderNotFoundError,
    FolderPathInvalidError,
    FolderPathUnreadableError,
    FutureScanDateError,
    InvalidAliasError,
    InvalidCommitHashError,
    InvalidFolderError,
    InvalidFolderPathError,
    InvalidRootPathError,
    NestedFolderPathError,
    PathAlreadyRegisteredError,
    PraxisForgeError,
    RegistryFileNotFoundError,
    RegistryMigrationRequiredError,
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


def test_content_inspection_error_eh_praxisforge_error_e_cita_alias() -> None:
    """Falha de inspeção git é semântica e cita o alias, nunca caminho absoluto (FR-009)."""
    error = ContentInspectionError("repo", "tempo esgotado")
    assert isinstance(error, PraxisForgeError)
    assert error.alias == "repo"
    assert "repo" in str(error) and "tempo esgotado" in str(error)
    assert "/" not in str(error)


def test_invalid_commit_hash_error_eh_invalid_folder_error() -> None:
    """Hash malformado é uma violação de invariante de Folder (FR-011)."""
    error = InvalidCommitHashError("repo")
    assert isinstance(error, InvalidFolderError)
    assert "repo" in str(error)


def test_excecoes_de_caminho_da_feature_005() -> None:
    """Hierarquia e atributo owner (T003, feature 005)."""
    assert issubclass(InvalidFolderPathError, InvalidFolderError)
    duplicado = PathAlreadyRegisteredError("repo_a")
    aninhado = NestedFolderPathError("repo_a")
    for erro in (duplicado, aninhado):
        assert isinstance(erro, PraxisForgeError)
        assert erro.owner == "repo_a"
        assert "repo_a" in str(erro)
    migracao = RegistryMigrationRequiredError()
    assert isinstance(migracao, RegistryUnavailableError)
    assert "folders migrate" in str(migracao)


def test_excecoes_da_politica_de_extracao_feature_006() -> None:
    """Hierarquia, atributos e mensagens (T003, feature 006)."""
    from praxisforge.domain.errors import (
        ContractValidationError,
        ExtractPolicyExceedsLicenseError,
        IncompleteAttributionError,
        SourceSchemaMigrationRequiredError,
    )

    excede = ExtractPolicyExceedsLicenseError(
        license="Elastic-2.0", scope="code", declared="verbatim", maximum="summary"
    )
    assert isinstance(excede, PraxisForgeError)
    assert (excede.license, excede.scope, excede.declared, excede.maximum) == (
        "Elastic-2.0",
        "code",
        "verbatim",
        "summary",
    )
    assert str(excede) == (
        "política 'verbatim' excede a máxima 'summary' para a licença Elastic-2.0 (escopo: code)"
    )

    atribuicao = IncompleteAttributionError(field="author", policy="summary")
    assert isinstance(atribuicao, PraxisForgeError)
    assert atribuicao.field == "author"
    assert "author" in str(atribuicao) and "summary" in str(atribuicao)

    migracao = SourceSchemaMigrationRequiredError()
    assert isinstance(migracao, ContractValidationError)
    assert "extract_policy" in str(migracao) and "'3'" in str(migracao)


def test_excecoes_do_registro_fora_do_repo_feature_007() -> None:
    """Local do registro nas mensagens; novas exceções da realocação (T002, feature 007)."""
    from praxisforge.domain.errors import (
        RegistryAlreadyExistsError,
        RegistryFileNotFoundError,
        RegistryRelocationError,
    )

    ausente = RegistryFileNotFoundError("/cfg/praxisforge/folders.yaml")
    assert isinstance(ausente, RegistryUnavailableError)
    assert ausente.location == "/cfg/praxisforge/folders.yaml"
    assert "/cfg/praxisforge/folders.yaml" in str(ausente)
    assert "folders add" in str(ausente) and "folders bootstrap" in str(ausente)

    existe = RegistryAlreadyExistsError("/cfg/praxisforge/folders.yaml")
    assert isinstance(existe, PraxisForgeError)
    assert existe.location == "/cfg/praxisforge/folders.yaml"
    assert "/cfg/praxisforge/folders.yaml" in str(existe)

    falha = RegistryRelocationError("sem permissão de escrita")
    assert isinstance(falha, PraxisForgeError)
    assert "sem permissão de escrita" in str(falha)


def test_excecoes_da_biblioteca_de_skills_feature_008() -> None:
    """Exceções semânticas de skills (T003, feature 008)."""
    from praxisforge.domain.errors import (
        ForeignSkillDestinationError,
        InvalidSkillError,
        SkillNotFoundError,
        SkillPublicationError,
        SkillVersionNotBumpedError,
    )

    violacoes = [Violation("name", "difere da pasta"), Violation("description", "vazia")]
    invalida = InvalidSkillError("revisar", violacoes)
    assert isinstance(invalida, PraxisForgeError)
    assert invalida.name == "revisar"
    assert invalida.violations == violacoes
    assert "revisar" in str(invalida)
    assert "difere da pasta" in str(invalida) and "vazia" in str(invalida)

    ausente = SkillNotFoundError("revisar")
    assert isinstance(ausente, PraxisForgeError)
    assert ausente.name == "revisar" and "revisar" in str(ausente)

    terceiro = ForeignSkillDestinationError("revisar", "/destino/revisar")
    assert isinstance(terceiro, PraxisForgeError)
    assert terceiro.location == "/destino/revisar"
    assert "/destino/revisar" in str(terceiro) and "praxisforge" in str(terceiro)

    versao = SkillVersionNotBumpedError("revisar", "1.0.0")
    assert isinstance(versao, PraxisForgeError)
    assert versao.version == "1.0.0"
    assert "1.0.0" in str(versao) and "versão" in str(versao)

    gravacao = SkillPublicationError("revisar", "sem permissão")
    assert isinstance(gravacao, PraxisForgeError)
    assert gravacao.reason == "sem permissão" and "sem permissão" in str(gravacao)


def test_catalog_write_error_feature_008() -> None:
    """Falha de gravação do catálogo é semântica e cita o motivo."""
    from praxisforge.domain.errors import CatalogWriteError

    erro = CatalogWriteError("sem permissão")
    assert isinstance(erro, PraxisForgeError)
    assert erro.reason == "sem permissão" and "catálogo" in str(erro)
