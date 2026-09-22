# -*- coding: utf-8 -*-
"""
NOME: test_source_schema.py
TITULO: Testes de contrato — schemas/source-schema-v1.json
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:52
VERSÃO: 0.1.0
DEPEND: pytest, jsonschema
HISTÓRICO:
    - 22/09/2026 09:45: criação (T011)
STATUS: DEV
"""

import json
from pathlib import Path
from typing import cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

SCHEMA_PATH = Path(__file__).parents[2] / "schemas" / "source-schema-v1.json"


@pytest.fixture
def schema() -> dict[str, object]:
    return cast(dict[str, object], json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_schema_eh_um_metaschema_valido(schema: dict[str, object]) -> None:
    """O schema publicado é um Draft 2020-12 válido."""
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:  # pragma: no cover
        pytest.fail(f"schema inválido: {error}")


def _validar(schema: dict[str, object], documento: dict[str, object]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [error.message for error in validator.iter_errors(documento)]


def test_fonte_valida_nao_tem_erros(schema: dict[str, object]) -> None:
    """Uma fonte válida não levanta violações."""
    documento = {
        "schema_version": "1",
        "origin": "https://github.com/exemplo/repo",
        "date": "2026-09-21",
        "license": "MIT",
        "relevance": "referência principal sobre o tema",
        "status": "active",
        "extract_allowed": True,
    }
    assert _validar(schema, documento) == []


@pytest.mark.parametrize(
    "documento",
    [
        {"origin": "x"},  # campos obrigatórios ausentes
        {
            "schema_version": "1",
            "origin": "/home/user/repo",
            "date": "2026-09-21",
            "license": "MIT",
            "relevance": "x",
            "status": "active",
            "extract_allowed": True,
        },  # origin com caminho absoluto
        {
            "schema_version": "1",
            "origin": "https://x",
            "date": "2026-09-21",
            "license": "unknown",
            "relevance": "x",
            "status": "active",
            "extract_allowed": True,
        },  # unknown + status active
        {
            "schema_version": "1",
            "origin": "https://x",
            "date": "2026-09-21",
            "license": "MIT",
            "relevance": "x",
            "status": "pending",
            "extract_allowed": True,
        },  # pending + extract_allowed true
        {
            "schema_version": "1",
            "origin": "https://x",
            "date": "amanha",
            "license": "MIT",
            "relevance": "x",
            "status": "active",
            "extract_allowed": True,
        },  # data inválida
    ],
)
def test_documentos_invalidos_sao_rejeitados(
    schema: dict[str, object], documento: dict[str, object]
) -> None:
    """Cada variação inválida da spec é rejeitada pelo schema."""
    assert _validar(schema, documento) != []
