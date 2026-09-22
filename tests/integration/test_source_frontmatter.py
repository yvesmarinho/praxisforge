# -*- coding: utf-8 -*-
"""
NOME: test_source_frontmatter.py
TITULO: Testes de falha — leitor de frontmatter de fontes (Infrastructure)
DATA: 22/09/2026 10:30
MODIFICADO: 22/09/2026 10:05
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.source_frontmatter
HISTÓRICO:
    - 22/09/2026 10:30: criação (T052)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.domain.errors import RegistryUnavailableError
from praxisforge.infrastructure.source_frontmatter import read_frontmatter


def test_sem_frontmatter_levanta_erro(tmp_path: Path) -> None:
    """Arquivo .md sem frontmatter levanta erro específico."""
    arquivo = tmp_path / "sem_frontmatter.md"
    arquivo.write_text("# Título\n\nConteúdo sem frontmatter.\n", encoding="utf-8")
    with pytest.raises(RegistryUnavailableError):
        read_frontmatter(arquivo)


def test_frontmatter_corrompido_levanta_erro(tmp_path: Path) -> None:
    """Frontmatter com YAML corrompido levanta erro específico."""
    arquivo = tmp_path / "corrompido.md"
    arquivo.write_text("---\norigin: [invalido: : :\n---\nConteúdo\n", encoding="utf-8")
    with pytest.raises(RegistryUnavailableError):
        read_frontmatter(arquivo)


def test_arquivo_ilegivel_levanta_erro(tmp_path: Path) -> None:
    """Arquivo inexistente levanta erro específico."""
    with pytest.raises(RegistryUnavailableError):
        read_frontmatter(tmp_path / "inexistente.md")


def test_frontmatter_valido_devolve_dict(tmp_path: Path) -> None:
    """Frontmatter válido é devolvido como dict, com date preservada como string."""
    arquivo = tmp_path / "valido.md"
    arquivo.write_text(
        "---\n"
        "schema_version: '1'\n"
        "origin: https://exemplo.com\n"
        "date: 2026-09-21\n"
        "license: MIT\n"
        "relevance: alta\n"
        "status: active\n"
        "extract_allowed: true\n"
        "---\n"
        "Conteúdo.\n",
        encoding="utf-8",
    )
    documento = read_frontmatter(arquivo)
    assert documento["origin"] == "https://exemplo.com"
    assert documento["date"] == "2026-09-21"
    assert isinstance(documento["date"], str)


def test_lote_de_arquivos_com_falha_por_item(tmp_path: Path) -> None:
    """Ler múltiplos arquivos; um sem frontmatter não impede ler os demais (uso pelo caller)."""
    valido = tmp_path / "valido.md"
    valido.write_text(
        "---\nschema_version: '1'\norigin: x\ndate: 2026-09-21\nlicense: MIT\n"
        "relevance: y\nstatus: active\nextract_allowed: true\n---\n",
        encoding="utf-8",
    )
    invalido = tmp_path / "invalido.md"
    invalido.write_text("sem frontmatter\n", encoding="utf-8")

    resultados: dict[str, object] = {}
    for arquivo in (valido, invalido):
        try:
            resultados[arquivo.name] = read_frontmatter(arquivo)
        except RegistryUnavailableError as error:
            resultados[arquivo.name] = error
    assert isinstance(resultados["valido.md"], dict)
    assert isinstance(resultados["invalido.md"], RegistryUnavailableError)
