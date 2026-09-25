# -*- coding: utf-8 -*-
"""
NOME: test_library_schemas.py
TITULO: Testes de contrato — schemas do acervo library/ e source-schema-v3 (feature 009)
DATA: 25/09/2026 12:58
MODIFICADO: 25/09/2026 12:58
VERSÃO: 0.1.0
DEPEND: pytest, jsonschema
HISTÓRICO:
    - 25/09/2026 12:58: criação (T008, feature 009)
STATUS: DEV
"""

import json
from pathlib import Path
from typing import cast

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).parents[2]
CONTRATOS = ROOT / "specs" / "009-acervo-library" / "contracts"
NOVOS = (
    "command-frontmatter-v1.json",
    "agent-frontmatter-v1.json",
    "rule-frontmatter-v1.json",
    "hook-frontmatter-v1.json",
    "reference-frontmatter-v1.json",
    "library-publication-v1.json",
    "source-schema-v3.json",
    "skill-frontmatter-v1.json",
)
META = {"version": "1.0.0", "sources": ["guia-a"], "authored": False}


def _carregar(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _sem_meta(documento: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in documento.items() if key != "_meta"}


def _erros(nome: str, documento: dict[str, object]) -> list[str]:
    validator = Draft202012Validator(_carregar(ROOT / "schemas" / nome))
    return [error.message for error in validator.iter_errors(documento)]


@pytest.mark.parametrize("nome", NOVOS)
def test_schema_valido_e_identico_ao_contrato(nome: str) -> None:
    """schemas/<nome> é Draft 2020-12 válido e idêntico (sem _meta) ao contrato da 009."""
    runtime = _carregar(ROOT / "schemas" / nome)
    Draft202012Validator.check_schema(runtime)
    assert _sem_meta(runtime) == _sem_meta(_carregar(CONTRATOS / nome))


VALIDOS: list[tuple[str, dict[str, object]]] = [
    (
        "command-frontmatter-v1.json",
        {"description": "Revisa", "argument-hint": "[x]", "metadata": META},
    ),
    (
        "agent-frontmatter-v1.json",
        {"name": "revisor", "description": "Revisa", "tools": "Read", "metadata": META},
    ),
    ("rule-frontmatter-v1.json", {"description": "Regra", "paths": ["src/**"], "metadata": META}),
    ("rule-frontmatter-v1.json", {"description": "Regra sem paths", "metadata": META}),
    (
        "hook-frontmatter-v1.json",
        {
            "name": "aviso",
            "description": "Avisa",
            "event": "SessionStart",
            "run": ["run.sh"],
            "metadata": META,
        },
    ),
    (
        "hook-frontmatter-v1.json",
        {
            "name": "fmt",
            "description": "Formata",
            "event": "PostToolUse",
            "matcher": "Edit|Write",
            "run": ["fmt.sh"],
            "metadata": META,
        },
    ),
    (
        "reference-frontmatter-v1.json",
        {"name": "checklist-seguranca", "description": "Checklist", "metadata": META},
    ),
    (
        "skill-frontmatter-v1.json",
        {
            "name": "s",
            "description": "d",
            "metadata": {**META, "references": ["checklist-seguranca"], "rewrite_pending": True},
        },
    ),
    (
        "library-publication-v1.json",
        {
            "schema_version": "1",
            "kind": "command",
            "name": "revisar",
            "version": "1.0.0",
            "content_sha256": "a" * 64,
            "source": "library/commands/revisar",
        },
    ),
    (
        "source-schema-v3.json",
        {
            "schema_version": "3",
            "origin": "https://x.io/r",
            "author": "A",
            "date": "2026-09-25",
            "license": "MIT",
            "relevance": "r",
            "status": "active",
        },
    ),
]


@pytest.mark.parametrize(("nome", "documento"), VALIDOS)
def test_documento_valido(nome: str, documento: dict[str, object]) -> None:
    """Exemplos válidos passam sem erro."""
    assert _erros(nome, documento) == []


INVALIDOS: list[tuple[str, str, dict[str, object]]] = [
    ("command sem description", "command-frontmatter-v1.json", {"metadata": META}),
    ("command sem metadata", "command-frontmatter-v1.json", {"description": "d"}),
    (
        "versão não semver",
        "command-frontmatter-v1.json",
        {"description": "d", "metadata": {"version": "1.0"}},
    ),
    (
        "agent com nome inválido",
        "agent-frontmatter-v1.json",
        {"name": "Revisor_X", "description": "d", "metadata": META},
    ),
    ("agent sem name", "agent-frontmatter-v1.json", {"description": "d", "metadata": META}),
    (
        "rule com paths vazio",
        "rule-frontmatter-v1.json",
        {"description": "d", "paths": [], "metadata": META},
    ),
    (
        "hook com evento inválido",
        "hook-frontmatter-v1.json",
        {"name": "h", "description": "d", "event": "OnSave", "run": ["a.sh"], "metadata": META},
    ),
    (
        "hook com run vazio",
        "hook-frontmatter-v1.json",
        {"name": "h", "description": "d", "event": "Stop", "run": [], "metadata": META},
    ),
    (
        "hook sem event",
        "hook-frontmatter-v1.json",
        {"name": "h", "description": "d", "run": ["a.sh"], "metadata": META},
    ),
    ("reference sem name", "reference-frontmatter-v1.json", {"description": "d", "metadata": META}),
    (
        "description longa",
        "reference-frontmatter-v1.json",
        {"name": "r", "description": "x" * 1025, "metadata": META},
    ),
    (
        "rewrite_pending não bool",
        "skill-frontmatter-v1.json",
        {"name": "s", "description": "d", "metadata": {**META, "rewrite_pending": "sim"}},
    ),
    (
        "references repetidas",
        "skill-frontmatter-v1.json",
        {"name": "s", "description": "d", "metadata": {**META, "references": ["a", "a"]}},
    ),
    (
        "marcador com kind hook",
        "library-publication-v1.json",
        {
            "schema_version": "1",
            "kind": "hook",
            "name": "h",
            "version": "1.0.0",
            "content_sha256": "a" * 64,
            "source": "library/hooks/h",
        },
    ),
    (
        "fonte v3 com extract_policy",
        "source-schema-v3.json",
        {
            "schema_version": "3",
            "origin": "o",
            "date": "2026-09-25",
            "license": "MIT",
            "relevance": "r",
            "status": "active",
            "extract_policy": "summary",
        },
    ),
    (
        "fonte v3 sem license",
        "source-schema-v3.json",
        {
            "schema_version": "3",
            "origin": "o",
            "date": "2026-09-25",
            "relevance": "r",
            "status": "active",
        },
    ),
    (
        "fonte declarando v2",
        "source-schema-v3.json",
        {
            "schema_version": "2",
            "origin": "o",
            "date": "2026-09-25",
            "license": "MIT",
            "relevance": "r",
            "status": "active",
        },
    ),
]


@pytest.mark.parametrize(("caso", "nome", "documento"), INVALIDOS, ids=[c[0] for c in INVALIDOS])
def test_documento_invalido(caso: str, nome: str, documento: dict[str, object]) -> None:
    """Exemplos inválidos geram ao menos um erro."""
    assert _erros(nome, documento), caso
