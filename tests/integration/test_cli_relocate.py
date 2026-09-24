# -*- coding: utf-8 -*-
"""
NOME: test_cli_relocate.py
TITULO: Testes de falha — CLI praxisforge folders relocate e dica de registro antigo
DATA: 24/09/2026 14:34
MODIFICADO: 24/09/2026 14:34
VERSÃO: 0.1.0
DEPEND: pytest, pyyaml, praxisforge.presentation.cli
HISTÓRICO:
    - 24/09/2026 14:34: criação (T026/T027, US3, feature 007)
STATUS: DEV
"""

import os
import shutil
import time
from pathlib import Path

import pytest
import yaml

from praxisforge.presentation.cli import main

_RAIZ_PROJETO = Path(__file__).parents[2]
_DICA = (
    "registro antigo encontrado em src/data/folders.yaml — execute: praxisforge folders relocate"
)


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture
def projeto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Diretório de trabalho temporário com schemas/ (a CLI resolve schemas pelo cwd)."""
    raiz = tmp_path / "projeto"
    shutil.copytree(_RAIZ_PROJETO / "schemas", raiz / "schemas")
    monkeypatch.chdir(raiz)
    return raiz


def _legado(raiz: Path, n: int) -> Path:
    pastas = {
        f"pasta_{i:03d}": {
            "content_type": "documents",
            "description": "d",
            "last_scanned": None,
            "license": "MIT",
            "path": f"/srv/pastas/p{i:03d}",
            "status": "not_scanned",
        }
        for i in range(n)
    }
    arquivo = raiz / "src" / "data" / "folders.yaml"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(
        yaml.safe_dump({"schema_version": "2", "folders": pastas}, sort_keys=True),
        encoding="utf-8",
    )
    return arquivo


def _padrao(tmp_path: Path) -> Path:
    return tmp_path / "xdg" / "praxisforge" / "folders.yaml"


def test_dica_de_registro_antigo_em_comando_de_leitura(
    projeto: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Registro ausente + legado com pastas → dica no stderr (FR-008)."""
    _legado(projeto, 2)
    code, _, err = _run(["folders", "list"], capsys)
    assert code == 1
    assert _DICA in err


def test_legado_vazio_nao_gera_dica(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Legado sem pastas não gera dica."""
    _legado(projeto, 0)
    _, _, err = _run(["folders", "list"], capsys)
    assert _DICA not in err


def test_relocate_move_e_recusa_na_segunda_vez(
    projeto: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Move com conteúdo idêntico, remove a origem; repetir → exit 1 (destino existe)."""
    origem = _legado(projeto, 3)
    conteudo = origem.read_bytes()
    code, out, err = _run(["folders", "relocate"], capsys)
    assert code == 0, err
    assert f"registro movido para {_padrao(tmp_path)} (3 pastas)" in out
    assert _padrao(tmp_path).read_bytes() == conteudo
    assert not origem.exists()
    code, out, _ = _run(["folders", "list"], capsys)
    assert code == 0 and out.count("\n") == 3

    _legado(projeto, 1)
    code, out, err = _run(["folders", "relocate"], capsys)
    assert code == 1
    assert str(_padrao(tmp_path)) in out + err


def test_relocate_com_from_e_registry(
    projeto: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--from escolhe a origem; --registry define o destino."""
    origem = _legado(projeto, 2).rename(projeto / "outro.yaml")
    destino = tmp_path / "destino" / "reg.yaml"
    code, _, err = _run(
        ["--registry", str(destino), "folders", "relocate", "--from", str(origem)], capsys
    )
    assert code == 0, err
    assert destino.is_file() and not origem.exists()


def test_relocate_destino_pela_variavel(
    projeto: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PRAXISFORGE_REGISTRY define o destino."""
    destino = tmp_path / "var" / "reg.yaml"
    monkeypatch.setenv("PRAXISFORGE_REGISTRY", str(destino))
    _legado(projeto, 1)
    code, _, err = _run(["folders", "relocate"], capsys)
    assert code == 0, err
    assert destino.is_file()


@pytest.mark.parametrize("n", [0])
def test_relocate_origem_vazia_codigo_1(
    projeto: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], n: int
) -> None:
    """Origem sem pastas → exit 1; nada muda."""
    origem = _legado(projeto, n)
    code, out, err = _run(["folders", "relocate"], capsys)
    assert code == 1
    assert "sem pastas" in out + err
    assert origem.exists() and not _padrao(tmp_path).exists()


def test_relocate_origem_ausente_codigo_1(
    projeto: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sem origem → exit 1 citando a origem."""
    code, out, err = _run(["folders", "relocate"], capsys)
    assert code == 1
    assert "src/data/folders.yaml" in out + err


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignora permissões")
def test_relocate_sem_permissao_codigo_3(
    projeto: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Destino sem permissão de escrita → exit 3; origem intacta."""
    origem = _legado(projeto, 1)
    bloqueada = tmp_path / "bloqueada"
    bloqueada.mkdir()
    bloqueada.chmod(0o500)
    try:
        code, _, _ = _run(
            ["--registry", str(bloqueada / "sub" / "reg.yaml"), "folders", "relocate"], capsys
        )
    finally:
        bloqueada.chmod(0o700)
    assert code == 3
    assert origem.exists()


def test_relocate_60_pastas_em_menos_de_1s(
    projeto: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Escala (SC-003)."""
    _legado(projeto, 60)
    inicio = time.perf_counter()
    code, out, err = _run(["folders", "relocate"], capsys)
    assert time.perf_counter() - inicio < 1.0
    assert code == 0, err
    assert "(60 pastas)" in out
