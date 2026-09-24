# -*- coding: utf-8 -*-
"""
NOME: test_cli_bootstrap.py
TITULO: Testes de falha — CLI praxisforge folders bootstrap
DATA: 22/09/2026 18:00
MODIFICADO: 23/09/2026 16:58
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 22/09/2026 18:00: criação (T014)
    - 22/09/2026 18:50: +caso de rerun idempotente (T022, US2)
    - 23/09/2026 16:58: v2, alias <raiz>__<sub>, duas raízes, escala (T029, feature 005)
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


def _registro_vazio(caminho: Path) -> None:
    caminho.write_text("schema_version: '2'\nfolders: {}\n", encoding="utf-8")


def test_bootstrap_registra_subpastas_codigo_0(
    tmp_registry_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders bootstrap <root> com subpastas válidas retorna código 0 e lista as registradas."""
    _registro_vazio(tmp_registry_path)
    raiz = tmp_path / "raiz"
    raiz.mkdir()
    (raiz / "repo_a").mkdir()
    (raiz / "repo_a" / "README.md").write_text("Descrição do repo A.\n", encoding="utf-8")
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "bootstrap", str(raiz)], capsys
    )
    assert code == 0
    assert "raiz__repo_a" in out


def test_bootstrap_raiz_inexistente_codigo_1(
    tmp_registry_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders bootstrap com raiz inexistente retorna código 1 e cita o caminho da raiz."""
    _registro_vazio(tmp_registry_path)
    raiz = tmp_path / "nao-existe"
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "bootstrap", str(raiz)], capsys
    )
    assert code == 1
    assert str(raiz) in err


def test_bootstrap_sem_caminho_absoluto_de_subpasta_na_saida(
    tmp_registry_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nenhuma saída de sucesso contém o caminho absoluto de uma subpasta (FR-014)."""
    _registro_vazio(tmp_registry_path)
    raiz = tmp_path / "raiz"
    raiz.mkdir()
    subpasta = raiz / "repo_a"
    subpasta.mkdir()
    _, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "bootstrap", str(raiz)], capsys
    )
    assert str(subpasta) not in out


def test_rerun_produz_folders_yaml_identico_byte_a_byte(
    tmp_registry_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rodar o bootstrap duas vezes seguidas sem mudança no filesystem não altera folders.yaml
    para as pastas já existentes (SC-002)."""
    _registro_vazio(tmp_registry_path)
    raiz = tmp_path / "raiz"
    raiz.mkdir()
    (raiz / "repo_a").mkdir()
    (raiz / "repo_a" / "README.md").write_text("Descrição do repo A.\n", encoding="utf-8")

    _run(["--registry", str(tmp_registry_path), "folders", "bootstrap", str(raiz)], capsys)
    conteudo_1a_execucao = tmp_registry_path.read_text(encoding="utf-8")

    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "bootstrap", str(raiz)], capsys
    )
    conteudo_2a_execucao = tmp_registry_path.read_text(encoding="utf-8")

    assert code == 0
    assert conteudo_1a_execucao == conteudo_2a_execucao
    assert "1 já existentes" in out


def test_bootstrap_sem_registro_previo_funciona(
    tmp_registry_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Primeira execução sem folders.yaml prévio funciona (registro tratado como vazio)."""
    raiz = tmp_path / "raiz"
    raiz.mkdir()
    (raiz / "repo_a").mkdir()
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "bootstrap", str(raiz)], capsys
    )
    assert code == 0
    assert "repo_a" in out
    assert tmp_registry_path.exists()


# --- feature 005 -----------------------------------------------------------------------


def test_duas_raizes_com_subpasta_homonima_sem_colisao(
    tmp_registry_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Bootstrap em duas raízes com 'graphify' registra ambas; saída só com aliases (SC-001)."""
    raizes = []
    for nome in ("r1", "r2"):
        raiz = tmp_path / nome
        (raiz / "graphify").mkdir(parents=True)
        raizes.append(raiz)
    saidas = []
    for raiz in raizes:
        code, out, _ = _run(
            ["--registry", str(tmp_registry_path), "folders", "bootstrap", str(raiz)], capsys
        )
        assert code == 0
        saidas.append(out)
    assert "r1__graphify" in saidas[0] and "r2__graphify" in saidas[1]
    assert all(str(tmp_path) not in out for out in saidas)
    texto = tmp_registry_path.read_text(encoding="utf-8")
    assert f"path: {(raizes[0] / 'graphify').resolve()}" in texto
    assert f"path: {(raizes[1] / 'graphify').resolve()}" in texto


def test_bootstrap_de_100_subpastas_em_menos_de_5s(
    tmp_registry_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Escala: 100 subpastas registradas em < 5 s (Plan §Performance)."""
    raiz = tmp_path / "grande"
    for i in range(100):
        (raiz / f"repo_{i:03d}").mkdir(parents=True)
    inicio = time.perf_counter()
    code, out, _ = _run(
        ["--registry", str(tmp_registry_path), "folders", "bootstrap", str(raiz)], capsys
    )
    assert time.perf_counter() - inicio < 5.0
    assert code == 0
    assert "100 registradas" in out
