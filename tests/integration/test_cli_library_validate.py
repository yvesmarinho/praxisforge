# -*- coding: utf-8 -*-
"""
NOME: test_cli_library_validate.py
TITULO: Testes de integração — praxisforge library validate (contrato da CLI)
DATA: 25/09/2026 13:09
MODIFICADO: 25/09/2026 13:09
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 25/09/2026 13:09: criação (T017, feature 009) — sucede test_cli_skills_validate.py
STATUS: DEV
"""

import shutil
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


def test_tudo_valido_codigo_0(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Sem argumentos valida tudo; resumo N ok, 0 com falha."""
    escrever_item(projeto, "skill", "s")
    escrever_item(projeto, "command", "c")
    code, out, _ = _run(["library", "validate"], capsys)
    assert code == 0
    assert "2 ok, 0 com falha" in out


def test_falha_codigo_1_com_motivo_por_item(
    projeto: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Item inválido: linha <kind>/<nome>: <motivo> e código 1 (FR-010)."""
    escrever_item(projeto, "agent", "a", campos={"name": "outro"})
    escrever_item(projeto, "rule", "r")
    code, out, _ = _run(["library", "validate"], capsys)
    assert code == 1
    assert "agent/a: name:" in out
    assert "1 ok, 1 com falha" in out


def test_filtro_por_tipo_e_nome(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--type restringe; --type + nome valida um item."""
    escrever_item(projeto, "agent", "a")
    escrever_item(projeto, "agent", "b", campos={"name": "x"})
    escrever_item(projeto, "skill", "s")
    code, out, _ = _run(["library", "validate", "--type", "agent", "a"], capsys)
    assert (code, "1 ok, 0 com falha" in out) == (0, True)
    code, out, _ = _run(["library", "validate", "--type", "skill"], capsys)
    assert (code, "1 ok, 0 com falha" in out) == (0, True)


def test_nome_sem_tipo_codigo_2(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """<nome> sem --type é erro de uso."""
    code, _, err = _run(["library", "validate", "a"], capsys)
    assert code == 2
    assert "--type" in err


def test_tipo_desconhecido_codigo_2(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--type fora dos seis tipos é erro de uso."""
    code, _, err = _run(["library", "validate", "--type", "prompt"], capsys)
    assert code == 2
    assert "tipo desconhecido" in err


def test_reescrita_pendente_aparece(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Item com reescrita pendente é listado sem virar falha."""
    escrever_item(projeto, "skill", "s", metadata={"rewrite_pending": True})
    code, out, _ = _run(["library", "validate"], capsys)
    assert code == 0
    assert "skill/s: reescrita pendente" in out


def test_entrada_desconhecida(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Entrada fora dos tipos: ?/<caminho>: tipo desconhecido e código 1."""
    (projeto / "library" / "prompts").mkdir()
    code, out, _ = _run(["library", "validate"], capsys)
    assert code == 1
    assert "?/prompts: tipo desconhecido" in out


def test_acervo_ausente_codigo_3(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """library/ ausente → código 3 com a indicação de migrar."""
    shutil.rmtree(projeto / "library")
    code, _, err = _run(["library", "validate"], capsys)
    assert code == 3
    assert "library/" in err
