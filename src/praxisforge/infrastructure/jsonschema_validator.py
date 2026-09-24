# -*- coding: utf-8 -*-
"""
NOME: jsonschema_validator.py
TITULO: Adapter do ContractValidator — validação via jsonschema (Draft 2020-12)
DATA: 22/09/2026 09:45
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: jsonschema, praxisforge.application.ports, praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 09:45: criação (T024) — faz tests/integration/test_jsonschema_validator.py passar
    - 24/09/2026 16:54: schema_version só é exigido quando o schema o declara (T017, feature 008)
STATUS: DEV
"""

import json
import logging
from collections.abc import Mapping
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from praxisforge.application.ports import ContractValidator
from praxisforge.domain.errors import (
    ContractValidationError,
    PraxisForgeError,
    UnsupportedSchemaVersionError,
    Violation,
)

_SUPPORTED_SCHEMA_VERSIONS = ("1", "2")

logger = logging.getLogger(__name__)


class SchemaNotFoundError(PraxisForgeError):
    """O schema nomeado não existe ou está ilegível em `schemas/`."""

    def __init__(self, schema_name: str) -> None:
        super().__init__(f"schema '{schema_name}' não encontrado ou ilegível")


class JsonSchemaContractValidator(ContractValidator):
    """
    Adapter que valida documentos contra os contratos JSON Schema em `schemas/`.

    :param schemas_dir: diretório onde os arquivos `<schema_name>.json` residem.
    :type schemas_dir: Path
    """

    def __init__(self, schemas_dir: Path) -> None:
        self._schemas_dir = schemas_dir

    def _load_schema(self, schema_name: str) -> dict[str, object]:
        path = self._schemas_dir / f"{schema_name}.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
        except (OSError, json.JSONDecodeError) as error:
            raise SchemaNotFoundError(schema_name) from error

    def validate(self, document: Mapping[str, object], schema_name: str) -> None:
        """Ver ContractValidator.validate."""
        schema = self._load_schema(schema_name)
        propriedades = schema.get("properties")
        # Schemas versionados pelo nome (ex.: skill-frontmatter-v1) não declaram schema_version
        if isinstance(propriedades, dict) and "schema_version" in propriedades:
            version = document.get("schema_version")
            if version not in _SUPPORTED_SCHEMA_VERSIONS:
                raise UnsupportedSchemaVersionError(
                    found=version if isinstance(version, str) else None,
                    supported=_SUPPORTED_SCHEMA_VERSIONS,
                )
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(
            validator.iter_errors(document), key=lambda e: ".".join(str(p) for p in e.path)
        )
        if errors:
            violations = [
                Violation(
                    field=".".join(str(p) for p in error.path) or "(raiz)",
                    reason=error.message,
                )
                for error in errors
            ]
            raise ContractValidationError(violations)
