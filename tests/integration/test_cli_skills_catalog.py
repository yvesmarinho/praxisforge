# -*- coding: utf-8 -*-
"""
NOME: test_cli_skills_catalog.py
TITULO: Testes de integração — CLI praxisforge skills catalog (feature 008)
DATA: 24/09/2026 16:54
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 24/09/2026 16:54: criação (T023, feature 008)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.presentation.cli import main
from tests.skills_helpers import criar_projeto, escrever_skill


@pytest.fixture
def projeto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = criar_projeto(tmp_path / "projeto")
    monkeypatch.chdir(root)
    return root


def test_catalog_grava_e_e_idempotente(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Grava skills/README.md; segunda execução é idêntica byte a byte (SC-002)."""
    escrever_skill(projeto, "beta", authored=True)
    escrever_skill(projeto, "alfa", authored=True)
    (projeto / "skills" / "_template").mkdir()
    assert main(["skills", "catalog"]) == 0
    primeiro = (projeto / "skills" / "README.md").read_bytes()
    assert main(["skills", "catalog"]) == 0
    assert (projeto / "skills" / "README.md").read_bytes() == primeiro
    texto = primeiro.decode("utf-8")
    assert "| alfa |" in texto and "| beta |" in texto and "| _template |" not in texto
    assert "catálogo: 2 skills (0 omitidas)" in capsys.readouterr().out


def test_catalog_com_invalida_sai_1(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Inválida omitida e listada; exit 1."""
    escrever_skill(projeto, "boa", authored=True)
    escrever_skill(projeto, "ruim", version="1", authored=True)
    assert main(["skills", "catalog"]) == 1
    out = capsys.readouterr().out
    assert "catálogo: 1 skills (1 omitidas)" in out
    assert "ruim: " in out
    assert "ruim" not in (projeto / "skills" / "README.md").read_text(encoding="utf-8")


def test_catalog_sem_permissao_sai_3(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Falha de gravação do catálogo → exit 3, catálogo anterior preservado."""
    escrever_skill(projeto, "alfa", authored=True)
    readme = projeto / "skills" / "README.md"
    readme.write_text("anterior", encoding="utf-8")
    (projeto / "skills").chmod(0o500)
    try:
        assert main(["skills", "catalog"]) == 3
    finally:
        (projeto / "skills").chmod(0o700)
    assert readme.read_text(encoding="utf-8") == "anterior"
    assert "catálogo" in capsys.readouterr().err
