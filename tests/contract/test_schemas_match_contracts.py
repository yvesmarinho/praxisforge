# -*- coding: utf-8 -*-
"""
NOME: test_schemas_match_contracts.py
TITULO: Testes de contrato — schemas/ idênticos aos rascunhos em specs/.../contracts/
DATA: 22/09/2026 09:45
MODIFICADO: 24/09/2026 10:51
VERSÃO: 0.1.0
DEPEND: pytest
HISTÓRICO:
    - 22/09/2026 09:45: criação (T012)
    - 24/09/2026 10:51: source-schema-v2 comparado com o rascunho da feature 006 (T005)
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


def test_source_schema_v2_identico_ao_rascunho_da_006() -> None:
    """schemas/source-schema-v2.json é idêntico (ignorando _meta) ao contrato da feature 006."""
    rascunho_dir = ROOT / "specs" / "006-politica-extracao-licenca" / "contracts"
    runtime = json.loads((RUNTIME_DIR / "source-schema-v2.json").read_text(encoding="utf-8"))
    rascunho = json.loads((rascunho_dir / "source-schema-v2.json").read_text(encoding="utf-8"))
    assert _sem_meta(runtime) == _sem_meta(rascunho)
