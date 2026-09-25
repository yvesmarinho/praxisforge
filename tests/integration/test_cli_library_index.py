# -*- coding: utf-8 -*-
"""
NOME: test_cli_library_index.py
TITULO: Testes de integração — praxisforge library index
DATA: 25/09/2026 13:15
MODIFICADO: 25/09/2026 13:15
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 25/09/2026 13:15: criação (T029, feature 009) — sucede test_cli_skills_catalog.py
STATUS: DEV
"""

import os
from pathlib import Path

import pytest

from praxisforge.presentation.cli import main
from tests.library_helpers import criar_projeto, escrever_item


@pytest.fixture
def projeto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = criar_projeto(tmp_path / "projeto")
    monkeypatch.chdir(root)
    return root


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_gera_indice_idempotente(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Gera library/INDEX.md; segunda execução produz bytes idênticos (SC-003)."""
    escrever_item(projeto, "skill", "s")
    escrever_item(projeto, "rule", "r")
    code, out, _ = _run(["library", "index"], capsys)
    assert code == 0
    assert "índice: 2 itens (0 omitidos)" in out
    indice = projeto / "library" / "INDEX.md"
    antes = indice.read_bytes()
    _run(["library", "index"], capsys)
    assert indice.read_bytes() == antes


def test_omitidos_listados_codigo_1(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Item inválido fica fora, é listado e o código é 1."""
    escrever_item(projeto, "agent", "a", campos={"name": "x"})
    code, out, _ = _run(["library", "index"], capsys)
    assert code == 1
    assert "índice: 0 itens (1 omitidos)" in out
    assert "agent/a:" in out


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignora permissão de escrita")
def test_falha_de_gravacao_codigo_3(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Pasta library/ sem escrita → código 3 e índice anterior intacto."""
    indice = projeto / "library" / "INDEX.md"
    indice.write_text("antigo\n", encoding="utf-8")
    (projeto / "library").chmod(0o555)
    try:
        code, _, err = _run(["library", "index"], capsys)
    finally:
        (projeto / "library").chmod(0o755)
    assert code == 3
    assert "falha ao gravar o índice" in err
    assert indice.read_text(encoding="utf-8") == "antigo\n"
