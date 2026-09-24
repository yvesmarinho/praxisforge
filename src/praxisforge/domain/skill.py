# -*- coding: utf-8 -*-
"""
NOME: skill.py
TITULO: Entidade Skill, value object SkillName e extração de referências do SKILL.md
DATA: 24/09/2026 16:54
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: (nenhuma — stdlib apenas; camada Domain)
HISTÓRICO:
    - 24/09/2026 16:54: criação (T009, feature 008) — faz tests/unit/domain/test_skill.py passar
    - 24/09/2026 16:54: links dentro de código não são referências (bug do quickstart, T042)
STATUS: DEV
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from praxisforge.domain.errors import InvalidSkillError, Violation

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_NAME_MAX = 64
_DESCRIPTION_MAX = 1024
# Regex oficial do semver 2.0 (semver.org), com pré-release e build opcionais
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
_LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_EXTERNAL_PREFIXES = ("http:", "https:", "mailto:")
_FENCE_RE = re.compile(
    r"^[ ]{0,3}(`{3,}|~{3,})[^\n]*\n.*?^[ ]{0,3}\1[ \t]*$", re.MULTILINE | re.DOTALL
)
_INLINE_CODE_RE = re.compile(r"(`+)(?!`).*?(?<!`)\1(?!`)", re.DOTALL)
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def _name_violation(value: object) -> Violation | None:
    if not isinstance(value, str) or not _NAME_RE.match(value) or len(value) > _NAME_MAX:
        return Violation(
            "name", f"'{value}' fora do formato minúsculo-com-hífen (até {_NAME_MAX} caracteres)"
        )
    return None


@dataclass(frozen=True)
class SkillName:
    """
    Nome de skill: minúsculas, dígitos e hífens entre partes, até 64 caracteres.

    :param value: nome candidato.
    :type value: str
    :raises InvalidSkillError: nome fora do formato.

    :Example:

    >>> SkillName("revisar-codigo").value
    'revisar-codigo'
    """

    value: str

    def __post_init__(self) -> None:
        violation = _name_violation(self.value)
        if violation is not None:
            raise InvalidSkillError(str(self.value), [violation])


def extract_references(body: str) -> list[str]:
    """
    Extrai os alvos locais de links e imagens Markdown do corpo, em ordem e sem duplicatas.

    Ignora `http:`, `https:`, `mailto:`, âncoras puras e links dentro de código (inline ou
    blocos cercados, que são exemplos); remove `#fragmento`.

    :param body: corpo do SKILL.md (sem frontmatter).
    :type body: str
    :return: alvos relativos citados.
    :rtype: list[str]

    :Example:

    >>> extract_references("[a](ref/a.md#x) [b](https://x.io) [c](#y)")
    ['ref/a.md']
    """
    alvos: list[str] = []
    texto = _INLINE_CODE_RE.sub("", _FENCE_RE.sub("", body))
    for match in _LINK_RE.finditer(texto):
        alvo = match.group(1)
        if alvo.startswith("#") or alvo.lower().startswith(_EXTERNAL_PREFIXES):
            continue
        alvo = alvo.split("#", 1)[0]
        if alvo and alvo not in alvos:
            alvos.append(alvo)
    return alvos


def _reference_escapes(reference: str) -> bool:
    if reference.startswith(("/", "\\")) or _SCHEME_RE.match(reference):
        return True
    profundidade = 0
    for parte in PurePosixPath(reference.replace("\\", "/")).parts:
        if parte == "..":
            profundidade -= 1
            if profundidade < 0:
                return True
        elif parte != ".":
            profundidade += 1
    return False


def _check_description(value: object) -> list[Violation]:
    if not isinstance(value, str) or not value.strip():
        return [Violation("description", "obrigatória e não vazia")]
    if len(value) > _DESCRIPTION_MAX:
        return [Violation("description", f"mais de {_DESCRIPTION_MAX} caracteres")]
    return []


def _check_sources(value: object) -> tuple[tuple[str, ...], list[Violation]]:
    if value is None:
        return (), []
    if not isinstance(value, list) or not all(isinstance(s, str) and s for s in value):
        return (), [Violation("metadata.sources", "deve ser lista de slugs não vazios")]
    if len(set(value)) != len(value):
        return tuple(value), [Violation("metadata.sources", "slugs repetidos")]
    return tuple(value), []


def _check_references(references: Sequence[str], missing: Iterable[str]) -> list[Violation]:
    violations = [
        Violation("references", f"'{ref}' fora da pasta da skill")
        for ref in references
        if _reference_escapes(ref)
    ]
    violations.extend(Violation("references", f"'{ref}' não encontrado") for ref in missing)
    return violations


@dataclass(frozen=True)
class Skill:
    """
    Skill versionada do praxisforge (forma do SKILL.md já conferida).

    Construir por `Skill.from_parts`, que coleta todas as violações de uma vez.
    """

    name: str
    description: str
    version: str
    sources: tuple[str, ...]
    authored: bool
    license: str | None
    references: tuple[str, ...]

    @classmethod
    def from_parts(
        cls,
        folder_name: str,
        frontmatter: Mapping[str, object],
        references: Sequence[str],
        missing_references: Iterable[str] = (),
    ) -> "Skill":
        """
        Monta a skill a partir do frontmatter e das referências do corpo.

        :param folder_name: nome da pasta da skill.
        :type folder_name: str
        :param frontmatter: frontmatter do SKILL.md.
        :type frontmatter: Mapping[str, object]
        :param references: alvos locais citados no corpo.
        :type references: Sequence[str]
        :param missing_references: referências que não existem na pasta.
        :type missing_references: Iterable[str]
        :return: a entidade.
        :rtype: Skill
        :raises InvalidSkillError: com todas as violações encontradas.

        :Example:

        >>> meta = {"version": "1.0.0", "authored": True}
        >>> fm = {"name": "a", "description": "d", "metadata": meta}
        >>> Skill.from_parts("a", fm, []).version
        '1.0.0'
        """
        violations: list[Violation] = []
        name = frontmatter.get("name")
        name_violation = _name_violation(name)
        if name_violation is not None:
            violations.append(name_violation)
        if name != folder_name:
            violations.append(
                Violation("name", f"'{name}' difere do nome da pasta '{folder_name}'")
            )
        description = frontmatter.get("description")
        violations.extend(_check_description(description))

        metadata = frontmatter.get("metadata")
        meta: Mapping[str, object] = metadata if isinstance(metadata, Mapping) else {}
        version = meta.get("version")
        if not isinstance(version, str) or not _SEMVER_RE.match(version):
            violations.append(Violation("metadata.version", f"'{version}' não é semver"))
        sources, source_violations = _check_sources(meta.get("sources"))
        violations.extend(source_violations)
        authored = meta.get("authored", False)
        if not isinstance(authored, bool):
            violations.append(Violation("metadata.authored", "deve ser verdadeiro ou falso"))
            authored = False
        if not sources and not authored and not source_violations:
            violations.append(
                Violation("metadata.sources", "sem fontes declaradas — marque authored: true")
            )
        violations.extend(_check_references(references, missing_references))

        license_value = frontmatter.get("license")
        if violations:
            raise InvalidSkillError(folder_name, violations)
        return cls(
            name=str(name),
            description=str(description).strip(),
            version=str(version),
            sources=sources,
            authored=authored,
            license=license_value if isinstance(license_value, str) else None,
            references=tuple(references),
        )
