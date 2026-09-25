# -*- coding: utf-8 -*-
"""
NOME: test_curation_schemas.py
TITULO: Testes de contrato — convenções, manifesto e estado da curadoria (feature 010)
DATA: 25/09/2026 14:52
MODIFICADO: 25/09/2026 14:50
VERSÃO: 0.1.0
DEPEND: pytest, jsonschema, pyyaml
HISTÓRICO:
    - 25/09/2026 14:52: criação (T005, feature 010)
STATUS: DEV
"""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).parents[2]
CONTRACTS = ROOT / "specs" / "010-inventario-curadoria" / "contracts"
SHA = "a" * 64

_NOMES = (
    "curation-conventions-schema-v1.json",
    "curation-manifest-schema-v1.json",
    "curation-state-schema-v1.json",
)


def _schema(nome: str) -> dict[str, Any]:
    return json.loads((ROOT / "schemas" / nome).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _erros(documento: dict[str, Any], nome: str) -> list[str]:
    validator = Draft202012Validator(_schema(nome), format_checker=FormatChecker())
    return [erro.message for erro in validator.iter_errors(documento)]


def _manifesto(**extra: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema_version": "1",
        "alias": "agent_skills",
        "conventions_version": SHA,
        "artifacts": [{"path": "skills/x", "kind": "skill", "size": 3, "sha256": SHA, "files": 2}],
        "excluded": [{"path": "node_modules", "reason": "fixed_dir", "is_dir": True}],
    }
    doc.update(extra)
    return doc


def _estado(**artefato: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "kind": "skill",
        "sha256": SHA,
        "stage": "pending",
        "verdict": None,
        "last_error": None,
        "attempts": 0,
    }
    base.update(artefato)
    return {
        "schema_version": "1",
        "alias": "agent_skills",
        "conventions_version": SHA,
        "updated_at": "2026-09-25T14:52:00-03:00",
        "artifacts": {"skills/x": base},
    }


@pytest.mark.parametrize("nome", _NOMES)
def test_schema_runtime_identico_ao_contrato(nome: str) -> None:
    """schemas/ é cópia do contrato da feature (ignorando _meta)."""
    runtime = {k: v for k, v in _schema(nome).items() if k != "_meta"}
    contrato = json.loads((CONTRACTS / nome).read_text(encoding="utf-8"))
    assert runtime == {k: v for k, v in contrato.items() if k != "_meta"}


def test_exemplo_de_convencoes_valido() -> None:
    """src/data/curation-conventions.example.yaml respeita o schema (FR-004)."""
    doc = yaml.safe_load((ROOT / "src/data/curation-conventions.example.yaml").read_text("utf-8"))
    assert _erros(doc, "curation-conventions-schema-v1.json") == []


@pytest.mark.parametrize(
    "regra",
    [
        {"kind": "unknown", "pattern": "*.md", "unit": "file"},
        {"kind": "skill", "pattern": "", "unit": "file"},
        {"kind": "skill", "pattern": "x", "unit": "tree"},
        {"kind": "skill", "pattern": "x", "unit": "directory", "marker": "a/b"},
        {"kind": "skill", "pattern": "x", "unit": "file", "extra": 1},
    ],
)
def test_convencoes_rejeitam_regra_invalida(regra: dict[str, Any]) -> None:
    """kind unknown, pattern vazio, unit/marker inválidos e campo extra são recusados."""
    doc = {"schema_version": "1", "rules": [regra]}
    assert _erros(doc, "curation-conventions-schema-v1.json") != []


def test_convencoes_sem_regras_recusadas() -> None:
    """Lista de regras vazia é recusada."""
    assert _erros({"schema_version": "1", "rules": []}, "curation-conventions-schema-v1.json")


def test_manifesto_valido() -> None:
    assert _erros(_manifesto(), "curation-manifest-schema-v1.json") == []


@pytest.mark.parametrize(
    "extra",
    [
        {"schema_version": "9"},
        {"alias": "Agent-Skills"},
        {"conventions_version": "xyz"},
        {"artifacts": [{"path": "/abs", "kind": "skill", "size": 1, "sha256": SHA, "files": 1}]},
        {"artifacts": [{"path": "a/../b", "kind": "skill", "size": 1, "sha256": SHA, "files": 1}]},
        {"artifacts": [{"path": "a", "kind": "outro", "size": 1, "sha256": SHA, "files": 1}]},
        {"artifacts": [{"path": "a", "kind": "skill", "size": -1, "sha256": SHA, "files": 1}]},
        {"artifacts": [{"path": "a", "kind": "skill", "size": 1, "sha256": SHA, "files": 0}]},
        {"excluded": [{"path": "a", "reason": "outro", "is_dir": False}]},
        {"generated_at": "2026-09-25"},
    ],
)
def test_manifesto_invalido(extra: dict[str, Any]) -> None:
    """Versão, alias, sha, path absoluto/`..`, enums, limites e campo extra (FR-012)."""
    assert _erros(_manifesto(**extra), "curation-manifest-schema-v1.json") != []


def test_estado_valido() -> None:
    assert _erros(_estado(), "curation-state-schema-v1.json") == []


@pytest.mark.parametrize(
    "artefato",
    [
        {"stage": "ignorado"},
        {"attempts": -1},
        {"sha256": "curto"},
        {"kind": "outro"},
        {"extra": True},
    ],
)
def test_estado_invalido(artefato: dict[str, Any]) -> None:
    assert _erros(_estado(**artefato), "curation-state-schema-v1.json") != []


def test_estado_sem_data_recusado() -> None:
    doc = _estado()
    doc["updated_at"] = "ontem"
    assert _erros(doc, "curation-state-schema-v1.json") != []
