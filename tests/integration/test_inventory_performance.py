# -*- coding: utf-8 -*-
"""
NOME: test_inventory_performance.py
TITULO: Teste de desempenho — inventário de 5.000 arquivos em menos de 10 s (SC-005)
DATA: 25/09/2026 15:28
MODIFICADO: 25/09/2026 14:57
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.inventory_folders
HISTÓRICO:
    - 25/09/2026 15:28: criação (T033, feature 010)
STATUS: DEV
"""

import time
from pathlib import Path

import pytest

from tests.integration.test_inventory_folders import _Ambiente


@pytest.mark.slow
def test_cinco_mil_arquivos_em_menos_de_dez_segundos(tmp_path: Path) -> None:
    amb = _Ambiente(tmp_path)
    arquivos: dict[str, str | bytes] = {}
    for i in range(250):
        arquivos[f"skills/s{i}/SKILL.md"] = f"# skill {i}"
        for j in range(9):
            arquivos[f"skills/s{i}/references/r{j}.md"] = "apoio " * 20
    for i in range(2500):
        arquivos[f"docs/d{i // 100}/n{i}.md"] = "nota " * 30
    assert len(arquivos) == 5000
    amb.registrar("grande_a", arquivos)
    inicio = time.perf_counter()
    resultado = amb.inventariar("grande_a")
    assert time.perf_counter() - inicio < 10
    assert resultado.artifacts == 250 + 2500
