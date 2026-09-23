# -*- coding: utf-8 -*-
"""
NOME: test_cli_scan.py
TITULO: Testes de falha — CLI praxisforge folders scan
DATA: 22/09/2026 12:40
MODIFICADO: 23/09/2026 16:52
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 22/09/2026 12:40: criação (T003/T009/T015)
    - 22/09/2026 19:10: +casos status ignore (T030, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:15: linha 'conteúdo' e reversão com repositórios git reais (T026, feature 004)
    - 23/09/2026 16:52: caminho no registro, sem variáveis de ambiente (T022, feature 005)
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


def _add_folder(
    registry_path: Path,
    alias: str,
    capsys: pytest.CaptureFixture[str],
    path: Path | None = None,
) -> Path:
    """Registra uma pasta real; cria `<registro>/../pastas/<alias>` se nenhum caminho for dado."""
    if path is None:
        path = registry_path.parent / "pastas" / alias
        path.mkdir(parents=True, exist_ok=True)
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
            str(path),
        ],
        capsys,
    )
    return path


# --- US1: scan de um único alias ----------------------------------------------------


def test_scan_alias_sucesso_codigo_0(
    tmp_registry_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders scan ALIAS com caminho do registro retorna código 0 (sem variável de ambiente)."""
    _add_folder(tmp_registry_path, "demo_a", capsys)
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "scan", "demo_a"], capsys)
    assert code == 0
    assert "demo_a" in out
    assert "varrida" in out


def test_scan_alias_inexistente_codigo_1(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders scan de alias não registrado retorna código 1 e cita o alias."""
    tmp_registry_path.write_text("schema_version: '2'\nfolders: {}\n", encoding="utf-8")
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "scan", "alias_nao_registrado"], capsys
    )
    assert code == 1
    assert "alias_nao_registrado" in err


def test_scan_pasta_movida_codigo_3(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pasta registrada que sumiu do caminho → código 3 citando o alias (feature 005)."""
    caminho = _add_folder(tmp_registry_path, "demo_a", capsys)
    caminho.rmdir()
    code, _, err = _run(["--registry", str(tmp_registry_path), "folders", "scan", "demo_a"], capsys)
    assert code == 3
    assert "demo_a" in err


def test_scan_sem_caminho_absoluto_na_saida(
    tmp_registry_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Nenhuma saída de sucesso de folders scan contém caminho absoluto (FR-010, FR-012)."""
    destino = _add_folder(tmp_registry_path, "demo_a", capsys)
    _, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "scan", "demo_a"], capsys)
    assert str(destino) not in out


# --- US2: scan --all (lote) ----------------------------------------------------------


def test_scan_all_resume_ok_e_falhas(
    tmp_registry_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders scan --all resume quantas pastas foram atualizadas e quantas falharam."""
    _add_folder(tmp_registry_path, "demo_a", capsys)
    _add_folder(tmp_registry_path, "demo_quebrada", capsys).rmdir()
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


# --- status ignore (feature 003) -------------------------------------------------------


def test_scan_all_pula_pasta_ignore_sem_exigir_variavel(
    tmp_registry_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders scan --all pula pasta ignore, sem conferir o caminho dela."""
    _add_folder(tmp_registry_path, "demo_a", capsys)
    _add_folder(tmp_registry_path, "pasta_ignorada", capsys)
    _run(
        [
            "--registry",
            str(tmp_registry_path),
            "folders",
            "update",
            "pasta_ignorada",
            "--status",
            "ignore",
        ],
        capsys,
    )
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "scan", "--all"], capsys)
    assert code == 0
    assert "1 ignoradas" in out


def test_scan_individual_em_alias_ignore_continua_funcionando(
    tmp_registry_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """folders scan <alias> individual sobre um alias ignore não é pulado (FR-013)."""
    _add_folder(tmp_registry_path, "pasta_ignorada", capsys)
    _run(
        [
            "--registry",
            str(tmp_registry_path),
            "folders",
            "update",
            "pasta_ignorada",
            "--status",
            "ignore",
        ],
        capsys,
    )
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "scan", "pasta_ignorada"], capsys
    )
    assert code == 0
    assert "pasta_ignorada" in out


# --- feature 004 / US2: verificação de conteúdo com git real -------------------------

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


def _commit(repo: Path, relpath: str, conteudo: str) -> None:
    arquivo = repo / relpath
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(conteudo, encoding="utf-8")
    _git(repo, "add", "--all")
    _git(repo, "commit", "-q", "-m", f"altera {relpath}")


def _repo(base: Path, nome: str) -> Path:
    repo = base / nome
    repo.mkdir()
    _git(repo, "init", "-q")
    _commit(repo, "README.md", "inicial")
    return repo


def _curar(registry: Path, alias: str, capsys: pytest.CaptureFixture[str]) -> None:
    for status in ("in_curation", "curated"):
        code, _, err = _run(
            ["--registry", str(registry), "folders", "update", alias, "--status", status], capsys
        )
        assert code == 0, err


def test_scan_individual_reverte_e_exibe_conteudo(
    tmp_registry_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Commit na pasta curada → scan exibe status em curadoria e linha conteúdo (FR-018)."""
    repo = _repo(tmp_path, "fonte")
    _add_folder(tmp_registry_path, "fonte", capsys, path=repo)
    _curar(tmp_registry_path, "fonte", capsys)

    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "scan", "fonte"], capsys)
    assert code == 0
    assert "conteúdo: sem mudança" in out

    _commit(repo, "docs/novo.md", "novo")
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "scan", "fonte"], capsys)
    assert code == 0
    assert "status: em curadoria" in out
    assert "conteúdo: mudou — revertida para em curadoria" in out
    assert str(tmp_path) not in out


def test_scan_all_exibe_conteudo_por_linha_e_resumo_de_revertidas(
    tmp_registry_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--all: alias, status e conteúdo por linha + resumo 'revertidas: N' (FR-018, SC-006)."""
    alterada = _repo(tmp_path, "alterada")
    inalterada = _repo(tmp_path, "inalterada")
    solta = tmp_path / "solta"
    solta.mkdir()
    for alias, caminho in (("alterada", alterada), ("inalterada", inalterada), ("solta", solta)):
        _add_folder(tmp_registry_path, alias, capsys, path=caminho)
    _curar(tmp_registry_path, "alterada", capsys)
    _curar(tmp_registry_path, "inalterada", capsys)
    _commit(alterada, "x.txt", "x")

    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "scan", "--all"], capsys)
    assert code == 0
    linhas = {linha.split(" ")[0]: linha for linha in out.splitlines() if " → " in linha}
    assert "em curadoria" in linhas["alterada"]
    assert "mudou — revertida para em curadoria" in linhas["alterada"]
    assert "curada" in linhas["inalterada"] and "sem mudança" in linhas["inalterada"]
    assert "conteúdo: -" in linhas["solta"]
    assert "revertidas: 1 (alterada)" in out
    assert str(tmp_path) not in out


def test_scan_individual_com_git_indisponivel_sai_com_3(
    tmp_registry_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """git ausente durante o scan de pasta curada → exit 3, registro intocado (FR-009)."""
    repo = _repo(tmp_path, "fonte")
    _add_folder(tmp_registry_path, "fonte", capsys, path=repo)
    _curar(tmp_registry_path, "fonte", capsys)
    antes = tmp_registry_path.read_bytes()
    monkeypatch.setenv("PATH", "")
    code, _, err = _run(["--registry", str(tmp_registry_path), "folders", "scan", "fonte"], capsys)
    assert code == 3
    assert "fonte" in err and "git" in err
    assert tmp_registry_path.read_bytes() == antes


# --- feature 004 / US3: legado curado sem versão gravada ------------------------------


def test_legado_recebe_referencia_e_depois_reverte(
    tmp_registry_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """YAML curado sem hash → 'referência registrada'; novo commit → revertida (quickstart C4)."""
    repo = _repo(tmp_path, "fonte")
    tmp_registry_path.write_text(
        "schema_version: '2'\n"
        "folders:\n"
        "  fonte:\n"
        "    description: Fonte legada\n"
        "    content_type: documents\n"
        "    license: MIT\n"
        "    last_scanned: null\n"
        "    status: curated\n"
        f"    path: {repo}\n",
        encoding="utf-8",
    )
    registry_arg = ["--registry", str(tmp_registry_path)]

    code, out, _ = _run([*registry_arg, "folders", "scan", "fonte"], capsys)
    assert code == 0
    assert "conteúdo: referência registrada" in out
    assert "status: curada" in out
    assert "last_curated_commit:" in tmp_registry_path.read_text(encoding="utf-8")

    _commit(repo, "novo.md", "novo")
    code, out, _ = _run([*registry_arg, "folders", "scan", "fonte"], capsys)
    assert "conteúdo: mudou — revertida para em curadoria" in out
