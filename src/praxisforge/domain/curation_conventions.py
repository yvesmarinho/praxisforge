# -*- coding: utf-8 -*-
"""
NOME: curation_conventions.py
TITULO: Convenções de classificação de artefatos por caminho (inventário de curadoria)
DATA: 25/09/2026 15:08
MODIFICADO: 25/09/2026 14:54
VERSÃO: 0.1.0
DEPEND: (nenhuma — stdlib apenas; o casamento de padrões é injetado como Matcher)
HISTÓRICO:
    - 25/09/2026 15:08: criação (T015, feature 010) — faz test_curation_conventions.py passar
STATUS: DEV
"""

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum

from praxisforge.domain.curation_artifact import ArtifactKind
from praxisforge.domain.errors import ConventionsError

Matcher = Callable[[str, str], bool]
"""Casa `(pattern, caminho relativo)`; a Infrastructure fornece a semântica gitignore."""


class RuleUnit(Enum):
    """Unidade que a regra transforma em artefato."""

    FILE = "file"
    DIRECTORY = "directory"


@dataclass(frozen=True)
class ConventionRule:
    """
    Uma regra `padrão de caminho → tipo`.

    :param kind: tipo atribuído (nunca `unknown`, que é o fallback).
    :param pattern: glob relativo à pasta (semântica gitignore).
    :param unit: FILE casa o arquivo; DIRECTORY casa o diretório, que vira um artefato só.
    :param marker: arquivo que precisa existir no diretório (só para DIRECTORY).
    :raises ConventionsError: regra fora das invariantes.
    """

    kind: ArtifactKind
    pattern: str
    unit: RuleUnit
    marker: str | None = None

    def __post_init__(self) -> None:
        if self.kind is ArtifactKind.UNKNOWN:
            raise ConventionsError("'unknown' é o fallback e não pode ser regra")
        if not self.pattern.strip():
            raise ConventionsError("pattern vazio")
        if self.marker is not None:
            if self.unit is not RuleUnit.DIRECTORY:
                raise ConventionsError(f"marker só vale para unit=directory ({self.pattern})")
            if not self.marker or "/" in self.marker:
                raise ConventionsError(f"marker deve ser um nome de arquivo ({self.pattern})")

    def as_dict(self) -> dict[str, str]:
        """
        Forma canônica (base da versão das convenções).

        :return: campos serializados, sem `marker` quando ausente.
        :rtype: dict[str, str]
        """
        dados = {"kind": self.kind.value, "pattern": self.pattern, "unit": self.unit.value}
        if self.marker is not None:
            dados["marker"] = self.marker
        return dados


class Conventions:
    """
    Lista ordenada de regras (ordem = prioridade) e sua versão (SHA-256 canônico).

    :param rules: regras, ao menos uma.
    :type rules: Sequence[ConventionRule]
    :param matcher: função que casa um pattern com um caminho relativo.
    :type matcher: Matcher
    :raises ConventionsError: sem regras.
    """

    def __init__(self, rules: Sequence[ConventionRule], matcher: Matcher) -> None:
        if not rules:
            raise ConventionsError("nenhuma regra definida")
        self._rules = tuple(rules)
        self._matcher = matcher
        canonico = json.dumps([r.as_dict() for r in self._rules], sort_keys=True)
        self._version = hashlib.sha256(canonico.encode("utf-8")).hexdigest()

    @property
    def version(self) -> str:
        """Versão das convenções: muda quando qualquer regra ou a ordem muda (FR-016)."""
        return self._version

    def classify_directory(self, rel_dir: str, names: frozenset[str]) -> ArtifactKind | None:
        """
        Tipo do diretório, se alguma regra DIRECTORY casar (e o marker existir nele).

        :param rel_dir: caminho relativo do diretório.
        :type rel_dir: str
        :param names: nomes dos arquivos diretamente dentro do diretório.
        :type names: frozenset[str]
        :return: tipo da primeira regra que casar, ou None.
        :rtype: ArtifactKind | None
        """
        for rule in self._rules:
            if rule.unit is not RuleUnit.DIRECTORY:
                continue
            if rule.marker is not None and rule.marker not in names:
                continue
            if self._matcher(rule.pattern, rel_dir):
                return rule.kind
        return None

    def classify_file(self, rel_path: str) -> ArtifactKind | None:
        """
        Tipo do arquivo, se alguma regra FILE casar.

        :param rel_path: caminho relativo do arquivo.
        :type rel_path: str
        :return: tipo da primeira regra que casar, ou None.
        :rtype: ArtifactKind | None
        """
        for rule in self._rules:
            if rule.unit is RuleUnit.FILE and self._matcher(rule.pattern, rel_path):
                return rule.kind
        return None
