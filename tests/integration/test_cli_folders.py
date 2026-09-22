# -*- coding: utf-8 -*-
"""
NOME: test_cli_folders.py
TITULO: Testes de falha — CLI praxisforge folders add|list|show|update
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 16:44
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 22/09/2026 09:45: criação (T032)
    - 22/09/2026 19:08: +caso update --status ignore (T029, feature 003-bootstrap-registro-pastas)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.presentation.cli import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_add_list_show_update_fluxo_completo(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fluxo completo add → list → show → update com código 0 em cada passo."""
    registry_arg = ["--registry", str(tmp_registry_path)]
    code, out, _ = _run(
        [
            *registry_arg,
            "folders",
            "add",
            "--alias",
            "exemplo",
            "--description",
            "Pasta de teste",
            "--content-type",
            "documents",
            "--license",
            "MIT",
            "--status",
            "not_scanned",
        ],
        capsys,
    )
    assert code == 0

    code, out, _ = _run([*registry_arg, "folders", "list"], capsys)
    assert code == 0
    assert "exemplo" in out
    assert str(tmp_registry_path.parent) not in out

    code, out, _ = _run([*registry_arg, "folders", "show", "exemplo"], capsys)
    assert code == 0
    assert "exemplo" in out

    code, out, _ = _run(
        [*registry_arg, "folders", "update", "exemplo", "--status", "scanned"], capsys
    )
    assert code == 0


def test_add_duas_vezes_identico_imprime_inalterado_codigo_0(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Segundo add idêntico imprime 'inalterado' e retorna código 0."""
    registry_arg = ["--registry", str(tmp_registry_path)]
    args = [
        *registry_arg,
        "folders",
        "add",
        "--alias",
        "exemplo",
        "--description",
        "Pasta de teste",
        "--content-type",
        "documents",
        "--license",
        "MIT",
        "--status",
        "not_scanned",
    ]
    _run(args, capsys)
    code, out, _ = _run(args, capsys)
    assert code == 0
    assert "inalterado" in out


def test_add_duplicado_com_dados_diferentes_codigo_1(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """add de alias já registrado com dados diferentes retorna código 1."""
    registry_arg = ["--registry", str(tmp_registry_path)]
    base = [
        *registry_arg,
        "folders",
        "add",
        "--alias",
        "exemplo",
        "--description",
        "Pasta de teste",
        "--content-type",
        "documents",
        "--license",
        "MIT",
        "--status",
        "not_scanned",
    ]
    _run(base, capsys)
    outro = [*base[:-1], "not_scanned"]
    outro[base.index("--description") + 1] = "Outra descrição"
    code, _, err = _run(outro, capsys)
    assert code == 1
    assert err


def test_show_alias_inexistente_codigo_1(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """show de alias inexistente retorna código 1."""
    tmp_registry_path.write_text("schema_version: '1'\nfolders: {}\n", encoding="utf-8")
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "show", "inexistente"], capsys
    )
    assert code == 1
    assert err


def test_mensagens_pt_br_no_stderr(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Mensagens de erro estão em pt-BR e vão para stderr."""
    tmp_registry_path.write_text("schema_version: '1'\nfolders: {}\n", encoding="utf-8")
    _, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "show", "inexistente"], capsys
    )
    assert "não encontrada" in err


def test_nenhuma_saida_contem_caminho_absoluto(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nenhuma saída da CLI (exceto resolve) contém caminho absoluto."""
    registry_arg = ["--registry", str(tmp_registry_path)]
    _run(
        [
            *registry_arg,
            "folders",
            "add",
            "--alias",
            "exemplo",
            "--description",
            "Pasta de teste",
            "--content-type",
            "documents",
            "--license",
            "MIT",
            "--status",
            "not_scanned",
        ],
        capsys,
    )
    code, out, _ = _run([*registry_arg, "folders", "list"], capsys)
    assert str(tmp_registry_path) not in out


def test_update_status_ignore_aceito_codigo_0(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders update --status ignore é aceito mesmo com licença unknown (FR-011)."""
    registry_arg = ["--registry", str(tmp_registry_path)]
    _run(
        [
            *registry_arg,
            "folders",
            "add",
            "--alias",
            "pasta_tecnica",
            "--description",
            "Pasta técnica",
            "--content-type",
            "unclassified",
            "--license",
            "unknown",
            "--status",
            "pending",
        ],
        capsys,
    )
    code, out, _ = _run(
        [*registry_arg, "folders", "update", "pasta_tecnica", "--status", "ignore"], capsys
    )
    assert code == 0
