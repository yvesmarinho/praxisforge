# -*- coding: utf-8 -*-
"""
NOME: triage_budget.py
TITULO: Teto de chamadas e de custo de uma execução de triagem (feature 011)
DATA: 28/09/2026 16:02
MODIFICADO: 28/09/2026 16:02
VERSÃO: 0.1.0
DEPEND: (stdlib)
HISTÓRICO:
    - 28/09/2026 16:02: criação (T030/T045, feature 011)
STATUS: DEV
"""

from dataclasses import dataclass, field
from decimal import Decimal

from praxisforge.domain.errors import InvalidTriageOptionsError

TRIAGE_CALLS = 1
DRAFT_WORST_CASE_CALLS = 4  # rascunho + juiz + regeneração + juiz


@dataclass
class TriageBudget:
    """
    Orçamento de uma execução: nunca é ultrapassado (SC-005, FR-026 a FR-028).

    Antes de cada etapa, reserva o pior caso dela; toda chamada conta, com ou sem sucesso.

    :param max_calls: teto de chamadas (≥ 1), somando todas as pastas.
    :param max_cost_usd: teto em US$ (> 0) ou None.
    :raises InvalidTriageOptionsError: teto fora do intervalo.

    :Example:

    >>> b = TriageBudget(max_calls=2)
    >>> b.can_spend(1), b.record(Decimal("0.01")), b.can_spend(2)
    (True, None, False)
    """

    max_calls: int
    max_cost_usd: Decimal | None = None
    calls: int = 0
    cost: Decimal = field(default_factory=lambda: Decimal("0"))
    cost_measurable: bool = True

    def __post_init__(self) -> None:
        if self.max_calls < 1:
            raise InvalidTriageOptionsError("--max-calls precisa ser ≥ 1")
        if self.max_cost_usd is not None and self.max_cost_usd <= 0:
            raise InvalidTriageOptionsError("--max-cost-usd precisa ser > 0")

    def can_spend(self, calls: int) -> bool:
        """Diz se ainda cabem `calls` chamadas (e se sobra custo, quando mensurável)."""
        if self.calls + calls > self.max_calls:
            return False
        if self.max_cost_usd is not None and self.cost_measurable:
            return self.cost < self.max_cost_usd
        return True

    def record(self, cost: Decimal | None) -> None:
        """Contabiliza uma chamada concluída; custo None torna o teto em US$ não mensurável."""
        self.calls += 1
        if cost is None:
            self.cost_measurable = False
        else:
            self.cost += cost

    def record_failed_call(self) -> None:
        """Contabiliza uma chamada que falhou (custo desconhecido, sem mudar a mensurabilidade)."""
        self.calls += 1

    def remaining_usd(self) -> Decimal | None:
        """Orçamento em US$ restante, repassado ao CLI (None sem teto ou sem medição)."""
        if self.max_cost_usd is None or not self.cost_measurable:
            return None
        return max(self.max_cost_usd - self.cost, Decimal("0"))
