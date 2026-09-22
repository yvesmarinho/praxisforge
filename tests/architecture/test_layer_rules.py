# -*- coding: utf-8 -*-
"""
NOME: test_layer_rules.py
TITULO: Aplica o layer_checker ao código real de src/praxisforge/ — zero violações exigidas
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:53
VERSÃO: 0.1.0
DEPEND: pytest, tests.architecture.layer_checker
HISTÓRICO:
    - 22/09/2026 09:45: criação (T062)
STATUS: DEV
"""

from pathlib import Path

from tests.architecture.layer_checker import check_layers

SRC_ROOT = Path(__file__).parents[2] / "src" / "praxisforge"


def test_codigo_real_sem_violacoes_de_camada() -> None:
    """O código real de src/praxisforge/ não viola a matriz de dependências entre camadas."""
    violations = check_layers(SRC_ROOT, "praxisforge")
    assert violations == [], "\n".join(
        f"{v.module} importa {v.imported} — {v.rule}" for v in violations
    )
