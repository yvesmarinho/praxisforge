# -*- coding: utf-8 -*-
"""
NOME: test_source_schema_v2.py
TITULO: Testes de contrato — schemas/source-schema-v2.json (feature 006)
DATA: 24/09/2026 10:51
MODIFICADO: 24/09/2026 10:51
VERSÃO: 0.1.0
DEPEND: pytest, jsonschema
HISTÓRICO:
    - 24/09/2026 10:51: criação (T004, feature 006)
STATUS: DEV
"""

import json
from pathlib import Path
from typing import cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

SCHEMA_PATH = Path(__file__).parents[2] / "schemas" / "source-schema-v2.json"


@pytest.fixture
def schema() -> dict[str, object]:
    return cast(dict[str, object], json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def _validar(schema: dict[str, object], documento: dict[str, object]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [error.message for error in validator.iter_errors(documento)]


def _fonte(**campos: object) -> dict[str, object]:
    documento: dict[str, object] = {
        "schema_version": "2",
        "origin": "https://github.com/exemplo/repo",
        "author": "Fulano",
        "date": "2026-09-20",
        "license": "MIT",
        "relevance": "padrões de agentes",
        "status": "active",
        "extract_policy": "verbatim",
        "notice_preserved": True,
    }
    documento.update(campos)
    return documento


def test_schema_eh_um_metaschema_valido(schema: dict[str, object]) -> None:
    """O schema publicado é um Draft 2020-12 válido."""
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:  # pragma: no cover
        pytest.fail(f"schema inválido: {error}")


def test_fonte_valida_nao_tem_erros(schema: dict[str, object]) -> None:
    """Fonte v2 completa passa."""
    assert _validar(schema, _fonte()) == []


def test_link_sem_author_passa_na_forma(schema: dict[str, object]) -> None:
    """author é opcional na forma; exigência condicional fica no domínio."""
    documento = _fonte(extract_policy="link")
    del documento["author"]
    del documento["notice_preserved"]
    assert _validar(schema, documento) == []


@pytest.mark.parametrize("campo", ["schema_version", "extract_policy", "license", "origin"])
def test_campo_obrigatorio_ausente_eh_rejeitado(schema: dict[str, object], campo: str) -> None:
    """Campos obrigatórios da v2 (FR-001)."""
    documento = _fonte()
    del documento[campo]
    assert _validar(schema, documento) != []


@pytest.mark.parametrize(
    "campos",
    [
        {"schema_version": "1"},
        {"extract_allowed": True},
        {"extract_policy": "full"},
        {"extract_scope": "tudo"},
        {"notice_preserved": "sim"},
        {"modified": "nao"},
        {"author": ""},
    ],
)
def test_valores_invalidos_sao_rejeitados(
    schema: dict[str, object], campos: dict[str, object]
) -> None:
    """Versão, campo antigo, enums e tipos (FR-001, FR-014)."""
    assert _validar(schema, _fonte(**campos)) != []


def test_unknown_exige_pending(schema: dict[str, object]) -> None:
    """Licença unknown com status active é rejeitada."""
    assert _validar(schema, _fonte(license="unknown", extract_policy="link")) != []


def test_pending_exige_link(schema: dict[str, object]) -> None:
    """status pending com política diferente de link é rejeitado (FR-006)."""
    assert _validar(schema, _fonte(status="pending", extract_policy="summary")) != []
    assert _validar(schema, _fonte(status="pending", extract_policy="link")) == []


def test_documento_v1_eh_rejeitado(schema: dict[str, object]) -> None:
    """Frontmatter no formato v1 não passa na v2 (FR-014)."""
    documento_v1 = {
        "schema_version": "1",
        "origin": "https://github.com/exemplo/repo",
        "date": "2026-09-20",
        "license": "MIT",
        "relevance": "x",
        "status": "active",
        "extract_allowed": True,
    }
    assert _validar(schema, documento_v1) != []
