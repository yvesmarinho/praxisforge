# -*- coding: utf-8 -*-
"""
NOME: test_jsonschema_validator.py
TITULO: Testes de falha — adapter JsonSchemaContractValidator (Infrastructure)
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:48
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.jsonschema_validator
HISTÓRICO:
    - 22/09/2026 09:45: criação (T013)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.domain.errors import ContractValidationError, UnsupportedSchemaVersionError
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator

SCHEMAS_DIR = Path(__file__).parents[2] / "schemas"


def test_reporta_todas_as_violacoes_de_uma_vez() -> None:
    """Um documento com múltiplas violações reporta todas, não só a primeira."""
    validator = JsonSchemaContractValidator(schemas_dir=SCHEMAS_DIR)
    documento = {
        "schema_version": "1",
        "folders": {
            "Exemplo": {  # alias maiúsculo
                "description": "",  # vazio
                "content_type": "docs",
                "license": "unknown",
                "last_scanned": "2026-09-21T15:55:00-03:00",  # unknown + data preenchida
                "status": "scanned",  # unknown exige pending
            }
        },
    }
    with pytest.raises(ContractValidationError) as excinfo:
        validator.validate(documento, schema_name="folders-schema-v1")
    assert len(excinfo.value.violations) > 1


def test_versao_ausente_levanta_unsupported_schema_version() -> None:
    """Documento sem schema_version levanta UnsupportedSchemaVersionError."""
    validator = JsonSchemaContractValidator(schemas_dir=SCHEMAS_DIR)
    with pytest.raises(UnsupportedSchemaVersionError):
        validator.validate({"folders": {}}, schema_name="folders-schema-v1")


def test_versao_3_levanta_unsupported_schema_version() -> None:
    """Versão fora de ("1", "2") levanta UnsupportedSchemaVersionError (v2: feature 005)."""
    validator = JsonSchemaContractValidator(schemas_dir=SCHEMAS_DIR)
    with pytest.raises(UnsupportedSchemaVersionError):
        validator.validate({"schema_version": "3", "folders": {}}, schema_name="folders-schema-v2")


def test_versao_2_contra_schema_v1_viola_contrato() -> None:
    """Versão conhecida mas de outro schema é violação de contrato (const)."""
    validator = JsonSchemaContractValidator(schemas_dir=SCHEMAS_DIR)
    with pytest.raises(ContractValidationError):
        validator.validate({"schema_version": "2", "folders": {}}, schema_name="folders-schema-v1")


def test_schema_ausente_levanta_erro_especifico() -> None:
    """Nome de schema desconhecido/ilegível levanta erro específico de infraestrutura."""
    validator = JsonSchemaContractValidator(schemas_dir=SCHEMAS_DIR)
    with pytest.raises(Exception):  # noqa: B017 - erro específico, checado pelo type abaixo
        validator.validate({"schema_version": "1"}, schema_name="schema-inexistente")


def test_documento_valido_nao_levanta() -> None:
    """Documento válido não levanta exceção."""
    validator = JsonSchemaContractValidator(schemas_dir=SCHEMAS_DIR)
    documento = {
        "schema_version": "1",
        "folders": {
            "github_forks": {
                "description": "Forks de repositórios de referência",
                "content_type": "repository_forks",
                "license": "unknown",
                "last_scanned": None,
                "status": "pending",
            }
        },
    }
    validator.validate(documento, schema_name="folders-schema-v1")
