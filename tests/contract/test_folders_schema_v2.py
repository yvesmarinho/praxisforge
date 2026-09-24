# -*- coding: utf-8 -*-
"""
NOME: test_folders_schema_v2.py
TITULO: Testes de contrato — folders-schema-v2.json (path obrigatório)
DATA: 23/09/2026 16:47
MODIFICADO: 24/09/2026 14:39
VERSÃO: 0.1.0
DEPEND: pytest, jsonschema
HISTÓRICO:
    - 23/09/2026 16:47: criação (T002, feature 005-caminho-absoluto-registro)
    - 24/09/2026 14:39: registro versionado passa a ser o exemplo (feature 007)
STATUS: DEV
"""

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from praxisforge.infrastructure.yaml_loader import NoTimestampSafeLoader

_RAIZ = Path(__file__).parents[2]
_SCHEMA_V2 = _RAIZ / "schemas" / "folders-schema-v2.json"


@pytest.fixture
def schema() -> dict[str, object]:
    return cast(dict[str, object], json.loads(_SCHEMA_V2.read_text(encoding="utf-8")))


def _validar(schema: dict[str, object], documento: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [error.message for error in validator.iter_errors(documento)]


def _doc(**pasta: object) -> dict[str, Any]:
    entrada: dict[str, object] = {
        "description": "Repositório",
        "content_type": "repository_forks",
        "license": "MIT",
        "last_scanned": None,
        "status": "not_scanned",
        "path": "/srv/pastas/repo",
    }
    entrada.update(pasta)
    return {"schema_version": "2", "folders": {"repo": entrada}}


def test_schema_v2_eh_draft_2020_12_valido(schema: dict[str, object]) -> None:
    """O schema publicado é um Draft 2020-12 válido."""
    Draft202012Validator.check_schema(schema)


def test_documento_v2_valido(schema: dict[str, object]) -> None:
    """Pasta com path absoluto valida."""
    assert _validar(schema, _doc()) == []


@pytest.mark.parametrize("valor", ["relativo/repo", "", "~/repo", 42, None])
def test_path_invalido_eh_rejeitado(schema: dict[str, object], valor: object) -> None:
    """path relativo, vazio, com ~, não-string ou nulo é rejeitado (FR-001)."""
    assert _validar(schema, _doc(path=valor)) != []


def test_path_ausente_eh_rejeitado(schema: dict[str, object]) -> None:
    """path é obrigatório em toda pasta (FR-001)."""
    documento = _doc()
    del documento["folders"]["repo"]["path"]
    assert _validar(schema, documento) != []


def test_schema_version_1_eh_rejeitado(schema: dict[str, object]) -> None:
    """Documento v1 não valida contra a v2 (FR-009)."""
    documento = _doc()
    documento["schema_version"] = "1"
    assert _validar(schema, documento) != []


def test_regras_da_v1_continuam(schema: dict[str, object]) -> None:
    """Licença unknown exige pending/ignore; not_scanned exige last_scanned nulo; hash validado."""
    assert _validar(schema, _doc(license="unknown", status="scanned")) != []
    assert _validar(schema, _doc(last_scanned="2026-09-01T10:00:00-03:00")) != []
    assert _validar(schema, _doc(last_curated_commit="XYZ")) != []
    assert _validar(schema, _doc(last_curated_commit="a" * 40)) == []


def test_registro_versionado_atual_valida_na_v2(schema: dict[str, object]) -> None:
    """O registro versionado (exemplo, desde a feature 007) está no formato v2 (T036)."""
    texto = (_RAIZ / "src" / "data" / "folders.example.yaml").read_text("utf-8")
    documento = yaml.load(texto, Loader=NoTimestampSafeLoader)  # noqa: S506 # nosec B506
    assert _validar(schema, documento) == []
