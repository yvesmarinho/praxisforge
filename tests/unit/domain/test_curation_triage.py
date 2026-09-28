# -*- coding: utf-8 -*-
"""
NOME: test_curation_triage.py
TITULO: Testes de falha — veredito de triagem, elegibilidade e transições (feature 011)
DATA: 28/09/2026 15:51
MODIFICADO: 28/09/2026 15:51
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.curation_triage
HISTÓRICO:
    - 28/09/2026 15:51: criação (T006, feature 011)
STATUS: DEV
"""

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from praxisforge.domain.curation_artifact import ArtifactKind, Stage
from praxisforge.domain.curation_state import ArtifactState
from praxisforge.domain.curation_triage import (
    MergeTarget,
    Triage,
    TriageVerdict,
    is_eligible,
    validate_in_context,
    with_draft,
    with_failure,
    with_triage,
)
from praxisforge.domain.errors import InvalidTriageError

AGORA = datetime(2026, 9, 28, 15, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
SHA = "a" * 64
FP = "f" * 64
DID = "0123456789abcdef"


def _triage(**campos: Any) -> Triage:
    base: dict[str, Any] = {
        "verdict": TriageVerdict.GAP,
        "justification": "ideia nova",
        "covered_by": (),
        "merge_target": None,
        "suggested_kind": None,
        "ideas_summary": None,
        "prompt_fingerprint": FP,
        "model": "claude-haiku-4-5",
        "cost_usd": Decimal("0.01"),
        "triaged_at": AGORA,
    }
    return Triage(**(base | campos))


def _estado(stage: Stage, **campos: Any) -> ArtifactState:
    return ArtifactState(ArtifactKind.SKILL, SHA, stage, **campos)


# --- Triage ------------------------------------------------------------------------


def test_verdict_from_str() -> None:
    assert TriageVerdict.from_str("out_of_scope") is TriageVerdict.OUT_OF_SCOPE
    with pytest.raises(Exception, match="talvez"):
        TriageVerdict.from_str("talvez")


@pytest.mark.parametrize(
    ("campos", "motivo"),
    [
        ({"justification": "  "}, "justificativa"),
        ({"verdict": TriageVerdict.COVERED}, "covered"),
        ({"covered_by": ("skill/a",)}, "covered_by"),
        ({"verdict": TriageVerdict.COVERED, "covered_by": ("skill/a",),
          "merge_target": MergeTarget("library", "skill/a")}, "fusão"),
        ({"verdict": TriageVerdict.OUT_OF_SCOPE,
          "merge_target": MergeTarget("draft", DID)}, "fusão"),
        ({"suggested_kind": ArtifactKind.UNKNOWN}, "tipo sugerido"),
        ({"suggested_kind": ArtifactKind.PROJECT_INSTRUCTION}, "tipo sugerido"),
        ({"cost_usd": Decimal("-0.01")}, "custo"),
        ({"triaged_at": datetime(2026, 9, 28, 15, 0)}, "fuso"),
        ({"prompt_fingerprint": "x"}, "impressão digital"),
        ({"model": " "}, "modelo"),
        ({"ideas_summary": " "}, "resumo"),
        ({"draft_id": "../x"}, "draft_id"),
    ],
)  # fmt: skip
def test_triage_invalida(campos: dict[str, Any], motivo: str) -> None:
    with pytest.raises(InvalidTriageError, match=motivo):
        _triage(**campos)


@pytest.mark.parametrize(
    "alvo",
    [MergeTarget("draft", "../../etc"), MergeTarget("library", "/etc/x"), MergeTarget("x", DID)],
)
def test_merge_target_invalido(alvo: MergeTarget) -> None:
    with pytest.raises(InvalidTriageError, match="fusão"):
        _triage(merge_target=alvo)


def test_triage_valida() -> None:
    t = _triage(verdict=TriageVerdict.COVERED, covered_by=("skill/diretrizes-codificacao",))
    assert t.covered_by == ("skill/diretrizes-codificacao",)
    assert _triage(cost_usd=None).cost_usd is None


# --- validação com contexto --------------------------------------------------------


def _sempre(_: str) -> bool:
    return True


def _nunca(_: str) -> bool:
    return False


def test_contexto_item_citado_inexistente() -> None:
    t = _triage(verdict=TriageVerdict.COVERED, covered_by=("skill/fantasma",))
    with pytest.raises(InvalidTriageError, match="skill/fantasma"):
        validate_in_context(t, ArtifactKind.SKILL, False, _nunca, _sempre)


def test_contexto_fusao_com_alvo_inexistente() -> None:
    with pytest.raises(InvalidTriageError, match="rule/estilo"):
        validate_in_context(
            _triage(merge_target=MergeTarget("library", "rule/estilo")),
            ArtifactKind.RULE, False, _nunca, _sempre,
        )  # fmt: skip
    with pytest.raises(InvalidTriageError, match=DID):
        validate_in_context(
            _triage(merge_target=MergeTarget("draft", DID)),
            ArtifactKind.RULE,
            False,
            _sempre,
            _nunca,
        )


def test_contexto_unknown_gap_exige_tipo_sugerido() -> None:
    with pytest.raises(InvalidTriageError, match="tipo sugerido"):
        validate_in_context(_triage(), ArtifactKind.UNKNOWN, False, _sempre, _sempre)
    validate_in_context(
        _triage(suggested_kind=ArtifactKind.RULE), ArtifactKind.UNKNOWN, False, _sempre, _sempre
    )


def test_contexto_licenca_restrita_exige_resumo() -> None:
    with pytest.raises(InvalidTriageError, match="resumo"):
        validate_in_context(_triage(), ArtifactKind.SKILL, True, _sempre, _sempre)
    validate_in_context(_triage(ideas_summary="ideias"), ArtifactKind.SKILL, True, _sempre, _sempre)
    # covered com licença restrita não precisa de resumo
    covered = _triage(verdict=TriageVerdict.COVERED, covered_by=("skill/a",))
    validate_in_context(covered, ArtifactKind.SKILL, True, _sempre, _sempre)


# --- elegibilidade -------------------------------------------------------------------


@pytest.mark.parametrize("stage", [Stage.REVIEWED, Stage.PROMOTED, Stage.DISCARDED, Stage.REMOVED])
def test_nunca_elegivel(stage: Stage) -> None:
    assert not is_eligible(_estado(stage, triage=_triage(prompt_fingerprint="0" * 64)), FP, True)


def test_pending_sempre_elegivel() -> None:
    assert is_eligible(_estado(Stage.PENDING), FP, False)


def test_failed_respeita_tentativas() -> None:
    assert is_eligible(_estado(Stage.FAILED, attempts=2), FP, False)
    assert not is_eligible(_estado(Stage.FAILED, attempts=3), FP, False)
    assert is_eligible(_estado(Stage.FAILED, attempts=3), FP, True)
    # prompts mudaram: volta a ser elegível mesmo esgotado
    antiga = _triage(prompt_fingerprint="0" * 64)
    assert is_eligible(_estado(Stage.FAILED, attempts=3, triage=antiga), FP, False)


@pytest.mark.parametrize("stage", [Stage.TRIAGED, Stage.DRAFTED])
def test_triado_so_com_impressao_digital_diferente(stage: Stage) -> None:
    assert not is_eligible(_estado(stage, triage=_triage()), FP, False)
    assert is_eligible(_estado(stage, triage=_triage(prompt_fingerprint="0" * 64)), FP, False)
    assert is_eligible(_estado(stage), FP, False)  # inconsistente: sem triagem gravada


# --- transições ----------------------------------------------------------------------


def test_transicoes() -> None:
    pendente = _estado(Stage.PENDING, last_error="x", attempts=1)
    triado = with_triage(pendente, _triage())
    assert (triado.stage, triado.last_error, triado.attempts) == (Stage.TRIAGED, None, 1)
    rascunhado = with_draft(triado, DID)
    assert rascunhado.stage is Stage.DRAFTED
    assert rascunhado.triage is not None and rascunhado.triage.draft_id == DID
    falhou = with_failure(triado, "LanguageModelTimeoutError")
    assert (falhou.stage, falhou.last_error, falhou.attempts) == (
        Stage.FAILED,
        "LanguageModelTimeoutError",
        2,
    )
    assert falhou.triage == triado.triage  # a triagem já gravada é mantida


def test_with_draft_exige_triagem_gap() -> None:
    with pytest.raises(InvalidTriageError):
        with_draft(_estado(Stage.PENDING), DID)
    covered = with_triage(
        _estado(Stage.PENDING),
        _triage(verdict=TriageVerdict.COVERED, covered_by=("skill/a",)),
    )
    with pytest.raises(InvalidTriageError):
        with_draft(covered, DID)
    assert replace(covered).stage is Stage.TRIAGED
