# -*- coding: utf-8 -*-
"""
NOME: test_cli_validate.py
TITULO: Testes de falha — CLI praxisforge folders validate / sources validate
DATA: 22/09/2026 10:30
MODIFICADO: 23/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 22/09/2026 10:30: criação (T053)
    - 23/09/2026 16:54: registro v2 com path (T022, feature 005)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.presentation.cli import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_folders_validate_registro_valido_codigo_0(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders validate com registro válido retorna código 0."""
    tmp_registry_path.write_text(
        "schema_version: '2'\n"
        "folders:\n"
        "  github_forks:\n"
        "    description: d\n"
        "    content_type: docs\n"
        "    license: unknown\n"
        "    last_scanned: null\n"
        "    status: pending\n"
        "    path: /srv/pastas/github_forks\n",
        encoding="utf-8",
    )
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "validate"], capsys)
    assert code == 0
    assert "1 ok" in out


def test_folders_validate_lista_violacoes_e_resumo_codigo_1(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders validate com pasta inválida lista violações e retorna código 1."""
    tmp_registry_path.write_text(
        "schema_version: '2'\n"
        "folders:\n"
        "  invalida:\n"
        "    description: d\n"
        "    content_type: docs\n"
        "    license: unknown\n"
        "    last_scanned: null\n"
        "    status: scanned\n"  # unknown exige pending
        "    path: /srv/pastas/invalida\n",
        encoding="utf-8",
    )
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "validate"], capsys)
    assert code == 1
    assert "com falha" in out


def test_sources_validate_arquivo_e_diretorio(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """sources validate aceita arquivo ou diretório; falha por item não interrompe o lote."""
    valido = tmp_path / "valido.md"
    valido.write_text(
        "---\nschema_version: '1'\norigin: https://x\ndate: 2026-09-21\nlicense: MIT\n"
        "relevance: y\nstatus: active\nextract_allowed: true\n---\n",
        encoding="utf-8",
    )
    invalido = tmp_path / "invalido.md"
    invalido.write_text("sem frontmatter\n", encoding="utf-8")

    code, out, _ = _run(["sources", "validate", str(valido)], capsys)
    assert code == 0

    code, out, _ = _run(["sources", "validate", str(tmp_path)], capsys)
    assert code == 1
    assert "1 ok" in out
    assert "1 com falha" in out
