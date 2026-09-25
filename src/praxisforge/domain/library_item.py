# -*- coding: utf-8 -*-
"""
NOME: library_item.py
TITULO: Tipos de recurso do acervo (ItemKind), ItemName e entidade LibraryItem
DATA: 25/09/2026 13:01
MODIFICADO: 25/09/2026 13:01
VERSÃO: 0.1.0
DEPEND: (nenhuma — stdlib apenas; camada Domain)
HISTÓRICO:
    - 25/09/2026 13:01: criação (T011, feature 009) — generaliza domain/skill.py para seis tipos
STATUS: DEV
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from praxisforge.domain.errors import InvalidLibraryItemError, UnknownItemKindError, Violation
from praxisforge.domain.skill import (
    _SEMVER_RE,
    _check_description,
    _check_sources,
    _name_violation,
    _reference_escapes,
)

HOOK_EVENTS = (
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
    "SessionStart",
    "SessionEnd",
    "Notification",
    "PreCompact",
)


class ItemKind(Enum):
    """
    Tipo de recurso do acervo e suas regras de layout (tabela do data-model da 009).

    :Example:

    >>> ItemKind.from_str("hook").main_file
    'HOOK.md'
    >>> ItemKind.COMMAND.is_folder
    False
    """

    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    HOOK = "hook"
    RULE = "rule"
    REFERENCE = "reference"

    @property
    def directory(self) -> str:
        """Diretório do tipo dentro de `library/` (plural)."""
        return f"{self.value}s"

    @property
    def is_folder(self) -> bool:
        """True quando o item é uma pasta com arquivo principal (skill, hook)."""
        return self in (ItemKind.SKILL, ItemKind.HOOK)

    @property
    def main_file(self) -> str | None:
        """Arquivo principal dos tipos de pasta; None nos de arquivo único."""
        return {ItemKind.SKILL: "SKILL.md", ItemKind.HOOK: "HOOK.md"}.get(self)

    @property
    def name_in_frontmatter(self) -> bool:
        """True quando o frontmatter declara `name` (deve ser igual à pasta/arquivo)."""
        return self not in (ItemKind.COMMAND, ItemKind.RULE)

    @property
    def publishable(self) -> bool:
        """True para os tipos publicáveis em projetos (FR-019)."""
        return self not in (ItemKind.HOOK, ItemKind.REFERENCE)

    @classmethod
    def from_str(cls, value: str) -> "ItemKind":
        """
        Converte o nome do tipo.

        :param value: nome do tipo (singular).
        :type value: str
        :return: o tipo.
        :rtype: ItemKind
        :raises UnknownItemKindError: fora dos seis tipos.
        """
        for kind in cls:
            if kind.value == value:
                return kind
        raise UnknownItemKindError(str(value))

    @classmethod
    def from_directory(cls, directory: str) -> "ItemKind":
        """
        Converte o nome do diretório de tipo.

        :param directory: diretório dentro de `library/` (plural).
        :type directory: str
        :return: o tipo.
        :rtype: ItemKind
        :raises UnknownItemKindError: diretório que não é de tipo.
        """
        for kind in cls:
            if kind.directory == directory:
                return kind
        raise UnknownItemKindError(str(directory))


@dataclass(frozen=True)
class ItemName:
    """
    Nome de item: minúsculas, dígitos e hífens entre partes, até 64 caracteres.

    :param value: nome candidato.
    :type value: str
    :raises InvalidLibraryItemError: nome fora do formato.

    :Example:

    >>> ItemName("revisar-codigo").value
    'revisar-codigo'
    """

    value: str

    def __post_init__(self) -> None:
        violation = _name_violation(self.value)
        if violation is not None:
            raise InvalidLibraryItemError("?", str(self.value), [violation])


def _check_bool(meta: Mapping[str, object], field: str) -> tuple[bool, list[Violation]]:
    value = meta.get(field, False)
    if not isinstance(value, bool):
        return False, [Violation(f"metadata.{field}", "deve ser verdadeiro ou falso")]
    return value, []


def _check_item_references(
    kind: ItemKind, value: object
) -> tuple[tuple[str, ...], list[Violation]]:
    if value is None:
        return (), []
    if kind is not ItemKind.SKILL:
        return (), [Violation("metadata.references", "só skills podem citar references")]
    if not isinstance(value, list) or not all(
        isinstance(v, str) and _name_violation(v) is None for v in value
    ):
        return (), [Violation("metadata.references", "deve ser lista de nomes de reference")]
    if len(set(value)) != len(value):
        return tuple(value), [Violation("metadata.references", "nomes repetidos")]
    return tuple(value), []


def _check_support(kind: ItemKind, references: Sequence[str], missing: set[str]) -> list[Violation]:
    if not references:
        return []
    if not kind.is_folder:
        return [
            Violation("references", f"'{ref}': item de arquivo único não cita arquivos locais")
            for ref in references
        ]
    violations = [
        Violation("references", f"'{ref}' fora da pasta do item")
        for ref in references
        if _reference_escapes(ref)
    ]
    violations.extend(
        Violation("references", f"'{ref}' não encontrado") for ref in references if ref in missing
    )
    return violations


def _check_hook(
    frontmatter: Mapping[str, object], missing: set[str]
) -> tuple[tuple[str | None, str | None, tuple[str, ...]], list[Violation]]:
    violations: list[Violation] = []
    event = frontmatter.get("event")
    if event not in HOOK_EVENTS:
        violations.append(Violation("event", f"'{event}' não é evento do Claude Code"))
    matcher = frontmatter.get("matcher")
    if matcher is not None and (not isinstance(matcher, str) or not matcher.strip()):
        violations.append(Violation("matcher", "quando presente, texto não vazio"))
    run = frontmatter.get("run")
    run_files: tuple[str, ...] = ()
    if not isinstance(run, list) or not run or not all(isinstance(r, str) and r for r in run):
        violations.append(Violation("run", "lista não vazia dos arquivos executados"))
    else:
        run_files = tuple(run)
        for arquivo in run_files:
            if _reference_escapes(arquivo):
                violations.append(Violation("run", f"'{arquivo}' fora da pasta do hook"))
            elif arquivo in missing:
                violations.append(Violation("run", f"'{arquivo}' não encontrado"))
    return (
        (
            event if isinstance(event, str) else None,
            matcher if isinstance(matcher, str) else None,
            run_files,
        ),
        violations,
    )


def _check_paths(value: object) -> tuple[tuple[str, ...], list[Violation]]:
    if value is None:
        return (), []
    if not isinstance(value, list) or not value or not all(isinstance(v, str) and v for v in value):
        return (), [Violation("paths", "lista não vazia de globs")]
    return tuple(value), []


@dataclass(frozen=True)
class LibraryItem:
    """
    Item do acervo `library/` (forma já conferida). Construir por `LibraryItem.from_parts`.
    """

    kind: ItemKind
    name: str
    description: str
    version: str
    sources: tuple[str, ...]
    authored: bool
    rewrite_pending: bool
    references: tuple[str, ...]
    support_files: tuple[str, ...]
    hook_event: str | None = None
    hook_matcher: str | None = None
    hook_run: tuple[str, ...] = ()
    rule_paths: tuple[str, ...] = ()

    @classmethod
    def from_parts(
        cls,
        kind: ItemKind,
        entry_name: str,
        frontmatter: Mapping[str, object],
        support_files: Sequence[str] = (),
        missing_files: Iterable[str] = (),
    ) -> "LibraryItem":
        """
        Monta o item a partir do frontmatter, coletando todas as violações de uma vez.

        :param kind: tipo do item.
        :type kind: ItemKind
        :param entry_name: nome da pasta (skill, hook) ou do arquivo sem `.md`.
        :type entry_name: str
        :param frontmatter: frontmatter do arquivo principal.
        :type frontmatter: Mapping[str, object]
        :param support_files: alvos locais citados no corpo.
        :type support_files: Sequence[str]
        :param missing_files: arquivos citados (corpo ou `run`) que não existem.
        :type missing_files: Iterable[str]
        :return: a entidade.
        :rtype: LibraryItem
        :raises InvalidLibraryItemError: com todas as violações encontradas.

        :Example:

        >>> fm = {"description": "d", "metadata": {"version": "1.0.0", "authored": True}}
        >>> LibraryItem.from_parts(ItemKind.COMMAND, "revisar", fm).name
        'revisar'
        """
        missing = set(missing_files)
        violations: list[Violation] = []
        if kind.name_in_frontmatter:
            name = frontmatter.get("name")
            name_violation = _name_violation(name)
            if name_violation is not None:
                violations.append(name_violation)
            if name != entry_name:
                violations.append(
                    Violation("name", f"'{name}' difere do nome da pasta/arquivo '{entry_name}'")
                )
        else:
            name_violation = _name_violation(entry_name)
            if name_violation is not None:
                violations.append(name_violation)
        description = frontmatter.get("description")
        violations.extend(_check_description(description))

        metadata = frontmatter.get("metadata")
        meta: Mapping[str, object] = metadata if isinstance(metadata, Mapping) else {}
        version = meta.get("version")
        if not isinstance(version, str) or not _SEMVER_RE.match(version):
            violations.append(Violation("metadata.version", f"'{version}' não é semver"))
        sources, source_violations = _check_sources(meta.get("sources"))
        violations.extend(source_violations)
        authored, bool_violations = _check_bool(meta, "authored")
        violations.extend(bool_violations)
        rewrite_pending, bool_violations = _check_bool(meta, "rewrite_pending")
        violations.extend(bool_violations)
        if not sources and not authored and not source_violations:
            violations.append(
                Violation("metadata.sources", "sem fontes declaradas — marque authored: true")
            )
        references, ref_violations = _check_item_references(kind, meta.get("references"))
        violations.extend(ref_violations)
        violations.extend(_check_support(kind, support_files, missing))

        hook: tuple[str | None, str | None, tuple[str, ...]] = (None, None, ())
        if kind is ItemKind.HOOK:
            hook, hook_violations = _check_hook(frontmatter, missing)
            violations.extend(hook_violations)
        rule_paths: tuple[str, ...] = ()
        if kind is ItemKind.RULE:
            rule_paths, path_violations = _check_paths(frontmatter.get("paths"))
            violations.extend(path_violations)

        if violations:
            raise InvalidLibraryItemError(kind.value, entry_name, violations)
        return cls(
            kind=kind,
            name=entry_name,
            description=str(description).strip(),
            version=str(version),
            sources=sources,
            authored=authored,
            rewrite_pending=rewrite_pending,
            references=references,
            support_files=tuple(support_files),
            hook_event=hook[0],
            hook_matcher=hook[1],
            hook_run=hook[2],
            rule_paths=rule_paths,
        )
