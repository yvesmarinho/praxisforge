# -*- coding: utf-8 -*-
"""
NOME: test_schemas_match_contracts.py
TITULO: Testes de contrato — schemas/ idênticos aos rascunhos em specs/.../contracts/
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:48
VERSÃO: 0.1.0
DEPEND: pytest
HISTÓRICO:
    - 22/09/2026 09:45: criação (T012)
STATUS: DEV
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
RUNTIME_DIR = ROOT / "schemas"
DRAFT_DIR = ROOT / "specs" / "001-registro-pastas-curadoria" / "contracts"


def _sem_meta(documento: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in documento.items() if key != "_meta"}


@pytest.mark.parametrize("nome", ["folders-schema-v1.json", "source-schema-v1.json"])
def test_schema_runtime_identico_ao_rascunho(nome: str) -> None:
    """schemas/<nome> é idêntico (ignorando _meta) ao rascunho em contracts/."""
    runtime = json.loads((RUNTIME_DIR / nome).read_text(encoding="utf-8"))
    rascunho = json.loads((DRAFT_DIR / nome).read_text(encoding="utf-8"))
    assert _sem_meta(runtime) == _sem_meta(rascunho)
