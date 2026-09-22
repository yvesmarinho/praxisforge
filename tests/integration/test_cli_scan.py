# -*- coding: utf-8 -*-
"""
NOME: test_cli_scan.py
TITULO: Testes de falha — CLI praxisforge folders scan
DATA: 22/09/2026 12:40
MODIFICADO: 22/09/2026 16:44
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 22/09/2026 12:40: criação (T003/T009/T015)
    - 22/09/2026 19:10: +casos status ignore (T030, feature 003-bootstrap-registro-pastas)
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


# --- US1: scan de um único alias ----------------------------------------------------


def test_scan_alias_sucesso_codigo_0(
    tmp_registry_path: Path,
    tmp_path: Path,
    env_folder: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders scan ALIAS com caminho válido retorna código 0 e confirma status/last_scanned."""
    _add_folder(tmp_registry_path, "demo_a", capsys)
    destino = tmp_path / "real"
    destino.mkdir()
    env_folder.set("demo_a", str(destino))  # type: ignore[attr-defined]
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "scan", "demo_a"], capsys)
    assert code == 0
    assert "demo_a" in out
    assert "varrida" in out


def test_scan_alias_inexistente_codigo_1(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders scan de alias não registrado retorna código 1 e cita o alias."""
    tmp_registry_path.write_text("schema_version: '1'\nfolders: {}\n", encoding="utf-8")
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "scan", "alias_nao_registrado"], capsys
    )
    assert code == 1
    assert "alias_nao_registrado" in err


def test_scan_caminho_nao_configurado_codigo_3(
    tmp_registry_path: Path, env_folder: object, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders scan com variável de ambiente ausente retorna código 3 e cita o motivo."""
    _add_folder(tmp_registry_path, "demo_a", capsys)
    env_folder.unset("demo_a")  # type: ignore[attr-defined]
    code, _, err = _run(["--registry", str(tmp_registry_path), "folders", "scan", "demo_a"], capsys)
    assert code == 3
    assert "PRAXISFORGE_FOLDER_DEMO_A" in err


def test_scan_sem_caminho_absoluto_na_saida(
    tmp_registry_path: Path,
    tmp_path: Path,
    env_folder: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Nenhuma saída de sucesso de folders scan contém caminho absoluto (FR-010)."""
    _add_folder(tmp_registry_path, "demo_a", capsys)
    destino = tmp_path / "real"
    destino.mkdir()
    env_folder.set("demo_a", str(destino))  # type: ignore[attr-defined]
    _, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "scan", "demo_a"], capsys)
    assert str(destino) not in out


# --- US2: scan --all (lote) ----------------------------------------------------------


def test_scan_all_resume_ok_e_falhas(
    tmp_registry_path: Path,
    tmp_path: Path,
    env_folder: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders scan --all resume quantas pastas foram atualizadas e quantas falharam."""
    _add_folder(tmp_registry_path, "demo_a", capsys)
    _add_folder(tmp_registry_path, "demo_quebrada", capsys)
    destino = tmp_path / "real"
    destino.mkdir()
    env_folder.set("demo_a", str(destino))  # type: ignore[attr-defined]
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "scan", "--all"], capsys)
    assert code == 1  # há falha de item, mesmo padrão de `folders resolve --all`
    assert "1 ok, 1 com falha" in out


def test_scan_alias_e_all_juntos_codigo_2(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders scan com alias e --all ao mesmo tempo é uso incorreto (argparse, exit != 0)."""
    with pytest.raises(SystemExit) as excinfo:
        _run(["--registry", str(tmp_registry_path), "folders", "scan", "demo_a", "--all"], capsys)
    assert excinfo.value.code != 0


# --- US3: detecção de aliases duplicados ----------------------------------------------


def test_scan_all_lista_aliases_duplicados(
    tmp_registry_path: Path,
    tmp_path: Path,
    env_folder: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders scan --all lista os aliases duplicados no resumo, sem impedir a varredura."""
    _add_folder(tmp_registry_path, "demo_a", capsys)
    _add_folder(tmp_registry_path, "demo_dup", capsys)
    destino = tmp_path / "real"
    destino.mkdir()
    env_folder.set("demo_a", str(destino))  # type: ignore[attr-defined]
    env_folder.set("demo_dup", str(destino))  # type: ignore[attr-defined]
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "scan", "--all"], capsys)
    assert code == 0
    assert "demo_a" in out
    assert "demo_dup" in out
    assert str(destino) not in out


# --- status ignore (feature 003) -------------------------------------------------------


def test_scan_all_pula_pasta_ignore_sem_exigir_variavel(
    tmp_registry_path: Path,
    tmp_path: Path,
    env_folder: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders scan --all pula pasta ignore, sem exigir PRAXISFORGE_FOLDER_<ALIAS> para ela."""
    _add_folder(tmp_registry_path, "demo_a", capsys)
    _add_folder(tmp_registry_path, "pasta_ignorada", capsys)
    _run(
        ["--registry", str(tmp_registry_path), "folders", "update", "pasta_ignorada",
         "--status", "ignore"],
        capsys,
    )
    destino = tmp_path / "real"
    destino.mkdir()
    env_folder.set("demo_a", str(destino))  # type: ignore[attr-defined]
    # nenhuma variável PRAXISFORGE_FOLDER_PASTA_IGNORADA definida — não deve ser exigida
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "scan", "--all"], capsys)
    assert code == 0
    assert "1 ignoradas" in out


def test_scan_individual_em_alias_ignore_continua_funcionando(
    tmp_registry_path: Path,
    tmp_path: Path,
    env_folder: object,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders scan <alias> individual sobre um alias ignore não é pulado (FR-013)."""
    _add_folder(tmp_registry_path, "pasta_ignorada", capsys)
    _run(
        ["--registry", str(tmp_registry_path), "folders", "update", "pasta_ignorada",
         "--status", "ignore"],
        capsys,
    )
    destino = tmp_path / "real"
    destino.mkdir()
    env_folder.set("pasta_ignorada", str(destino))  # type: ignore[attr-defined]
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "scan", "pasta_ignorada"], capsys
    )
    assert code == 0
    assert "pasta_ignorada" in out
