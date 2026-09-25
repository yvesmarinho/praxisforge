# -*- coding: utf-8 -*-
"""
NOME: errors.py
TITULO: Hierarquia de exceções semânticas do Domain e Application
DATA: 22/09/2026 09:45
MODIFICADO: 25/09/2026 09:56
VERSÃO: 0.1.0
DEPEND: (nenhuma — stdlib apenas; camada Domain)
HISTÓRICO:
    - 22/09/2026 09:45: criação (T017) — faz tests/unit/domain/test_errors.py passar
    - 22/09/2026 17:42: +InvalidRootPathError (T009, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:07: +InvalidCommitHashError, ContentInspectionError (T011, feature 004)
    - 24/09/2026 10:52: exceções da política de extração (T009, feature 006)
    - 24/09/2026 14:31: registro fora do repositório: local no erro de ausência + realocação
      (T006, feature 007)
    - 24/09/2026 16:54: exceções de skills (T008) e CatalogWriteError (T025), feature 008
    - 25/09/2026 09:56: ProjectRootNotFoundError (CLI independente do cwd)
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
    """
    Arquivo do registro ausente (só `folders add`/`folders bootstrap` o criam).

    :param location: local resolvido do registro (o próprio item com problema); vazio quando
        desconhecido.
    :type location: str
    """

    def __init__(self, location: str = "") -> None:
        self.location = location
        onde = f" em {location}" if location else ""
        super().__init__(f"registro ausente{onde} — crie com folders add ou folders bootstrap")


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
    "CatalogWriteError",
    "ContentInspectionError",
    "ContractValidationError",
    "ExtractPolicyExceedsLicenseError",
    "FolderNotFoundError",
    "ForeignSkillDestinationError",
    "FolderPathInvalidError",
    "FolderPathUnreadableError",
    "FutureScanDateError",
    "IncompleteAttributionError",
    "InvalidAliasError",
    "InvalidCommitHashError",
    "InvalidFolderError",
    "InvalidFolderPathError",
    "InvalidRootPathError",
    "InvalidSkillError",
    "NestedFolderPathError",
    "NothingToRelocateError",
    "PathAlreadyRegisteredError",
    "PraxisForgeError",
    "RegistryAlreadyExistsError",
    "RegistryFileNotFoundError",
    "RegistryMigrationRequiredError",
    "RegistryRelocationError",
    "RegistryUnavailableError",
    "SkillNotFoundError",
    "SkillPublicationError",
    "SkillVersionNotBumpedError",
    "SourceSchemaMigrationRequiredError",
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


class InvalidFolderPathError(InvalidFolderError):
    """`path` fora da forma absoluta canônica (feature 005)."""

    def __init__(self, alias: str = "", reason: str = "caminho fora da forma absoluta") -> None:
        super().__init__(f"pasta '{alias}': {reason}" if alias else reason)


class PathAlreadyRegisteredError(PraxisForgeError):
    """
    Caminho já registrado por outra pasta (comparação sem diferenciar maiúsculas).

    :param owner: alias da pasta que já ocupa o caminho.
    :type owner: str
    """

    def __init__(self, owner: str) -> None:
        self.owner = owner
        super().__init__(f"caminho já registrado pela pasta '{owner}'")


class NestedFolderPathError(PraxisForgeError):
    """
    Caminho dentro de (ou contendo) outra pasta registrada — aninhamento proibido.

    :param owner: alias da pasta registrada com a qual há aninhamento.
    :type owner: str
    """

    def __init__(self, owner: str) -> None:
        self.owner = owner
        super().__init__(f"caminho aninhado com a pasta registrada '{owner}'")


class RegistryMigrationRequiredError(RegistryUnavailableError):
    """Registro em formato antigo (v1) — exige `praxisforge folders migrate`."""

    def __init__(self) -> None:
        super().__init__(
            "registro no formato v1 — execute: praxisforge folders migrate [--root <pasta-raiz>]"
        )


class ExtractPolicyExceedsLicenseError(PraxisForgeError):
    """
    Política de extração declarada acima da máxima permitida pela licença (feature 006).

    :param license: licença declarada na fonte.
    :type license: str
    :param scope: escopo considerado (docs ou code).
    :type scope: str
    :param declared: política declarada.
    :type declared: str
    :param maximum: política máxima para a licença e o escopo.
    :type maximum: str
    """

    def __init__(self, license: str, scope: str, declared: str, maximum: str) -> None:  # noqa: A002
        self.license = license
        self.scope = scope
        self.declared = declared
        self.maximum = maximum
        super().__init__(
            f"política '{declared}' excede a máxima '{maximum}' para a licença {license} "
            f"(escopo: {scope})"
        )


class IncompleteAttributionError(PraxisForgeError):
    """
    Campo de atribuição/conformidade exigido pela política está ausente ou inválido.

    :param field: campo exigido (ex.: author, notice_preserved, modified).
    :type field: str
    :param policy: política declarada que exige o campo.
    :type policy: str
    """

    def __init__(self, field: str, policy: str) -> None:
        self.field = field
        self.policy = policy
        super().__init__(f"política '{policy}' exige o campo '{field}'")


class SourceSchemaMigrationRequiredError(ContractValidationError):
    """Registro de fonte no formato v1 (extract_allowed) — não é mais aceito."""

    def __init__(self) -> None:
        super().__init__(
            [
                Violation(
                    field="schema_version",
                    reason="source-schema-v1 não é mais aceito — use extract_policy "
                    "(source-schema-v2)",
                )
            ]
        )


class RegistryAlreadyExistsError(PraxisForgeError):
    """
    Já existe registro no destino da realocação — nada é sobrescrito (feature 007).

    :param location: destino resolvido.
    :type location: str
    """

    def __init__(self, location: str) -> None:
        self.location = location
        super().__init__(f"já existe registro em {location}; nada foi alterado")


class RegistryRelocationError(PraxisForgeError):
    """
    Falha de I/O ao realocar o registro; a origem permanece intacta (feature 007).

    :param reason: motivo em pt-BR.
    :type reason: str
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"falha ao realocar o registro: {reason}")


class NothingToRelocateError(PraxisForgeError):
    """Registro de origem sem pastas — nada a realocar (feature 007)."""

    def __init__(self) -> None:
        super().__init__("registro de origem sem pastas; nada a mover")


class InvalidSkillError(PraxisForgeError):
    """
    Skill viola o formato ou a proveniência exigidos (feature 008).

    :param name: nome da skill (pasta) avaliada.
    :type name: str
    :param violations: todas as violações encontradas de uma vez.
    :type violations: list[Violation]
    """

    def __init__(self, name: str, violations: list[Violation]) -> None:
        self.name = name
        self.violations = violations
        resumo = "; ".join(f"{v.field}: {v.reason}" for v in violations)
        super().__init__(
            f"skill '{name}' inválida — {resumo}" if resumo else f"skill '{name}' inválida"
        )


class SkillNotFoundError(PraxisForgeError):
    """Skill pedida não existe em `skills/` (feature 008)."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"skill '{name}' não encontrada")


class ForeignSkillDestinationError(PraxisForgeError):
    """
    Destino de mesmo nome não foi publicado pelo praxisforge — nada é alterado (feature 008).

    :param name: nome da skill.
    :type name: str
    :param location: destino existente.
    :type location: str
    """

    def __init__(self, name: str, location: str) -> None:
        self.name = name
        self.location = location
        super().__init__(
            f"destino {location} não foi publicado pelo praxisforge; nada foi alterado"
        )


class SkillVersionNotBumpedError(PraxisForgeError):
    """
    Conteúdo mudou mas `metadata.version` é a mesma já publicada (feature 008).

    :param name: nome da skill.
    :type name: str
    :param version: versão já publicada.
    :type version: str
    """

    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version
        super().__init__(
            f"conteúdo alterado com a mesma versão {version} já publicada — incremente a versão"
        )


class SkillPublicationError(PraxisForgeError):
    """
    Falha de gravação ao publicar; o destino permanece como estava (feature 008).

    :param name: nome da skill.
    :type name: str
    :param reason: motivo em pt-BR.
    :type reason: str
    """

    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.reason = reason
        super().__init__(f"falha ao publicar a skill '{name}': {reason}")


class CatalogWriteError(PraxisForgeError):
    """
    Falha ao gravar `skills/README.md`; o catálogo anterior permanece (feature 008).

    :param reason: motivo em pt-BR.
    :type reason: str
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"falha ao gravar o catálogo: {reason}")


class ProjectRootNotFoundError(PraxisForgeError):
    """
    Raiz do projeto praxisforge não encontrada (nem por `PRAXISFORGE_ROOT`, nem subindo do cwd).

    :param reason: motivo em pt-BR.
    :type reason: str
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"raiz do projeto não encontrada: {reason}")
