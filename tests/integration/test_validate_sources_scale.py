# -*- coding: utf-8 -*-
"""
NOME: test_validate_sources_scale.py
TITULO: Teste de escala — sources validate com 500 registros (SC-005, feature 006)
DATA: 24/09/2026 10:54
MODIFICADO: 25/09/2026 13:04
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 24/09/2026 10:54: criação (T015, feature 006)
    - 25/09/2026 13:04: registros no v3 (T041, feature 009)
STATUS: DEV
"""

import time
from pathlib import Path

import pytest

from praxisforge.presentation.cli import main

_TOTAL = 500
_LIMITE_SEGUNDOS = 5.0


def test_500_registros_em_menos_de_5s(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Validação em lote de 500 fontes válidas dentro do limite (SC-005)."""
    for indice in range(_TOTAL):
        categoria = tmp_path / f"cat{indice % 10}"
        categoria.mkdir(exist_ok=True)
        (categoria / f"fonte_{indice:03d}.md").write_text(
            "---\nschema_version: '3'\norigin: https://x\nauthor: Fulano\ndate: 2026-09-21\n"
            "license: MIT\nrelevance: y\nstatus: active\n---\n",
            encoding="utf-8",
        )
    inicio = time.perf_counter()
    code = main(["sources", "validate", str(tmp_path)])
    duracao = time.perf_counter() - inicio
    out = capsys.readouterr().out
    assert code == 0
    assert f"{_TOTAL} ok, 0 com falha" in out
    assert duracao < _LIMITE_SEGUNDOS
