# -*- coding: utf-8 -*-
"""
NOME: test_build_index.py
TITULO: Testes de falha — caso de uso build_index (library/INDEX.md determinístico)
DATA: 25/09/2026 13:15
MODIFICADO: 25/09/2026 13:15
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.build_index
HISTÓRICO:
    - 25/09/2026 13:15: criação (T028, feature 009) — sucede test_build_catalog.py
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.application.build_index import IndexResult, build_index
from praxisforge.application.ports import IndexWriter
from praxisforge.domain.errors import IndexWriteError
from praxisforge.infrastructure.filesystem_library_repository import FilesystemLibraryRepository
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from praxisforge.infrastructure.source_frontmatter import FrontmatterSourceReader
from tests.library_helpers import criar_projeto, escrever_fonte, escrever_item


class _Writer(IndexWriter):
    def __init__(self, falhar: bool = False) -> None:
        self.conteudo: str | None = None
        self.falhar = falhar

    def write(self, content: str) -> None:
        if self.falhar:
            raise IndexWriteError("disco cheio")
        self.conteudo = content


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return criar_projeto(tmp_path / "projeto")


def _gerar(root: Path, writer: _Writer) -> IndexResult:
    return build_index(
        FilesystemLibraryRepository(root / "library"),
        JsonSchemaContractValidator(schemas_dir=root / "schemas"),
        FrontmatterSourceReader(),
        sorted((root / "src" / "data" / "sources").rglob("*.md")),
        writer,
    )


def test_ordem_por_tipo_e_nome_sem_data(root: Path) -> None:
    """Seções na ordem dos tipos; itens por nome; nenhuma data no conteúdo (FR-012)."""
    escrever_item(root, "rule", "zeta")
    escrever_item(root, "skill", "beta")
    escrever_item(root, "skill", "alfa")
    writer = _Writer()
    resultado = _gerar(root, writer)
    texto = writer.conteudo or ""
    assert texto.index("## Skills") < texto.index("## Commands") < texto.index("## Rules")
    assert texto.index("| alfa |") < texto.index("| beta |")
    assert "`library/rules/zeta.md`" in texto
    assert "2026" not in texto
    assert resultado.items == ["skill/alfa", "skill/beta", "rule/zeta"]


def test_colunas_com_fontes_e_autoral(root: Path) -> None:
    """Linha traz descrição, versão, fontes (ou autoral) e caminho (FR-011)."""
    escrever_fonte(root, "x", "guia")
    escrever_item(
        root, "agent", "a", sources=["guia"], authored=None, description="Revisa | código"
    )
    escrever_item(root, "command", "c", version="2.1.0")
    writer = _Writer()
    _gerar(root, writer)
    texto = writer.conteudo or ""
    assert "| a | Revisa \\| código | 1.0.0 | guia | `library/agents/a.md` |" in texto
    assert "| c | Descrição do item | 2.1.0 | autoral | `library/commands/c.md` |" in texto


def test_reescrita_pendente_sinalizada(root: Path) -> None:
    """Item com rewrite_pending aparece com o aviso (FR-011, FR-024)."""
    escrever_item(root, "skill", "s", metadata={"rewrite_pending": True})
    writer = _Writer()
    _gerar(root, writer)
    assert "| s ⚠ reescrita pendente |" in (writer.conteudo or "")


def test_invalido_fica_de_fora_e_e_omitido(root: Path) -> None:
    """Item inválido não entra e vem em omitted com motivo (FR-013)."""
    escrever_item(root, "agent", "ruim", campos={"name": "x"})
    escrever_item(root, "agent", "bom")
    writer = _Writer()
    resultado = _gerar(root, writer)
    assert "| ruim |" not in (writer.conteudo or "")
    assert [(f.kind, f.name) for f in resultado.omitted] == [("agent", "ruim")]


def test_acervo_vazio(root: Path) -> None:
    """Sem itens: seções presentes com 'Nenhum item.'."""
    writer = _Writer()
    resultado = _gerar(root, writer)
    assert (writer.conteudo or "").count("Nenhum item.") == 6
    assert resultado.items == []


def test_deterministico(root: Path) -> None:
    """Duas gerações sem mudança produzem o mesmo texto (SC-003)."""
    escrever_item(root, "skill", "s")
    escrever_item(root, "hook", "h")
    primeiro, segundo = _Writer(), _Writer()
    _gerar(root, primeiro)
    _gerar(root, segundo)
    assert primeiro.conteudo == segundo.conteudo


def test_falha_do_writer_propaga(root: Path) -> None:
    """Falha de gravação sobe como IndexWriteError."""
    with pytest.raises(IndexWriteError):
        _gerar(root, _Writer(falhar=True))
