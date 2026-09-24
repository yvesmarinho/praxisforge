# -*- coding: utf-8 -*-
"""
NOME: test_filesystem_registry_mover.py
TITULO: Testes de falha — adapter FilesystemRegistryMover com arquivos reais
DATA: 24/09/2026 14:34
MODIFICADO: 24/09/2026 14:34
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.filesystem_registry_mover
HISTÓRICO:
    - 24/09/2026 14:34: criação (T025, US3, feature 007)
STATUS: DEV
"""

import os
from pathlib import Path

import pytest

from praxisforge.application.ports import RegistryFileMover
from praxisforge.domain.errors import RegistryRelocationError
from praxisforge.infrastructure import filesystem_registry_mover
from praxisforge.infrastructure.filesystem_registry_mover import FilesystemRegistryMover

_CONTEUDO = "# comentário preservado\nschema_version: '2'\nfolders: {}\n".encode()


def _origem(tmp_path: Path) -> Path:
    origem = tmp_path / "repo" / "src" / "data" / "folders.yaml"
    origem.parent.mkdir(parents=True)
    origem.write_bytes(_CONTEUDO)
    return origem


def test_move_preservando_bytes_e_cria_pasta(tmp_path: Path) -> None:
    """Destino idêntico byte a byte; pasta criada; origem removida (FR-009)."""
    origem = _origem(tmp_path)
    destino = tmp_path / "cfg" / "praxisforge" / "folders.yaml"
    mover = FilesystemRegistryMover()
    assert isinstance(mover, RegistryFileMover)
    mover.move(origem, destino)
    assert destino.read_bytes() == _CONTEUDO
    assert not origem.exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignora permissões")
def test_destino_sem_permissao_preserva_origem(tmp_path: Path) -> None:
    """Sem permissão de escrita → RegistryRelocationError; origem intacta; nada no destino."""
    origem = _origem(tmp_path)
    bloqueada = tmp_path / "cfg"
    bloqueada.mkdir()
    bloqueada.chmod(0o500)
    try:
        with pytest.raises(RegistryRelocationError):
            FilesystemRegistryMover().move(origem, bloqueada / "praxisforge" / "folders.yaml")
    finally:
        bloqueada.chmod(0o700)
    assert origem.read_bytes() == _CONTEUDO
    assert list(bloqueada.iterdir()) == []


def test_falha_na_verificacao_remove_parcial_e_preserva_origem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cópia divergente → nenhum arquivo no destino e origem intacta (FR-013)."""
    origem = _origem(tmp_path)
    destino = tmp_path / "cfg" / "folders.yaml"
    monkeypatch.setattr(filesystem_registry_mover, "_iguais", lambda a, b: False)
    with pytest.raises(RegistryRelocationError):
        FilesystemRegistryMover().move(origem, destino)
    assert origem.read_bytes() == _CONTEUDO
    assert not destino.exists()
    assert [p for p in destino.parent.iterdir()] == []
