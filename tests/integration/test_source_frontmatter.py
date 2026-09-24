# -*- coding: utf-8 -*-
"""
NOME: test_source_frontmatter.py
TITULO: Testes de falha — leitor de frontmatter de fontes (Infrastructure)
DATA: 22/09/2026 10:30
MODIFICADO: 24/09/2026 10:54
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.source_frontmatter
HISTÓRICO:
    - 22/09/2026 10:30: criação (T052)
    - 24/09/2026 10:54: adapter FrontmatterSourceReader da porta SourceReader (T013, feature 006)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.application.ports import SourceReader
from praxisforge.domain.errors import RegistryUnavailableError
from praxisforge.infrastructure.source_frontmatter import FrontmatterSourceReader, read_frontmatter


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


def test_adapter_implementa_a_porta_e_le_o_frontmatter(tmp_path: Path) -> None:
    """FrontmatterSourceReader é um SourceReader e devolve o mesmo dict de read_frontmatter."""
    arquivo = tmp_path / "fonte.md"
    arquivo.write_text("---\norigin: x\ndate: 2026-09-21\n---\ncorpo\n", encoding="utf-8")
    reader = FrontmatterSourceReader()
    assert isinstance(reader, SourceReader)
    assert reader.read(arquivo) == {"origin": "x", "date": "2026-09-21"}


@pytest.mark.parametrize(
    "conteudo", [None, "sem frontmatter\n", "---\norigin: [x\n---\n", "---\norigin: x\n"]
)
def test_adapter_falhas_viram_registry_unavailable(tmp_path: Path, conteudo: str | None) -> None:
    """Inexistente, sem frontmatter, YAML inválido e não fechado → RegistryUnavailableError."""
    arquivo = tmp_path / "fonte.md"
    if conteudo is not None:
        arquivo.write_text(conteudo, encoding="utf-8")
    with pytest.raises(RegistryUnavailableError):
        FrontmatterSourceReader().read(arquivo)
