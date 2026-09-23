# -*- coding: utf-8 -*-
"""
NOME: test_cli_migrate.py
TITULO: Testes de integração — praxisforge folders migrate
DATA: 23/09/2026 17:02
MODIFICADO: 23/09/2026 17:02
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 23/09/2026 17:02: criação (T033, feature 005-caminho-absoluto-registro)
STATUS: DEV
"""

import time
from pathlib import Path

import pytest

from praxisforge.presentation.cli import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _v1(*aliases: str) -> str:
    linhas = ["schema_version: '1'", "folders:"]
    for alias in aliases:
        linhas += [
            f"  {alias}:",
            "    description: d",
            "    content_type: documents",
            "    license: MIT",
            "    last_scanned: null",
            "    status: not_scanned",
        ]
    return "\n".join(linhas) + "\n"


def test_migracao_com_pendencia_nao_grava_e_sai_com_1(
    tmp_registry_path: Path, tmp_path: Path, env_folder: object, capsys: pytest.CaptureFixture[str]
) -> None:
    """3 pastas: variável, raiz, sem caminho → exit 1, YAML intacto (quickstart §5)."""
    raiz = tmp_path / "raiz"
    (raiz / "pela_raiz").mkdir(parents=True)
    pela_variavel = tmp_path / "var"
    pela_variavel.mkdir()
    env_folder.set("pela_variavel", str(pela_variavel))  # type: ignore[attr-defined]
    tmp_registry_path.write_text(_v1("pela_variavel", "pela_raiz", "sumida"), encoding="utf-8")
    antes = tmp_registry_path.read_bytes()

    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "migrate", "--root", str(raiz)], capsys
    )
    assert code == 1
    assert "sumida" in out
    assert tmp_registry_path.read_bytes() == antes
    assert str(tmp_path) not in out

    (raiz / "sumida").mkdir()
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "migrate", "--root", str(raiz)], capsys
    )
    assert code == 0
    assert "schema_version: '2'" in tmp_registry_path.read_text(encoding="utf-8")
    code, _, _ = _run(["--registry", str(tmp_registry_path), "folders", "validate"], capsys)
    assert code == 0

    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "migrate"], capsys)
    assert code == 0
    assert "já no formato atual" in out


def test_migracao_de_100_pastas_em_menos_de_5s(
    tmp_registry_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Escala (Plan §Performance)."""
    raiz = tmp_path / "raiz"
    aliases = [f"repo_{i:03d}" for i in range(100)]
    for alias in aliases:
        (raiz / alias).mkdir(parents=True)
    tmp_registry_path.write_text(_v1(*aliases), encoding="utf-8")
    inicio = time.perf_counter()
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "migrate", "--root", str(raiz)], capsys
    )
    assert time.perf_counter() - inicio < 5.0
    assert code == 0
    assert "100 migradas" in out
