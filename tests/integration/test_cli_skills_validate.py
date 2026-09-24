# -*- coding: utf-8 -*-
"""
NOME: test_cli_skills_validate.py
TITULO: Testes de integração — CLI praxisforge skills validate (feature 008)
DATA: 24/09/2026 16:54
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 24/09/2026 16:54: criação (T014, feature 008)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.presentation.cli import main
from tests.skills_helpers import criar_projeto, escrever_fonte, escrever_skill


@pytest.fixture
def projeto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = criar_projeto(tmp_path / "projeto")
    monkeypatch.chdir(root)
    return root


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_validate_skill_valida(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Skill válida com fonte summary → exit 0 e resumo."""
    escrever_fonte(projeto, "guias", "guia-a")
    escrever_skill(projeto, "revisar", sources=["guia-a"])
    code, out, _ = _run(["skills", "validate", "revisar"], capsys)
    assert code == 0
    assert "1 ok, 0 com falha" in out


def test_validate_all_com_invalida(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--all lista `<skill>: <motivo>` para a inválida e sai com 1."""
    escrever_skill(projeto, "boa", authored=True)
    escrever_skill(projeto, "ruim", sources=["nada"])
    code, out, _ = _run(["skills", "validate", "--all"], capsys)
    assert code == 1
    assert "ruim: " in out and "nada" in out
    assert "boa:" not in out
    assert "1 ok, 1 com falha" in out


def test_validate_schema_e_entidade(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Versão não semver e nome divergente aparecem como motivos da skill."""
    escrever_skill(projeto, "ruim", version="1.0", authored=True, frontmatter_name="outra")
    code, out, _ = _run(["skills", "validate", "ruim"], capsys)
    assert code == 1
    assert "metadata.version" in out and "name" in out


def test_validate_nome_inexistente(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Nome sem pasta → exit 1 com o motivo."""
    code, out, _ = _run(["skills", "validate", "nada"], capsys)
    assert code == 1
    assert "nada: " in out and "não encontrada" in out


@pytest.mark.parametrize("argv", [["skills", "validate"], ["skills", "validate", "x", "--all"]])
def test_validate_uso_incorreto(
    projeto: Path, capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    """Sem nome nem --all (ou ambos) → exit 2."""
    code, _, err = _run(argv, capsys)
    assert code == 2
    assert "--all" in err
