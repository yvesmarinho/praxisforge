# -*- coding: utf-8 -*-
"""
NOME: test_library_scale.py
TITULO: Teste de escala — 200 itens mistos no acervo (SC-004)
DATA: 25/09/2026 13:21
MODIFICADO: 25/09/2026 13:21
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 25/09/2026 13:21: criação (T045, feature 009) — sucede test_skills_scale.py
STATUS: DEV
"""

import time
from collections.abc import Callable
from functools import partial
from pathlib import Path

import pytest

from praxisforge.presentation.cli import main
from tests.library_helpers import criar_projeto, escrever_fonte, escrever_item

_LIMITE_S = 5.0
_TIPOS = ("skill", "command", "agent", "hook", "rule", "reference")
_QUANTIDADE = 200


def _medir(operacao: Callable[[], int]) -> tuple[int, float]:
    inicio = time.perf_counter()
    codigo = operacao()
    return codigo, time.perf_counter() - inicio


@pytest.mark.slow
def test_duzentos_itens_mistos_abaixo_de_cinco_segundos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """validate, index e publish sobre 200 itens mistos levam < 5 s cada (SC-004)."""
    root = criar_projeto(tmp_path / "projeto")
    app = tmp_path / "app"
    app.mkdir()
    monkeypatch.chdir(root)
    escrever_fonte(root, "guias", "guia")
    for indice in range(_QUANTIDADE):
        tipo = _TIPOS[indice % len(_TIPOS)]
        escrever_item(root, tipo, f"{tipo}-{indice:03d}", sources=["guia"], authored=None)

    for argv in (
        ["library", "validate"],
        ["library", "index"],
        ["library", "publish", "--all", "--target", str(app)],
    ):
        codigo, duracao = _medir(partial(main, argv))
        saida = capsys.readouterr().out
        assert codigo == 0, (argv, saida[-500:])
        assert duracao < _LIMITE_S, f"{argv[1]} levou {duracao:.2f}s"
    publicados = sum(1 for p in (app / ".claude").rglob("*.md") if not p.name.startswith("."))
    assert publicados >= _QUANTIDADE * 4 // len(_TIPOS)
