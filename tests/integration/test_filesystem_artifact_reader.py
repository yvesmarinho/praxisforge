# -*- coding: utf-8 -*-
"""
NOME: test_filesystem_artifact_reader.py
TITULO: Testes de falha — leitura do conteúdo de um artefato da pasta curada (feature 011)
DATA: 28/09/2026 15:59
MODIFICADO: 28/09/2026 15:59
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.filesystem_artifact_reader
HISTÓRICO:
    - 28/09/2026 15:59: criação (T023, feature 011)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.domain.errors import ArtifactTooLargeError, FolderPathInvalidError
from praxisforge.infrastructure.filesystem_artifact_reader import (
    ARTIFACT_LIMIT,
    FilesystemArtifactReader,
)


def _pasta(tmp_path: Path) -> Path:
    pasta = tmp_path / "fork"
    (pasta / "skills" / "tdd" / "references").mkdir(parents=True)
    (pasta / "skills" / "tdd" / "SKILL.md").write_text("# TDD principal", encoding="utf-8")
    (pasta / "skills" / "tdd" / "a-apoio.md").write_text("apoio A", encoding="utf-8")
    (pasta / "skills" / "tdd" / "references" / "b.md").write_text("apoio B", encoding="utf-8")
    (pasta / "skills" / "tdd" / "logo.png").write_bytes(b"\x89PNG\x00\x00")
    (pasta / "README.md").write_text("leia-me", encoding="utf-8")
    return pasta


def test_arquivo_unico(tmp_path: Path) -> None:
    assert FilesystemArtifactReader().read(_pasta(tmp_path), "README.md") == "leia-me"


def test_diretorio_principal_primeiro_e_apoio_por_caminho(tmp_path: Path) -> None:
    texto = FilesystemArtifactReader().read(_pasta(tmp_path), "skills/tdd")
    assert texto.index("# TDD principal") < texto.index("apoio A") < texto.index("apoio B")
    assert "=== SKILL.md ===" in texto and "=== references/b.md ===" in texto
    assert "PNG" not in texto and "logo.png" not in texto


def test_acima_do_limite_nao_trunca(tmp_path: Path) -> None:
    pasta = _pasta(tmp_path)
    (pasta / "skills" / "tdd" / "c.md").write_text("x" * ARTIFACT_LIMIT, encoding="utf-8")
    with pytest.raises(ArtifactTooLargeError, match="tamanho"):
        FilesystemArtifactReader().read(pasta, "skills/tdd")


@pytest.mark.parametrize("caminho", ["../fora.md", "nao-existe.md", "/etc/passwd"])
def test_caminho_invalido(tmp_path: Path, caminho: str) -> None:
    (tmp_path / "fora.md").write_text("fora", encoding="utf-8")
    with pytest.raises(FolderPathInvalidError):
        FilesystemArtifactReader().read(_pasta(tmp_path), caminho)


def test_link_simbolico_para_fora_e_ignorado(tmp_path: Path) -> None:
    pasta = _pasta(tmp_path)
    (tmp_path / "segredo.md").write_text("SEGREDO", encoding="utf-8")
    (pasta / "skills" / "tdd" / "link.md").symlink_to(tmp_path / "segredo.md")
    assert "SEGREDO" not in FilesystemArtifactReader().read(pasta, "skills/tdd")
    (pasta / "atalho.md").symlink_to(tmp_path / "segredo.md")
    with pytest.raises(FolderPathInvalidError):
        FilesystemArtifactReader().read(pasta, "atalho.md")


def test_nenhuma_escrita(tmp_path: Path) -> None:
    pasta = _pasta(tmp_path)
    antes = sorted((p, p.stat().st_mtime_ns) for p in pasta.rglob("*"))
    FilesystemArtifactReader().read(pasta, "skills/tdd")
    assert sorted((p, p.stat().st_mtime_ns) for p in pasta.rglob("*")) == antes
