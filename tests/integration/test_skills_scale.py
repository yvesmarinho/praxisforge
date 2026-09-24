# -*- coding: utf-8 -*-
"""
NOME: test_skills_scale.py
TITULO: Teste de escala — validate, catalog e publish com 50 skills (SC-005)
DATA: 24/09/2026 16:48
MODIFICADO: 24/09/2026 16:50
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 24/09/2026 16:48: criação (T032, feature 008) — skills mínimas e cada operação medida
      separadamente, para não repetir a lentidão do CI do PR #15
STATUS: DEV
"""

import time
from collections.abc import Callable
from functools import partial
from pathlib import Path

import pytest

from praxisforge.presentation.cli import main
from tests.skills_helpers import criar_projeto, escrever_skill

_LIMITE_S = 5.0
_QUANTIDADE = 50


def _medir(operacao: Callable[[], int]) -> tuple[int, float]:
    inicio = time.perf_counter()
    codigo = operacao()
    return codigo, time.perf_counter() - inicio


def test_cinquenta_skills_abaixo_de_cinco_segundos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Cada operação sobre 50 skills autorais leva menos de 5 s."""
    root = criar_projeto(tmp_path / "projeto")
    monkeypatch.chdir(root)
    for indice in range(_QUANTIDADE):
        escrever_skill(root, f"skill-{indice:02d}", authored=True)

    for argv in (
        ["skills", "validate", "--all"],
        ["skills", "catalog"],
        ["skills", "publish", "--all", "--target", "global"],
    ):
        codigo, duracao = _medir(partial(main, argv))
        capsys.readouterr()
        assert codigo == 0, argv
        assert duracao < _LIMITE_S, f"{argv[1]} levou {duracao:.2f}s"
    assert len(list((Path.home() / ".claude" / "skills").iterdir())) == _QUANTIDADE
