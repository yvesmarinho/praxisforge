# -*- coding: utf-8 -*-
"""
NOME: test_cli_project_root.py
TITULO: Testes de integração — CLI resolve schemas/skills/fontes pela raiz, não pelo cwd
DATA: 25/09/2026 09:55
MODIFICADO: 25/09/2026 09:55
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 25/09/2026 09:55: criação
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.presentation.cli import main
from tests.skills_helpers import criar_projeto, escrever_skill


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture
def projeto(tmp_path: Path) -> Path:
    root = criar_projeto(tmp_path / "projeto")
    escrever_skill(root, "revisar", authored=True)
    return root


def test_skills_validate_a_partir_de_subpasta(
    projeto: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rodar dentro de skills/revisar acha a raiz e valida normalmente."""
    monkeypatch.chdir(projeto / "skills" / "revisar")
    code, out, err = _run(["skills", "validate", "--all"], capsys)
    assert code == 0, err
    assert "1 ok" in out


def test_skills_catalog_grava_na_raiz_e_nao_no_cwd(
    projeto: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """catalog a partir de src/data grava skills/README.md na raiz."""
    cwd = projeto / "src" / "data"
    monkeypatch.chdir(cwd)
    code, _, err = _run(["skills", "catalog"], capsys)
    assert code == 0, err
    assert (projeto / "skills" / "README.md").is_file()
    assert not (cwd / "skills").exists()


def test_fora_do_projeto_codigo_3_com_dica(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fora de qualquer projeto → código 3 (ambiente) e dica de PRAXISFORGE_ROOT."""
    solta = tmp_path / "solta"
    solta.mkdir()
    monkeypatch.chdir(solta)
    code, _, err = _run(["skills", "validate", "--all"], capsys)
    assert code == 3
    assert "raiz do projeto" in err
    assert "PRAXISFORGE_ROOT" in err


def test_env_permite_rodar_de_fora(
    projeto: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """PRAXISFORGE_ROOT aponta a raiz e a CLI funciona de qualquer diretório."""
    solta = tmp_path / "solta"
    solta.mkdir()
    monkeypatch.chdir(solta)
    monkeypatch.setenv("PRAXISFORGE_ROOT", str(projeto))
    code, out, err = _run(["skills", "validate", "--all"], capsys)
    assert code == 0, err
    assert "1 ok" in out


def test_env_invalido_codigo_3(
    projeto: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """PRAXISFORGE_ROOT inválido falha com código 3 mesmo dentro do projeto."""
    monkeypatch.chdir(projeto)
    monkeypatch.setenv("PRAXISFORGE_ROOT", "relativo")
    code, _, err = _run(["skills", "validate", "--all"], capsys)
    assert code == 3
    assert "PRAXISFORGE_ROOT" in err


def test_folders_list_a_partir_de_subpasta(
    projeto: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders usa os schemas da raiz mesmo rodando numa subpasta."""
    registro = tmp_path / "registro.yaml"
    registro.write_text('schema_version: "2"\nfolders: {}\n', encoding="utf-8")
    monkeypatch.chdir(projeto / "skills")
    code, _, err = _run(["--registry", str(registro), "folders", "validate"], capsys)
    assert code == 0, err
