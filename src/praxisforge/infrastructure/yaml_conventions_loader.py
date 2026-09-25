# -*- coding: utf-8 -*-
"""
NOME: yaml_conventions_loader.py
TITULO: Adapter ConventionsSource — convenções de curadoria em YAML junto do registro
DATA: 25/09/2026 15:14
MODIFICADO: 25/09/2026 14:55
VERSÃO: 0.1.0
DEPEND: pyyaml, pathspec, praxisforge.application.ports
HISTÓRICO:
    - 25/09/2026 15:14: criação (T016, feature 010) — faz test_yaml_conventions_loader.py passar
STATUS: DEV
"""

from functools import lru_cache
from pathlib import Path

import pathspec
import yaml

from praxisforge.application.ports import ContractValidator, ConventionsSource
from praxisforge.domain.curation_artifact import ArtifactKind
from praxisforge.domain.curation_conventions import ConventionRule, Conventions, RuleUnit
from praxisforge.domain.errors import (
    ContractValidationError,
    ConventionsError,
    ConventionsMissingError,
    PraxisForgeError,
)

CONVENTIONS_FILE = "curation-conventions.yaml"
_SCHEMA = "curation-conventions-schema-v1"


@lru_cache(maxsize=256)
def _spec(pattern: str) -> "pathspec.PathSpec[pathspec.Pattern]":
    return pathspec.PathSpec.from_lines("gitignore", [pattern])


def gitignore_match(pattern: str, path: str) -> bool:
    """
    Casa um padrão com semântica gitignore (Matcher injetado no domínio).

    :Example:

    >>> gitignore_match("**/skills/*", ".claude/skills/x")
    True
    """
    return bool(_spec(pattern).match_file(path))


class YamlConventionsSource(ConventionsSource):
    """
    Lê `<dir do registro>/curation-conventions.yaml` e valida pelo schema v1.

    :param path: caminho do arquivo de convenções.
    :type path: Path
    :param validator: validador de contratos JSON Schema.
    :type validator: ContractValidator
    """

    def __init__(self, path: Path, validator: ContractValidator) -> None:
        self._path = path
        self._validator = validator

    def load(self) -> Conventions:
        """Ver ConventionsSource.load."""
        if not self._path.exists():
            raise ConventionsMissingError(str(self._path))
        try:
            documento = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
            raise ConventionsError(f"arquivo ilegível ({type(error).__name__})") from error
        if not isinstance(documento, dict):
            raise ConventionsError("o arquivo deve ser um mapeamento YAML")
        try:
            self._validator.validate(documento, _SCHEMA)
        except ContractValidationError as error:
            raise ConventionsError(str(error)) from error
        except PraxisForgeError as error:  # versão de schema não suportada
            raise ConventionsError(str(error)) from error
        regras = [
            ConventionRule(
                kind=ArtifactKind.from_str(regra["kind"]),
                pattern=regra["pattern"],
                unit=RuleUnit(regra["unit"]),
                marker=regra.get("marker"),
            )
            for regra in documento["rules"]
        ]
        return Conventions(regras, gitignore_match)
