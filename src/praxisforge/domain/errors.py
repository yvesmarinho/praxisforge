# -*- coding: utf-8 -*-
"""
NOME: errors.py
TITULO: Hierarquia de exceções semânticas do Domain e Application
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 12:07
VERSÃO: 0.1.0
DEPEND: (nenhuma — stdlib apenas; camada Domain)
HISTÓRICO:
    - 22/09/2026 09:45: criação (T017) — faz tests/unit/domain/test_errors.py passar
    - 22/09/2026 17:42: +InvalidRootPathError (T009, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:07: +InvalidCommitHashError, ContentInspectionError (T011, feature 004)
STATUS: DEV
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Violation:
    """
    Uma violação de contrato: campo e motivo.

    :param field: nome do campo violado (dot-path quando aninhado).
    :type field: str
    :param reason: motivo em pt-BR, sem caminho absoluto.
    :type reason: str
    """

    field: str
    reason: str


class PraxisForgeError(Exception):
    """Raiz da hierarquia de exceções semânticas do PraxisForge."""


class ContractValidationError(PraxisForgeError):
    """
    Um documento (registro ou fonte) viola o contrato JSON Schema.

    :param violations: lista de todas as violações encontradas de uma vez.
    :type violations: list[Violation]
    """

    def __init__(self, violations: list[Violation]) -> None:
        self.violations = violations
        resumo = "; ".join(f"{v.field}: {v.reason}" for v in violations)
        super().__init__(f"documento inválido — {resumo}" if resumo else "documento inválido")


class UnsupportedSchemaVersionError(ContractValidationError):
    """
    `schema_version` do documento não é suportada por esta versão do PraxisForge.

    :param found: versão encontrada no documento (ou None se ausente).
    :type found: str | None
    :param supported: tupla das versões suportadas.
    :type supported: tuple[str, ...]
    """

    def __init__(self, found: str | None, supported: tuple[str, ...]) -> None:
        self.found = found
        self.supported = supported
        violation = Violation(
            field="schema_version",
            reason=(
                f"versão '{found}' não suportada; suportadas: {', '.join(supported)}"
                if found is not None
                else f"campo ausente; suportadas: {', '.join(supported)}"
            ),
        )
        super().__init__([violation])


class InvalidAliasError(PraxisForgeError):
    """Alias fora do formato `^[a-z][a-z0-9_]{1,62}$`."""


class InvalidFolderError(PraxisForgeError):
    """Uma invariante da entidade Folder foi violada."""


class UnknownLicenseRequiresPendingError(InvalidFolderError):
    """Licença `unknown` exige status `pending`."""

    def __init__(self, alias: str = "") -> None:
        super().__init__(
            f"pasta '{alias}': licença 'unknown' exige status 'pending'"
            if alias
            else "licença 'unknown' exige status 'pending'"
        )


class FutureScanDateError(InvalidFolderError):
    """`last_scanned` está no futuro."""

    def __init__(self, alias: str = "") -> None:
        super().__init__(
            f"pasta '{alias}': last_scanned não pode estar no futuro"
            if alias
            else "last_scanned não pode estar no futuro"
        )


class InvalidCommitHashError(InvalidFolderError):
    """`last_curated_commit` fora do formato SHA-1/SHA-256 hexadecimal minúsculo."""

    def __init__(self, alias: str = "") -> None:
        super().__init__(
            f"pasta '{alias}': last_curated_commit fora do formato (40 ou 64 hex minúsculos)"
            if alias
            else "last_curated_commit fora do formato (40 ou 64 hex minúsculos)"
        )


class AliasAlreadyRegisteredError(PraxisForgeError):
    """Alias já registrado com dados diferentes dos informados."""

    def __init__(self, alias: str) -> None:
        self.alias = alias
        super().__init__(f"alias '{alias}' já registrado com dados diferentes")


class FolderNotFoundError(PraxisForgeError):
    """Alias não encontrado no registro."""

    def __init__(self, alias: str) -> None:
        self.alias = alias
        super().__init__(f"pasta '{alias}' não encontrada no registro")


class RegistryUnavailableError(PraxisForgeError):
    """Registro ilegível ou corrompido (Infrastructure)."""

    def __init__(self, reason: str = "registro indisponível") -> None:
        super().__init__(reason)


class RegistryFileNotFoundError(RegistryUnavailableError):
    """Arquivo do registro ausente (só `folders add` pode criá-lo)."""

    def __init__(self) -> None:
        super().__init__("registro ausente")


class FolderPathNotConfiguredError(PraxisForgeError):
    """Variável de ambiente `PRAXISFORGE_FOLDER_<ALIAS>` ausente ou vazia."""

    def __init__(self, alias: str) -> None:
        self.alias = alias
        super().__init__(
            f"variável PRAXISFORGE_FOLDER_{alias.upper()} não configurada para '{alias}'"
        )


class FolderPathInvalidError(PraxisForgeError):
    """Caminho configurado é relativo, contém `..`, não existe ou não é diretório."""

    def __init__(self, alias: str, reason: str = "caminho inválido") -> None:
        self.alias = alias
        super().__init__(f"pasta '{alias}': {reason}")


class FolderPathUnreadableError(PraxisForgeError):
    """Caminho configurado existe mas sem permissão de leitura."""

    def __init__(self, alias: str) -> None:
        self.alias = alias
        super().__init__(f"pasta '{alias}': sem permissão de leitura")


class InvalidRootPathError(PraxisForgeError):
    """
    Pasta-raiz do bootstrap inexistente, não é diretório ou sem permissão de leitura.

    Diferente dos erros de caminho por alias, esta exceção cita o caminho da própria
    pasta-raiz na mensagem — exceção explícita de FR-014 (a raiz é o "próprio item com
    erro" quando ela mesma é o problema, sem alias para citar em seu lugar).

    :param root: caminho da pasta-raiz recebida como argumento.
    :type root: str
    :param reason: motivo em pt-BR (ex.: "não existe", "não é um diretório").
    :type reason: str
    """

    def __init__(self, root: str, reason: str = "caminho inválido") -> None:
        self.root = root
        super().__init__(f"pasta-raiz '{root}': {reason}")


__all__ = [
    "AliasAlreadyRegisteredError",
    "ContractValidationError",
    "FolderNotFoundError",
    "FolderPathInvalidError",
    "FolderPathNotConfiguredError",
    "FolderPathUnreadableError",
    "FutureScanDateError",
    "InvalidAliasError",
    "InvalidFolderError",
    "InvalidRootPathError",
    "PraxisForgeError",
    "RegistryFileNotFoundError",
    "RegistryUnavailableError",
    "UnknownLicenseRequiresPendingError",
    "UnsupportedSchemaVersionError",
    "Violation",
]


class ContentInspectionError(PraxisForgeError):
    """
    Falha ao inspecionar o conteúdo versionado de uma pasta (feature 004).

    Cobre git indisponível, tempo esgotado e saída inesperada. A mensagem nunca
    contém caminho absoluto — só o alias (quando conhecido) e o motivo.

    :param alias: alias da pasta; vazio quando o adapter ainda não o conhece.
    :type alias: str
    :param reason: motivo em pt-BR (ex.: "tempo esgotado").
    :type reason: str
    """

    def __init__(self, alias: str, reason: str) -> None:
        self.alias = alias
        self.reason = reason
        super().__init__(
            f"pasta '{alias}': falha ao inspecionar conteúdo: {reason}"
            if alias
            else f"falha ao inspecionar conteúdo: {reason}"
        )
