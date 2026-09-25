# -*- coding: utf-8 -*-
"""
NOME: test_filesystem_folder_walker.py
TITULO: Testes de falha — varredura somente leitura de uma pasta para o inventário (feature 010)
DATA: 25/09/2026 15:02
MODIFICADO: 25/09/2026 14:52
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.filesystem_folder_walker
HISTÓRICO:
    - 25/09/2026 15:02: criação (T012, feature 010)
STATUS: DEV
"""

import hashlib
import os
from pathlib import Path

import pytest

from praxisforge.application.ports import FolderWalk
from praxisforge.domain.curation_artifact import ExclusionReason
from praxisforge.domain.errors import FolderPathInvalidError
from praxisforge.infrastructure.filesystem_folder_walker import (
    MAX_FILE_SIZE,
    FilesystemFolderWalker,
)


def _escrever(raiz: Path, rel: str, conteudo: bytes | str = "x") -> Path:
    alvo = raiz / rel
    alvo.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(conteudo, str):
        conteudo = conteudo.encode()
    alvo.write_bytes(conteudo)
    return alvo


def _walk(raiz: Path) -> FolderWalk:
    return FilesystemFolderWalker().walk(raiz)


def _arquivos(walk: FolderWalk) -> list[str]:
    return [f.path for f in walk.files]


def _exclusoes(walk: FolderWalk) -> dict[str, ExclusionReason]:
    return {e.path: e.reason for e in walk.excluded}


def test_lista_arquivos_ordenados_com_hash_e_tamanho(tmp_path: Path) -> None:
    _escrever(tmp_path, "b.md", "bb")
    _escrever(tmp_path, "a/z.md", "z")
    walk = _walk(tmp_path)
    assert _arquivos(walk) == ["a/z.md", "b.md"]
    b = walk.files[1]
    assert (b.size, b.sha256) == (2, hashlib.sha256(b"bb").hexdigest())


@pytest.mark.parametrize(
    "diretorio", [".git", "node_modules", ".venv", "__pycache__", "dist", "build", "graphify-out"]
)
def test_lista_fixa_em_qualquer_nivel(tmp_path: Path, diretorio: str) -> None:
    _escrever(tmp_path, f"{diretorio}/x.md")
    _escrever(tmp_path, f"sub/{diretorio}/y.md")
    walk = _walk(tmp_path)
    assert _arquivos(walk) == []
    assert _exclusoes(walk) == {
        diretorio: ExclusionReason.FIXED_DIR,
        f"sub/{diretorio}": ExclusionReason.FIXED_DIR,
    }
    assert all(e.is_dir for e in walk.excluded)


def test_gitignore_raiz_aninhado_e_negacao(tmp_path: Path) -> None:
    _escrever(tmp_path, ".gitignore", "*.log\n!keep.log\ntmp/\n")
    _escrever(tmp_path, "a.log")
    _escrever(tmp_path, "keep.log")
    _escrever(tmp_path, "tmp/x.md")
    _escrever(tmp_path, "sub/.gitignore", "segredo.md\n")
    _escrever(tmp_path, "sub/segredo.md")
    _escrever(tmp_path, "segredo.md")  # regra do filho não vale para o pai
    walk = _walk(tmp_path)
    assert _exclusoes(walk) == {
        "a.log": ExclusionReason.GITIGNORE,
        "tmp": ExclusionReason.GITIGNORE,
        "sub/segredo.md": ExclusionReason.GITIGNORE,
    }
    assert "keep.log" in _arquivos(walk)
    assert "segredo.md" in _arquivos(walk)


def test_limite_de_tamanho_exato(tmp_path: Path) -> None:
    assert MAX_FILE_SIZE == 262_144
    _escrever(tmp_path, "limite.md", b"a" * MAX_FILE_SIZE)
    _escrever(tmp_path, "grande.md", b"a" * (MAX_FILE_SIZE + 1))
    walk = _walk(tmp_path)
    assert _arquivos(walk) == ["limite.md"]
    assert _exclusoes(walk) == {"grande.md": ExclusionReason.TOO_LARGE}


def test_binario(tmp_path: Path) -> None:
    _escrever(tmp_path, "img.png", b"\x89PNG\x00\x01")
    assert _exclusoes(_walk(tmp_path)) == {"img.png": ExclusionReason.BINARY}


def test_links_simbolicos(tmp_path: Path) -> None:
    raiz = tmp_path / "raiz"
    fora = _escrever(tmp_path, "fora.md")
    dentro = _escrever(raiz, "real.md", "r")
    (raiz / "para_fora.md").symlink_to(fora)
    (raiz / "para_dentro.md").symlink_to(dentro)
    (raiz / "dir_link").symlink_to(raiz / "sub", target_is_directory=True)
    (raiz / "sub").mkdir()
    (raiz / "quebrado.md").symlink_to(raiz / "nao_existe.md")
    walk = _walk(raiz)
    assert _exclusoes(walk) == {
        "para_fora.md": ExclusionReason.SYMLINK_OUTSIDE,
        "dir_link": ExclusionReason.SYMLINK_DIR,
        "quebrado.md": ExclusionReason.UNREADABLE,
    }
    assert _arquivos(walk) == ["para_dentro.md", "real.md"]


def test_ciclo_de_links_nao_trava(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "volta").symlink_to(tmp_path, target_is_directory=True)
    walk = _walk(tmp_path)
    assert _exclusoes(walk) == {"a/volta": ExclusionReason.SYMLINK_DIR}


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignora permissões")
def test_ilegivel_nao_interrompe(tmp_path: Path) -> None:
    trancado = _escrever(tmp_path, "trancado.md")
    _escrever(tmp_path, "ok.md")
    pasta = tmp_path / "pasta_trancada"
    _escrever(pasta, "x.md")
    trancado.chmod(0)
    pasta.chmod(0)
    try:
        walk = _walk(tmp_path)
    finally:
        trancado.chmod(0o600)
        pasta.chmod(0o700)
    assert _exclusoes(walk) == {
        "trancado.md": ExclusionReason.UNREADABLE,
        "pasta_trancada": ExclusionReason.UNREADABLE,
    }
    assert _arquivos(walk) == ["ok.md"]


def test_pasta_inexistente(tmp_path: Path) -> None:
    with pytest.raises(FolderPathInvalidError):
        _walk(tmp_path / "nao_existe")


def test_somente_leitura(tmp_path: Path) -> None:
    """FR-008: nada é escrito na pasta (mtimes e listagem intactos)."""
    _escrever(tmp_path, ".gitignore", "*.log\n")
    _escrever(tmp_path, "a/b.md")
    antes = {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*")}
    _walk(tmp_path)
    assert {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*")} == antes
