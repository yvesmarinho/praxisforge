# -*- coding: utf-8 -*-
"""
NOME: test_filesystem_folder_probe.py
TITULO: Testes de falha — adapter FilesystemFolderProbe (Infrastructure)
DATA: 22/09/2026 17:50
MODIFICADO: 22/09/2026 16:41
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.filesystem_folder_probe
HISTÓRICO:
    - 22/09/2026 17:50: criação (T012)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.domain.errors import InvalidRootPathError
from praxisforge.infrastructure.filesystem_folder_probe import FilesystemFolderProbe

# --- list_subfolders ------------------------------------------------------------------


def test_list_subfolders_so_diretorios_ordenados(tmp_path: Path) -> None:
    """Só diretórios de primeiro nível, ordenados alfabeticamente; arquivo solto é ignorado."""
    (tmp_path / "zebra").mkdir()
    (tmp_path / "abelha").mkdir()
    (tmp_path / "arquivo.txt").write_text("x", encoding="utf-8")
    probe = FilesystemFolderProbe()
    resultado = probe.list_subfolders(tmp_path)
    assert [p.name for p in resultado] == ["abelha", "zebra"]


def test_list_subfolders_segue_link_simbolico(tmp_path: Path) -> None:
    """Link simbólico válido para um diretório aparece na listagem."""
    destino = tmp_path / "destino"
    destino.mkdir()
    (tmp_path / "link").symlink_to(destino)
    probe = FilesystemFolderProbe()
    resultado = probe.list_subfolders(tmp_path)
    assert "link" in [p.name for p in resultado]


def test_list_subfolders_ignora_link_quebrado(tmp_path: Path) -> None:
    """Link simbólico quebrado é ignorado silenciosamente, sem levantar."""
    (tmp_path / "quebrado").symlink_to(tmp_path / "nao-existe")
    probe = FilesystemFolderProbe()
    resultado = probe.list_subfolders(tmp_path)
    assert "quebrado" not in [p.name for p in resultado]


def test_list_subfolders_raiz_inexistente_levanta_erro(tmp_path: Path) -> None:
    """Raiz inexistente levanta InvalidRootPathError."""
    probe = FilesystemFolderProbe()
    with pytest.raises(InvalidRootPathError):
        probe.list_subfolders(tmp_path / "nao-existe")


def test_list_subfolders_raiz_nao_e_diretorio_levanta_erro(tmp_path: Path) -> None:
    """Raiz que é um arquivo (não diretório) levanta InvalidRootPathError."""
    arquivo = tmp_path / "arquivo.txt"
    arquivo.write_text("x", encoding="utf-8")
    probe = FilesystemFolderProbe()
    with pytest.raises(InvalidRootPathError):
        probe.list_subfolders(arquivo)


def test_list_subfolders_sem_permissao_levanta_erro(tmp_path: Path) -> None:
    """Raiz sem permissão de leitura levanta InvalidRootPathError."""
    raiz = tmp_path / "sem-permissao"
    raiz.mkdir()
    raiz.chmod(0o000)
    probe = FilesystemFolderProbe()
    try:
        with pytest.raises(InvalidRootPathError):
            probe.list_subfolders(raiz)
    finally:
        raiz.chmod(0o755)


# --- read_description -------------------------------------------------------------------


def test_read_description_extrai_primeiro_paragrafo_util(tmp_path: Path) -> None:
    """Extrai o primeiro parágrafo útil, ignorando cabeçalho e badge no início."""
    pasta = tmp_path / "repo"
    pasta.mkdir()
    (pasta / "README.md").write_text(
        "# Título\n\n[![CI](https://exemplo/badge.svg)](https://exemplo)\n\n"
        "Este repositório contém exemplos de uso da API.\n",
        encoding="utf-8",
    )
    probe = FilesystemFolderProbe()
    assert probe.read_description(pasta) == "Este repositório contém exemplos de uso da API."


def test_read_description_trunca_em_500_caracteres(tmp_path: Path) -> None:
    """Descrição extraída é truncada em até 500 caracteres."""
    pasta = tmp_path / "repo"
    pasta.mkdir()
    texto_longo = "a" * 800
    (pasta / "README.md").write_text(texto_longo, encoding="utf-8")
    probe = FilesystemFolderProbe()
    resultado = probe.read_description(pasta)
    assert resultado is not None
    assert len(resultado) <= 500


def test_read_description_none_sem_readme(tmp_path: Path) -> None:
    """Retorna None quando não há README."""
    pasta = tmp_path / "repo"
    pasta.mkdir()
    probe = FilesystemFolderProbe()
    assert probe.read_description(pasta) is None


def test_read_description_none_readme_vazio(tmp_path: Path) -> None:
    """Retorna None quando o README existe mas está vazio."""
    pasta = tmp_path / "repo"
    pasta.mkdir()
    (pasta / "README.md").write_text("", encoding="utf-8")
    probe = FilesystemFolderProbe()
    assert probe.read_description(pasta) is None


def test_read_description_none_readme_so_badges_e_cabecalho(tmp_path: Path) -> None:
    """Retorna None quando o README só tem cabeçalho e badges, sem parágrafo útil."""
    pasta = tmp_path / "repo"
    pasta.mkdir()
    (pasta / "README.md").write_text(
        "# Título\n\n![badge](https://exemplo/badge.svg)\n\n[![CI](https://x)](https://y)\n",
        encoding="utf-8",
    )
    probe = FilesystemFolderProbe()
    assert probe.read_description(pasta) is None


# --- detect_license ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("conteudo", "esperado"),
    [
        ("MIT License\n\nPermission is hereby granted, free of charge, to any person...", "MIT"),
        (
            "Apache License\nVersion 2.0, January 2004\n\nTERMS AND CONDITIONS...",
            "Apache-2.0",
        ),
        (
            "GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n\nPreamble...",
            "GPL-3.0",
        ),
        (
            "Redistribution and use in source and binary forms, with or without "
            "modification, are permitted provided...\nNeither the name of the copyright "
            "holder nor...",
            "BSD-3-Clause",
        ),
    ],
)
def test_detect_license_reconhece_licencas_suportadas(
    tmp_path: Path, conteudo: str, esperado: str
) -> None:
    """Reconhece MIT/Apache-2.0/GPL-3.0/BSD-3-Clause pelas frases-chave documentadas."""
    pasta = tmp_path / "repo"
    pasta.mkdir()
    (pasta / "LICENSE").write_text(conteudo, encoding="utf-8")
    probe = FilesystemFolderProbe()
    assert probe.detect_license(pasta) == esperado


def test_detect_license_none_sem_arquivo(tmp_path: Path) -> None:
    """Retorna None quando não há arquivo LICENSE."""
    pasta = tmp_path / "repo"
    pasta.mkdir()
    probe = FilesystemFolderProbe()
    assert probe.detect_license(pasta) is None


def test_detect_license_none_texto_nao_reconhecido(tmp_path: Path) -> None:
    """Retorna None quando o texto não corresponde a nenhuma licença suportada."""
    pasta = tmp_path / "repo"
    pasta.mkdir()
    (pasta / "LICENSE").write_text(
        "Licença proprietária customizada da empresa X.", encoding="utf-8"
    )
    probe = FilesystemFolderProbe()
    assert probe.detect_license(pasta) is None


def test_detect_license_none_ambiguo_duas_licencas(tmp_path: Path) -> None:
    """Retorna None quando o texto corresponde a mais de uma licença simultaneamente."""
    pasta = tmp_path / "repo"
    pasta.mkdir()
    conteudo = (
        "MIT License\n\nPermission is hereby granted, free of charge, to any person...\n\n"
        "---\n\nApache License\nVersion 2.0, January 2004\n\nTERMS AND CONDITIONS..."
    )
    (pasta / "LICENSE").write_text(conteudo, encoding="utf-8")
    probe = FilesystemFolderProbe()
    assert probe.detect_license(pasta) is None
