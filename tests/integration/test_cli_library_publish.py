# -*- coding: utf-8 -*-
"""
NOME: test_cli_library_publish.py
TITULO: Testes de integração — praxisforge library publish e remoção dos comandos skills
DATA: 25/09/2026 13:19
MODIFICADO: 25/09/2026 13:19
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 25/09/2026 13:19: criação (T034, feature 009) — sucede test_cli_skills_publish.py
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.presentation.cli import main
from tests.library_helpers import criar_projeto, escrever_item


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = criar_projeto(tmp_path / "repo")
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def app(tmp_path: Path) -> Path:
    destino = tmp_path / "app"
    destino.mkdir()
    return destino


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _arquivos(raiz: Path) -> set[str]:
    return {str(p.relative_to(raiz)) for p in raiz.rglob("*")}


def test_publica_tudo_e_so_escreve_no_projeto(
    repo: Path, app: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--all publica em <app>/.claude/ e nada é escrito fora dele nem no acervo (SC-006)."""
    escrever_item(repo, "skill", "s")
    escrever_item(repo, "command", "c")
    escrever_item(repo, "hook", "h")
    antes_repo = _arquivos(repo)
    code, out, _ = _run(["library", "publish", "--all", "--target", str(app)], capsys)
    assert code == 0
    assert "skill/s → publicada" in out
    assert "command/c → publicada" in out
    assert "hook/h" not in out
    assert _arquivos(repo) == antes_repo
    assert {p.split("/")[0] for p in _arquivos(app)} == {".claude"}
    code, out, _ = _run(["library", "publish", "--all", "--target", str(app)], capsys)
    assert (code, "2 inalteradas" in out) == (0, True)


def test_um_item(repo: Path, app: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--type + nome publica um item."""
    escrever_item(repo, "agent", "a")
    code, out, _ = _run(
        ["library", "publish", "--type", "agent", "a", "--target", str(app)], capsys
    )
    assert code == 0
    assert (app / ".claude" / "agents" / "a.md").is_file()


def test_alvo_global_removido(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--target global → código 2 explicando que só projetos são alvo (FR-018)."""
    code, _, err = _run(["library", "publish", "--all", "--target", "global"], capsys)
    assert code == 2
    assert "só em pastas de projeto" in err


@pytest.mark.parametrize("tipo", ["hook", "reference"])
def test_tipo_nao_publicavel(
    repo: Path, app: Path, capsys: pytest.CaptureFixture[str], tipo: str
) -> None:
    """Pedir hook ou reference → código 2 com o motivo."""
    escrever_item(repo, tipo, "x")
    code, _, err = _run(["library", "publish", "--type", tipo, "x", "--target", str(app)], capsys)
    assert code == 2
    assert "não é publicável" in err


@pytest.mark.parametrize(
    "argv",
    [
        ["library", "publish", "--target", "APP"],
        ["library", "publish", "--all", "--type", "skill", "s", "--target", "APP"],
        ["library", "publish", "--type", "skill", "--target", "APP"],
        ["library", "publish", "--type", "skill", "s", "--prune", "--target", "APP"],
        ["library", "publish", "--all", "--target", "APP", "--mode", "zip"],
    ],
    ids=["sem-item", "all-e-item", "tipo-sem-nome", "prune-sem-all", "modo-invalido"],
)
def test_uso_incorreto(
    repo: Path, app: Path, capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    """Combinações inválidas → código 2."""
    argv = [str(app) if a == "APP" else a for a in argv]
    try:
        code, _, _ = _run(argv, capsys)
    except SystemExit as saida:
        code = int(saida.code or 0)
    assert code == 2


def test_projeto_inexistente(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pasta de projeto inexistente → código 2."""
    code, _, err = _run(["library", "publish", "--all", "--target", str(tmp_path / "nada")], capsys)
    assert code == 2
    assert "não existe" in err


def test_recusa_codigo_1(repo: Path, app: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Item de terceiro no destino → recusada e código 1."""
    escrever_item(repo, "rule", "r")
    destino = app / ".claude" / "rules"
    destino.mkdir(parents=True)
    (destino / "r.md").write_text("meu\n", encoding="utf-8")
    code, out, _ = _run(["library", "publish", "--all", "--target", str(app)], capsys)
    assert code == 1
    assert "rule/r → recusada" in out


@pytest.mark.parametrize(
    ("sub", "equivalente"),
    [
        ("validate", "library validate"),
        ("catalog", "library index"),
        ("publish", "library publish"),
    ],
)
def test_comandos_skills_removidos(
    repo: Path, capsys: pytest.CaptureFixture[str], sub: str, equivalente: str
) -> None:
    """skills validate|catalog|publish → código 2 indicando o equivalente (FR-017a)."""
    code, _, err = _run(["skills", sub], capsys)
    assert code == 2
    assert f"use: praxisforge {equivalente}" in err
