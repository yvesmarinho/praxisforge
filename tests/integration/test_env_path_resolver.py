# -*- coding: utf-8 -*-
"""
NOME: test_env_path_resolver.py
TITULO: Testes de falha — adapter EnvPathResolver (Infrastructure)
DATA: 22/09/2026 10:10
MODIFICADO: 22/09/2026 10:01
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.env_path_resolver
HISTÓRICO:
    - 22/09/2026 10:10: criação (T041)
STATUS: DEV
"""

import logging
import os
import stat
from pathlib import Path

import pytest

from praxisforge.domain.errors import (
    FolderPathInvalidError,
    FolderPathNotConfiguredError,
    FolderPathUnreadableError,
)
from praxisforge.infrastructure.env_path_resolver import EnvPathResolver


def test_variavel_ausente_levanta_erro_com_nome(env_folder: object) -> None:
    """Variável ausente levanta FolderPathNotConfiguredError citando o nome da variável."""
    env_folder.unset("github_forks")  # type: ignore[attr-defined]
    resolver = EnvPathResolver()
    with pytest.raises(FolderPathNotConfiguredError) as excinfo:
        resolver.resolve("github_forks")
    assert "PRAXISFORGE_FOLDER_GITHUB_FORKS" in str(excinfo.value)


def test_variavel_vazia_levanta_erro(env_folder: object) -> None:
    """Variável vazia é tratada como ausente."""
    env_folder.set("github_forks", "")  # type: ignore[attr-defined]
    resolver = EnvPathResolver()
    with pytest.raises(FolderPathNotConfiguredError):
        resolver.resolve("github_forks")


def test_caminho_relativo_levanta_erro(env_folder: object) -> None:
    """Caminho relativo é inválido."""
    env_folder.set("github_forks", "relativo/pasta")  # type: ignore[attr-defined]
    resolver = EnvPathResolver()
    with pytest.raises(FolderPathInvalidError):
        resolver.resolve("github_forks")


def test_caminho_com_dotdot_levanta_erro(env_folder: object, tmp_path: Path) -> None:
    """Caminho com '..' é inválido."""
    env_folder.set("github_forks", str(tmp_path / ".." / "x"))  # type: ignore[attr-defined]
    resolver = EnvPathResolver()
    with pytest.raises(FolderPathInvalidError):
        resolver.resolve("github_forks")


def test_caminho_inexistente_levanta_erro(env_folder: object, tmp_path: Path) -> None:
    """Caminho inexistente é inválido."""
    env_folder.set("github_forks", str(tmp_path / "nao_existe"))  # type: ignore[attr-defined]
    resolver = EnvPathResolver()
    with pytest.raises(FolderPathInvalidError):
        resolver.resolve("github_forks")


def test_caminho_eh_arquivo_nao_diretorio_levanta_erro(env_folder: object, tmp_path: Path) -> None:
    """Caminho que aponta para um arquivo (não diretório) é inválido."""
    arquivo = tmp_path / "arquivo.txt"
    arquivo.write_text("x", encoding="utf-8")
    env_folder.set("github_forks", str(arquivo))  # type: ignore[attr-defined]
    resolver = EnvPathResolver()
    with pytest.raises(FolderPathInvalidError):
        resolver.resolve("github_forks")


def test_sem_permissao_levanta_erro(env_folder: object, tmp_path: Path) -> None:
    """Diretório sem permissão de leitura levanta FolderPathUnreadableError."""
    destino = tmp_path / "sem_permissao"
    destino.mkdir()
    env_folder.set("github_forks", str(destino))  # type: ignore[attr-defined]
    destino.chmod(0o000)
    try:
        if os.access(destino, os.R_OK | os.X_OK):
            pytest.skip("ambiente executa como root; permissão não é aplicável")
        resolver = EnvPathResolver()
        with pytest.raises(FolderPathUnreadableError):
            resolver.resolve("github_forks")
    finally:
        destino.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def test_link_simbolico_valido_eh_seguido(env_folder: object, tmp_path: Path) -> None:
    """Link simbólico válido é seguido e o destino real é devolvido."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    env_folder.set("github_forks", str(link))  # type: ignore[attr-defined]
    resolver = EnvPathResolver()
    resolved = resolver.resolve("github_forks")
    assert resolved == real.resolve()


def test_link_simbolico_quebrado_levanta_erro(env_folder: object, tmp_path: Path) -> None:
    """Link simbólico quebrado (destino inexistente) é inválido."""
    link = tmp_path / "link_quebrado"
    link.symlink_to(tmp_path / "inexistente")
    env_folder.set("github_forks", str(link))  # type: ignore[attr-defined]
    resolver = EnvPathResolver()
    with pytest.raises(FolderPathInvalidError):
        resolver.resolve("github_forks")


def test_mensagem_cita_so_o_alias_em_questao(env_folder: object) -> None:
    """Mensagens de erro citam só o alias em questão, nunca outros aliases/caminhos."""
    env_folder.unset("outra_pasta")  # type: ignore[attr-defined]
    resolver = EnvPathResolver()
    with pytest.raises(FolderPathNotConfiguredError) as excinfo:
        resolver.resolve("outra_pasta")
    assert "outra_pasta" in str(excinfo.value)
    assert "github_forks" not in str(excinfo.value)


def test_log_estruturado_sem_caminho_absoluto(
    env_folder: object, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A resolução emite log estruturado (evento, alias, resultado) sem caminho absoluto."""
    destino = tmp_path / "real"
    destino.mkdir()
    env_folder.set("github_forks", str(destino))  # type: ignore[attr-defined]
    resolver = EnvPathResolver()
    with caplog.at_level(logging.INFO):
        resolver.resolve("github_forks")
    assert caplog.records
    for record in caplog.records:
        assert str(destino) not in record.message
