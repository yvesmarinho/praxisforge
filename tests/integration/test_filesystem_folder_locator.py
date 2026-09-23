# -*- coding: utf-8 -*-
"""
NOME: test_filesystem_folder_locator.py
TITULO: Testes de integração — FilesystemFolderLocator (canonização e checagem de pastas reais)
DATA: 23/09/2026 16:48
MODIFICADO: 23/09/2026 16:48
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.filesystem_folder_locator
HISTÓRICO:
    - 23/09/2026 16:48: criação (T007, feature 005-caminho-absoluto-registro)
STATUS: DEV
"""

import os
import stat
from pathlib import Path

import pytest

from praxisforge.domain.errors import FolderPathInvalidError, FolderPathUnreadableError
from praxisforge.infrastructure.filesystem_folder_locator import FilesystemFolderLocator


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    destino = tmp_path / "fontes" / "repo"
    destino.mkdir(parents=True)
    return destino


def test_canonicalize_absoluto_devolve_o_mesmo(pasta: Path) -> None:
    """Caminho absoluto já canônico volta igual (FR-002)."""
    assert FilesystemFolderLocator().canonicalize("repo", str(pasta)) == pasta.resolve()


def test_canonicalize_expande_til(pasta: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ "~" é expandido para a pasta pessoal (FR-002)."""
    monkeypatch.setenv("HOME", str(pasta.parent))
    assert FilesystemFolderLocator().canonicalize("repo", "~/repo") == pasta.resolve()


def test_canonicalize_relativo_a_partir_do_cwd(
    pasta: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Relativo é resolvido a partir da pasta atual (US1 cenário 2)."""
    monkeypatch.chdir(pasta.parent)
    assert FilesystemFolderLocator().canonicalize("repo", "repo") == pasta.resolve()


def test_canonicalize_elimina_ponto_ponto(pasta: Path) -> None:
    """Segmentos '..' e '.' são eliminados."""
    bruto = f"{pasta.parent}/./outra/../repo"
    (pasta.parent / "outra").mkdir()
    assert FilesystemFolderLocator().canonicalize("repo", bruto) == pasta.resolve()


def test_canonicalize_resolve_link_simbolico(pasta: Path, tmp_path: Path) -> None:
    """Link simbólico é gravado pelo destino real (Edge Cases)."""
    link = tmp_path / "atalho"
    link.symlink_to(pasta)
    assert FilesystemFolderLocator().canonicalize("repo", str(link)) == pasta.resolve()


def test_canonicalize_remove_barra_final(pasta: Path) -> None:
    """Barra final não sobrevive."""
    resultado = FilesystemFolderLocator().canonicalize("repo", f"{pasta}/")
    assert not str(resultado).endswith("/")


def test_inexistente_levanta_erro_com_alias(tmp_path: Path) -> None:
    """Caminho inexistente → FolderPathInvalidError citando o alias (FR-004)."""
    with pytest.raises(FolderPathInvalidError) as info:
        FilesystemFolderLocator().canonicalize("repo", str(tmp_path / "nao_existe"))
    assert "repo" in str(info.value)


def test_arquivo_nao_eh_pasta(tmp_path: Path) -> None:
    """Arquivo comum não é pasta (FR-004)."""
    arquivo = tmp_path / "arquivo.txt"
    arquivo.write_text("x", encoding="utf-8")
    with pytest.raises(FolderPathInvalidError):
        FilesystemFolderLocator().canonicalize("repo", str(arquivo))


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignora permissões")
def test_sem_permissao_de_listar_levanta_unreadable(pasta: Path) -> None:
    """Sem permissão de listar/entrar → FolderPathUnreadableError (FR-004)."""
    pasta.chmod(0)
    try:
        with pytest.raises(FolderPathUnreadableError):
            FilesystemFolderLocator().canonicalize("repo", str(pasta))
    finally:
        pasta.chmod(stat.S_IRWXU)


def test_check_devolve_caminho_acessivel(pasta: Path) -> None:
    """check confirma uma pasta registrada acessível."""
    assert FilesystemFolderLocator().check("repo", pasta) == pasta


def test_check_pasta_movida_levanta_erro_so_com_o_proprio_caminho(
    pasta: Path, tmp_path: Path
) -> None:
    """Pasta movida → erro com alias; mensagem não cita outros caminhos (FR-012)."""
    pasta.rename(tmp_path / "movida")
    with pytest.raises(FolderPathInvalidError) as info:
        FilesystemFolderLocator().check("repo", pasta)
    assert "repo" in str(info.value)
    assert str(tmp_path / "movida") not in str(info.value)
