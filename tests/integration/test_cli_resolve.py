# -*- coding: utf-8 -*-
"""
NOME: test_cli_resolve.py
TITULO: Testes de falha — CLI praxisforge folders resolve
DATA: 22/09/2026 10:10
MODIFICADO: 24/09/2026 10:12
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 22/09/2026 10:10: criação (T043)
    - 23/09/2026 16:53: caminho no registro, sem variáveis de ambiente (T022, feature 005)
    - 24/09/2026 10:12: registro inválido sai com código 1, sem traceback (bug)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.presentation.cli import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _add_folder(registry_path: Path, alias: str, capsys: pytest.CaptureFixture[str]) -> Path:
    """Registra uma pasta real em `<registro>/../pastas/<alias>` e devolve o caminho."""
    caminho = registry_path.parent / "pastas" / alias
    caminho.mkdir(parents=True, exist_ok=True)
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
            "--path",
            str(caminho),
        ],
        capsys,
    )
    return caminho


def test_resolve_imprime_caminho_do_registro_e_codigo_0(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders resolve ALIAS imprime o caminho do registro, sem variável de ambiente (FR-008)."""
    destino = _add_folder(tmp_registry_path, "github_forks", capsys)
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "resolve", "github_forks"], capsys
    )
    assert code == 0
    assert str(destino.resolve()) in out


def test_resolve_pasta_movida_codigo_3(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pasta que sumiu do caminho registrado → código 3 citando o alias."""
    _add_folder(tmp_registry_path, "github_forks", capsys).rmdir()
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "resolve", "github_forks"], capsys
    )
    assert code == 3
    assert "github_forks" in err


def test_resolve_alias_inexistente_codigo_1(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders resolve de alias inexistente retorna código 1."""
    tmp_registry_path.write_text("schema_version: '2'\nfolders: {}\n", encoding="utf-8")
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "resolve", "inexistente"], capsys
    )
    assert code == 1
    assert err


def test_resolve_all_resumo_com_falha_e_codigo_1(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders resolve --all imprime resumo e retorna código 1 se houver falhas."""
    _add_folder(tmp_registry_path, "aa", capsys)
    _add_folder(tmp_registry_path, "bb", capsys).rmdir()
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "resolve", "--all"], capsys
    )
    assert code == 1
    assert "1 ok" in out
    assert "1 com falha" in out


def test_resolve_all_todas_ok_codigo_0(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders resolve --all com todas acessíveis retorna código 0."""
    _add_folder(tmp_registry_path, "aa", capsys)
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "resolve", "--all"], capsys
    )
    assert code == 0
    assert "1 ok" in out


def test_registro_v1_pede_migracao(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Qualquer comando sobre registro v1 → código 1 pedindo folders migrate (US3 c.4)."""
    tmp_registry_path.write_text("schema_version: '1'\nfolders: {}\n", encoding="utf-8")
    code, _, err = _run(["--registry", str(tmp_registry_path), "folders", "list"], capsys)
    assert code == 1
    assert "folders migrate" in err


_REGISTRO_INVALIDO = (
    "schema_version: '2'\nfolders:\n  fonte:\n    content_type: documents\n"
    "    description: ''\n    last_scanned: null\n    license: MIT\n"
    "    path: /srv/fonte\n    status: not_scanned\n"
)


@pytest.mark.parametrize("alvo", [["fonte"], ["--all"]])
def test_resolve_registro_invalido_codigo_1_sem_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], alvo: list[str]
) -> None:
    """Registro fora do contrato → código 1 e mensagem amigável no stderr (bug 24/09/2026)."""
    registry = tmp_path / "folders.yaml"
    registry.write_text(_REGISTRO_INVALIDO, encoding="utf-8")
    code, _, err = _run(["--registry", str(registry), "folders", "resolve", *alvo], capsys)
    assert code == 1
    assert "description" in err
    assert "folders validate" in err
