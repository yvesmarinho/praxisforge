# -*- coding: utf-8 -*-
"""
NOME: test_cli_resolve.py
TITULO: Testes de falha — CLI praxisforge folders resolve
DATA: 22/09/2026 10:10
MODIFICADO: 22/09/2026 10:01
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 22/09/2026 10:10: criação (T043)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.presentation.cli import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _add_folder(registry_path: Path, alias: str, capsys: pytest.CaptureFixture[str]) -> None:
    _run(
        [
            "--registry",
            str(registry_path),
            "folders",
            "add",
            "--alias",
            alias,
            "--description",
            "d",
            "--content-type",
            "documents",
            "--license",
            "MIT",
            "--status",
            "not_scanned",
        ],
        capsys,
    )


def test_resolve_imprime_caminho_real_e_codigo_0(
    tmp_registry_path: Path,
    tmp_path: Path,
    env_folder: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders resolve ALIAS imprime o caminho real e retorna código 0."""
    _add_folder(tmp_registry_path, "github_forks", capsys)
    destino = tmp_path / "real"
    destino.mkdir()
    env_folder.set("github_forks", str(destino))  # type: ignore[attr-defined]
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "resolve", "github_forks"], capsys
    )
    assert code == 0
    assert str(destino.resolve()) in out


def test_resolve_variavel_ausente_codigo_3(
    tmp_registry_path: Path, env_folder: object, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders resolve com variável ausente retorna código 3 e cita o nome da variável."""
    _add_folder(tmp_registry_path, "github_forks", capsys)
    env_folder.unset("github_forks")  # type: ignore[attr-defined]
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "resolve", "github_forks"], capsys
    )
    assert code == 3
    assert "PRAXISFORGE_FOLDER_GITHUB_FORKS" in err


def test_resolve_alias_inexistente_codigo_1(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders resolve de alias inexistente retorna código 1."""
    tmp_registry_path.write_text("schema_version: '1'\nfolders: {}\n", encoding="utf-8")
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "resolve", "inexistente"], capsys
    )
    assert code == 1
    assert err


def test_resolve_all_resumo_com_falha_e_codigo_1(
    tmp_registry_path: Path,
    tmp_path: Path,
    env_folder: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders resolve --all imprime resumo e retorna código 1 se houver falhas."""
    _add_folder(tmp_registry_path, "aa", capsys)
    _add_folder(tmp_registry_path, "bb", capsys)
    destino = tmp_path / "real"
    destino.mkdir()
    env_folder.set("aa", str(destino))  # type: ignore[attr-defined]
    env_folder.unset("bb")  # type: ignore[attr-defined]
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "resolve", "--all"], capsys
    )
    assert code == 1
    assert "1 ok" in out
    assert "1 com falha" in out


def test_resolve_all_todas_ok_codigo_0(
    tmp_registry_path: Path,
    tmp_path: Path,
    env_folder: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders resolve --all com todas resolvendo retorna código 0."""
    _add_folder(tmp_registry_path, "aa", capsys)
    destino = tmp_path / "real"
    destino.mkdir()
    env_folder.set("aa", str(destino))  # type: ignore[attr-defined]
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "resolve", "--all"], capsys
    )
    assert code == 0
    assert "1 ok" in out
