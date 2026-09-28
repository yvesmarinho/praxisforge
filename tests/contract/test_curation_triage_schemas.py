# -*- coding: utf-8 -*-
"""
NOME: test_curation_triage_schemas.py
TITULO: Testes de contrato — respostas do modelo, rascunho em staging e estado v2 (feature 011)
DATA: 28/09/2026 15:51
MODIFICADO: 28/09/2026 15:51
VERSÃO: 0.1.0
DEPEND: pytest, jsonschema
HISTÓRICO:
    - 28/09/2026 15:51: criação (T005, feature 011)
STATUS: DEV
"""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).parents[2]
SHA = "a" * 64
DID = "0123456789abcdef"


def _valido(documento: dict[str, Any], nome: str) -> bool:
    schema = json.loads((ROOT / "schemas" / f"{nome}.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(documento)


def _triagem(**campos: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "verdict": "gap",
        "justification": "ideia nova",
        "covered_by": [],
        "merge_target": None,
        "suggested_kind": None,
        "ideas_summary": None,
    }
    return base | campos


def _rascunho(**campos: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "kind": "skill",
        "name": "revisao-de-contratos",
        "description": "Revisa contratos.",
        "body": "# Corpo\n",
    }
    return base | campos


# --- resposta de triagem -----------------------------------------------------------


def test_triagem_validas() -> None:
    assert _valido(_triagem(), "curation-triage-response-v1")
    assert _valido(
        _triagem(verdict="covered", covered_by=["skill/diretrizes-codificacao"]),
        "curation-triage-response-v1",
    )
    assert _valido(
        _triagem(merge_target={"kind": "draft", "ref": DID}), "curation-triage-response-v1"
    )
    assert _valido(
        _triagem(merge_target={"kind": "library", "ref": "rule/estilo"}),
        "curation-triage-response-v1",
    )


@pytest.mark.parametrize(
    "campos",
    [
        {"verdict": "talvez"},
        {"justification": ""},
        {"justification": "   "},
        {"justification": "x" * 2001},
        {"verdict": "covered", "covered_by": []},
        {"verdict": "gap", "covered_by": ["skill/a-b"]},
        {"verdict": "covered", "covered_by": ["skill/a", "skill/b", "skill/c", "skill/d"]},
        {"verdict": "covered", "covered_by": ["../../etc/passwd"]},
        {
            "verdict": "covered",
            "covered_by": ["skill/a"],
            "merge_target": {"kind": "library", "ref": "skill/a"},
        },
        {"verdict": "out_of_scope", "merge_target": {"kind": "draft", "ref": DID}},
        {"merge_target": {"kind": "draft", "ref": "../../etc"}},
        {"merge_target": {"kind": "library", "ref": "/etc/x"}},
        {"merge_target": {"kind": "outro", "ref": DID}},
        {"suggested_kind": "unknown"},
        {"suggested_kind": "project_instruction"},
        {"ideas_summary": ""},
        {"ideas_summary": "x" * 4001},
        {"extra": 1},
    ],
)
def test_triagem_invalida(campos: dict[str, Any]) -> None:
    assert not _valido(_triagem(**campos), "curation-triage-response-v1")


def test_triagem_sem_campo_obrigatorio() -> None:
    documento = _triagem()
    del documento["ideas_summary"]
    assert not _valido(documento, "curation-triage-response-v1")


# --- resposta de rascunho e do juiz ------------------------------------------------


@pytest.mark.parametrize(
    "campos",
    [
        {"name": "Revisao_Contratos"},
        {"name": "ab"},
        {"name": "a" * 65},
        {"kind": "project_instruction"},
        {"kind": "unknown"},
        {"description": ""},
        {"description": "x" * 1025},
        {"body": "x" * 65537},
        {"body": " "},
        {"path": "/etc/x"},
    ],
)
def test_rascunho_invalido(campos: dict[str, Any]) -> None:
    assert _valido(_rascunho(), "curation-draft-response-v1")
    assert not _valido(_rascunho(**campos), "curation-draft-response-v1")


def test_juiz() -> None:
    assert _valido({"is_derivative": False, "justification": "ok"}, "curation-judge-response-v1")
    assert not _valido(
        {"is_derivative": "não", "justification": "ok"}, "curation-judge-response-v1"
    )
    assert not _valido({"is_derivative": True}, "curation-judge-response-v1")


# --- estado v2 e rascunho em staging ------------------------------------------------


def _estado(triage: Any) -> dict[str, Any]:
    return {
        "schema_version": "2",
        "alias": "demo_a",
        "conventions_version": SHA,
        "updated_at": "2026-09-28T15:00:00-03:00",
        "artifacts": {
            "skills/x": {
                "kind": "skill",
                "sha256": SHA,
                "stage": "triaged",
                "verdict": None,
                "last_error": None,
                "attempts": 0,
                "triage": triage,
            }
        },
    }


def _triage_gravada(**campos: Any) -> dict[str, Any]:
    return (
        _triagem(
            prompt_fingerprint=SHA,
            model="claude-haiku-4-5",
            cost_usd=0.01,
            triaged_at="2026-09-28T15:00:00-03:00",
            draft_id=None,
        )
        | campos
    )


def test_estado_v2() -> None:
    assert _valido(_estado(None), "curation-state-schema-v2")
    assert _valido(_estado(_triage_gravada()), "curation-state-schema-v2")
    assert not _valido(_estado(_triage_gravada(draft_id="x")), "curation-state-schema-v2")
    assert not _valido(_estado(_triage_gravada(cost_usd=-1)), "curation-state-schema-v2")
    sem_triage = _estado(None)
    del sem_triage["artifacts"]["skills/x"]["triage"]
    assert not _valido(sem_triage, "curation-state-schema-v2")
    v1 = _estado(None) | {"schema_version": "1"}
    assert not _valido(v1, "curation-state-schema-v2")


def _draft(**campos: Any) -> dict[str, Any]:
    check = {
        "structural_score": 0.2,
        "threshold": 0.7,
        "judge_is_derivative": False,
        "judge_justification": "ok",
        "flagged": False,
    }
    base: dict[str, Any] = {
        "schema_version": "1",
        "draft_id": DID,
        "proposal": _rascunho(),
        "origins": [{"alias": "demo_a", "path": "skills/x", "sha256": SHA}],
        "checks": [check],
        "similarity_alert": False,
        "merge_target": None,
        "prompt_fingerprint": SHA,
        "model": "claude-sonnet-5",
        "cost_usd": None,
        "updated_at": "2026-09-28T15:00:00-03:00",
    }
    return base | campos


@pytest.mark.parametrize(
    "campos",
    [
        {"origins": []},
        {"origins": [{"alias": "demo_a", "path": "/abs", "sha256": SHA}]},
        {"origins": [{"alias": "demo_a", "path": "../x", "sha256": SHA}]},
        {"checks": []},
        {"checks": [{}]},
        {"draft_id": "../x"},
        {"schema_version": "2"},
    ],
)
def test_rascunho_em_staging_invalido(campos: dict[str, Any]) -> None:
    assert _valido(_draft(), "curation-draft-schema-v1")
    assert not _valido(_draft(**campos), "curation-draft-schema-v1")


_PALAVRAS_POR_TIPO = {
    "array": {"minItems", "maxItems", "items", "uniqueItems"},
    "string": {"minLength", "maxLength", "pattern"},
    "object": {"properties", "required", "additionalProperties"},
    "number": {"minimum", "maximum", "exclusiveMinimum"},
}


def _sem_tipo(no: Any, caminho: str = "#") -> list[str]:
    """Palavras-chave de um tipo sem `type` no mesmo nó (regra strictTypes do CLI `claude`)."""
    problemas: list[str] = []
    if isinstance(no, dict):
        tipo = no.get("type")
        tipos = set(tipo) if isinstance(tipo, list) else {tipo}
        if "integer" in tipos:
            tipos.add("number")
        for esperado, palavras in _PALAVRAS_POR_TIPO.items():
            if palavras & set(no) and esperado not in tipos:
                problemas.append(f"{caminho}: {sorted(palavras & set(no))} sem type {esperado}")
        for chave, valor in no.items():
            problemas += _sem_tipo(valor, f"{caminho}/{chave}")
    elif isinstance(no, list):
        for i, valor in enumerate(no):
            problemas += _sem_tipo(valor, f"{caminho}/{i}")
    return problemas


@pytest.mark.parametrize(
    "nome",
    ["curation-triage-response-v1", "curation-draft-response-v1", "curation-judge-response-v1"],
)
def test_schemas_de_resposta_aceitos_pelo_modo_estrito_do_cli(nome: str) -> None:
    """Achado da triagem real (28/09/2026): o CLI recusa minItems sem type (strictTypes)."""
    schema = json.loads((ROOT / "schemas" / f"{nome}.json").read_text(encoding="utf-8"))
    assert _sem_tipo(schema) == []
