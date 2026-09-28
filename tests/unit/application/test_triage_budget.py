# -*- coding: utf-8 -*-
"""
NOME: test_triage_budget.py
TITULO: Testes de falha — teto de chamadas e de custo da triagem (feature 011)
DATA: 28/09/2026 16:22
MODIFICADO: 28/09/2026 16:22
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.triage_budget
HISTÓRICO:
    - 28/09/2026 16:22: criação (T042, feature 011)
STATUS: DEV
"""

from decimal import Decimal

import pytest

from praxisforge.application.triage_budget import DRAFT_WORST_CASE_CALLS, TriageBudget
from praxisforge.domain.errors import InvalidTriageOptionsError


@pytest.mark.parametrize(("chamadas", "custo"), [(0, None), (-1, None), (1, Decimal("0")),
                                                (1, Decimal("-0.5"))])  # fmt: skip
def test_tetos_invalidos(chamadas: int, custo: Decimal | None) -> None:
    with pytest.raises(InvalidTriageOptionsError):
        TriageBudget(chamadas, custo)


def test_teto_de_chamadas_com_reserva() -> None:
    b = TriageBudget(max_calls=5)
    assert b.can_spend(1) and b.can_spend(DRAFT_WORST_CASE_CALLS + 1)
    b.record(Decimal("0.01"))
    assert b.can_spend(DRAFT_WORST_CASE_CALLS) and not b.can_spend(DRAFT_WORST_CASE_CALLS + 1)
    b.record_failed_call()
    assert b.calls == 2 and b.cost == Decimal("0.01")


def test_teto_de_custo() -> None:
    b = TriageBudget(max_calls=100, max_cost_usd=Decimal("0.05"))
    assert b.remaining_usd() == Decimal("0.05")
    b.record(Decimal("0.03"))
    assert b.can_spend(1) and b.remaining_usd() == Decimal("0.02")
    b.record(Decimal("0.03"))
    assert not b.can_spend(1) and b.remaining_usd() == Decimal("0")


def test_custo_nao_informado_desliga_o_teto_em_usd() -> None:
    b = TriageBudget(max_calls=3, max_cost_usd=Decimal("0.01"))
    b.record(None)
    b.record(Decimal("5"))
    assert not b.cost_measurable and b.remaining_usd() is None
    assert b.can_spend(1) and not b.can_spend(2)  # só o teto de chamadas vale


def test_sem_teto_em_usd() -> None:
    assert TriageBudget(max_calls=1).remaining_usd() is None
