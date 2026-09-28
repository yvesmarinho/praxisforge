# -*- coding: utf-8 -*-
"""
NOME: test_curation_draft.py
TITULO: Testes de falha — rascunho em staging: proposta, origens e alerta (feature 011)
DATA: 28/09/2026 16:15
MODIFICADO: 28/09/2026 16:15
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.curation_draft
HISTÓRICO:
    - 28/09/2026 16:15: criação (T034, feature 011)
STATUS: DEV
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from praxisforge.domain.curation_artifact import ArtifactKind
from praxisforge.domain.curation_draft import Draft, DraftOrigin, DraftProposal, draft_id_for
from praxisforge.domain.curation_triage import MergeTarget
from praxisforge.domain.errors import InvalidTriageError
from praxisforge.domain.structure_similarity import SimilarityCheck

AGORA = datetime(2026, 9, 28, 16, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
SHA = "a" * 64
OK = SimilarityCheck(0.2, 0.7, False, "estrutura própria")
RUIM = SimilarityCheck(0.9, 0.7, False, "mesma estrutura")


def _proposta(**campos: Any) -> DraftProposal:
    base: dict[str, Any] = {
        "kind": ArtifactKind.SKILL,
        "name": "revisao-de-contratos",
        "description": "Revisa contratos.",
        "body": "# Corpo\n",
    }
    return DraftProposal(**(base | campos))


def _rascunho(**campos: Any) -> Draft:
    base: dict[str, Any] = {
        "draft_id": draft_id_for("demo_a", "skills/x"),
        "proposal": _proposta(),
        "origins": (DraftOrigin("demo_a", "skills/x", SHA),),
        "checks": (OK,),
        "merge_target": None,
        "prompt_fingerprint": "f" * 64,
        "model": "claude-sonnet-5",
        "cost_usd": Decimal("0.02"),
        "updated_at": AGORA,
    }
    return Draft(**(base | campos))


def test_draft_id_estavel() -> None:
    a = draft_id_for("demo_a", "skills/x")
    assert a == draft_id_for("demo_a", "skills/x") and len(a) == 16
    assert a != draft_id_for("demo_a", "skills/y")
    assert draft_id_for("ab", "c") != draft_id_for("a", "bc")


@pytest.mark.parametrize(
    "campos",
    [
        {"name": "Nome_Invalido"},
        {"name": "ab"},
        {"kind": ArtifactKind.UNKNOWN},
        {"kind": ArtifactKind.PROJECT_INSTRUCTION},
        {"description": " "},
        {"description": "x" * 1025},
        {"body": ""},
        {"body": "x" * 65537},
    ],
)
def test_proposta_invalida(campos: dict[str, Any]) -> None:
    with pytest.raises(InvalidTriageError):
        _proposta(**campos)


@pytest.mark.parametrize(
    "campos",
    [
        {"origins": ()},
        {"origins": (DraftOrigin("demo_a", "x", SHA), DraftOrigin("demo_a", "x", SHA))},
        {"origins": (DraftOrigin("demo_a", "/abs", SHA),)},
        {"checks": ()},
        {"checks": (OK, OK, OK)},
        {"draft_id": "../x"},
        {"updated_at": datetime(2026, 9, 28, 16, 0)},
        {"merge_target": MergeTarget("draft", "../x")},
        {"cost_usd": Decimal("-1")},
    ],
)
def test_rascunho_invalido(campos: dict[str, Any]) -> None:
    with pytest.raises(InvalidTriageError):
        _rascunho(**campos)


def test_alerta_e_o_ultimo_check() -> None:
    assert not _rascunho().similarity_alert
    assert _rascunho(checks=(RUIM,)).similarity_alert
    assert not _rascunho(checks=(RUIM, OK)).similarity_alert
    assert _rascunho(checks=(OK, RUIM)).similarity_alert


def test_origem_repetida_substitui() -> None:
    base = _rascunho()
    outra = base.with_origin(DraftOrigin("demo_b", "y.md", SHA))
    assert [o.alias for o in outra.origins] == ["demo_a", "demo_b"]
    nova = outra.with_origin(DraftOrigin("demo_a", "skills/x", "b" * 64))
    assert [(o.alias, o.sha256) for o in nova.origins] == [("demo_a", "b" * 64), ("demo_b", SHA)]
