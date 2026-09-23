# -*- coding: utf-8 -*-
"""
NOME: test_cli_folders.py
TITULO: Testes de falha — CLI praxisforge folders add|list|show|update
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 12:08
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 22/09/2026 09:45: criação (T032)
    - 22/09/2026 19:08: +caso update --status ignore (T029, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:08: versão curada em update/show (T019, feature 004)
STATUS: DEV
"""

import os
import subprocess
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


# --- feature 004: versão curada (US1) --------------------------------------------------

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Teste",
    "GIT_AUTHOR_EMAIL": "teste@example.invalid",
    "GIT_COMMITTER_NAME": "Teste",
    "GIT_COMMITTER_EMAIL": "teste@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **_GIT_ENV},
    )
    return result.stdout.strip()


def _repo_git(base: Path) -> tuple[Path, str]:
    repo = base / "fonte"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("fonte\n", encoding="utf-8")
    _git(repo, "add", "--all")
    _git(repo, "commit", "-q", "-m", "inicial")
    return repo, _git(repo, "rev-parse", "HEAD")


def _registrar(registry: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, _, _ = _run(
        [
            "--registry",
            str(registry),
            "folders",
            "add",
            "--alias",
            "fonte",
            "--description",
            "Fonte curada",
            "--content-type",
            "documents",
            "--license",
            "MIT",
            "--status",
            "in_curation",
        ],
        capsys,
    )
    assert code == 0


def test_update_curated_em_pasta_git_grava_e_exibe_versao(
    tmp_path: Path, tmp_registry_path: Path, env_folder: object, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders update --status curated grava o HEAD e show exibe 12 caracteres (FR-001, FR-011)."""
    repo, head = _repo_git(tmp_path)
    env_folder.set("fonte", str(repo))  # type: ignore[attr-defined]
    _registrar(tmp_registry_path, capsys)
    registry_arg = ["--registry", str(tmp_registry_path)]

    code, out, _ = _run(
        [*registry_arg, "folders", "update", "fonte", "--status", "curated"], capsys
    )
    assert code == 0
    assert f"versão curada: {head[:12]}" in out
    assert str(tmp_path) not in out
    assert f"last_curated_commit: {head}" in tmp_registry_path.read_text(encoding="utf-8")

    code, out, _ = _run([*registry_arg, "folders", "show", "fonte"], capsys)
    assert code == 0
    assert f"versão curada: {head[:12]}" in out


def test_update_curated_em_pasta_nao_git_informa(
    tmp_path: Path, tmp_registry_path: Path, env_folder: object, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pasta não-git: status muda e a saída explica que não há versão (FR-002)."""
    pasta = tmp_path / "solta"
    pasta.mkdir()
    env_folder.set("fonte", str(pasta))  # type: ignore[attr-defined]
    _registrar(tmp_registry_path, capsys)
    registry_arg = ["--registry", str(tmp_registry_path)]

    code, out, _ = _run(
        [*registry_arg, "folders", "update", "fonte", "--status", "curated"], capsys
    )
    assert code == 0
    assert "versão curada: (pasta não é repositório git)" in out

    code, out, _ = _run([*registry_arg, "folders", "show", "fonte"], capsys)
    assert "versão curada: -" in out


def test_update_curated_sem_caminho_configurado_sai_com_3_sem_alterar(
    tmp_registry_path: Path, env_folder: object, capsys: pytest.CaptureFixture[str]
) -> None:
    """Caminho não configurado → exit 3 e YAML inalterado (FR-003)."""
    env_folder.unset("fonte")  # type: ignore[attr-defined]
    _registrar(tmp_registry_path, capsys)
    antes = tmp_registry_path.read_bytes()
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "update", "fonte", "--status", "curated"],
        capsys,
    )
    assert code == 3
    assert "fonte" in err
    assert tmp_registry_path.read_bytes() == antes
