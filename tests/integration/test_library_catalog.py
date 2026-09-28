# -*- coding: utf-8 -*-
"""
NOME: test_library_catalog.py
TITULO: Testes de falha — catálogo do acervo visto pela triagem (feature 011)
DATA: 28/09/2026 15:59
MODIFICADO: 28/09/2026 15:59
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.library_catalog
HISTÓRICO:
    - 28/09/2026 15:59: criação (T022, feature 011)
STATUS: DEV
"""

from pathlib import Path

from praxisforge.domain.library_item import ItemKind
from praxisforge.infrastructure.library_catalog import FilesystemLibraryCatalog
from tests.library_helpers import REPO_ROOT, criar_projeto, escrever_item


def test_catalogo_do_repositorio_real() -> None:
    catalogo = FilesystemLibraryCatalog(REPO_ROOT / "library")
    assert "diretrizes-codificacao" in catalogo.index_text()
    assert catalogo.exists("skill/diretrizes-codificacao")
    assert not catalogo.exists("skill/inexistente")
    assert not catalogo.exists("rule/diretrizes-codificacao")
    skills = catalogo.items(ItemKind.SKILL)
    assert [i.name for i in skills] == sorted(i.name for i in skills)
    item = next(i for i in skills if i.name == "diretrizes-codificacao")
    assert item.ref == "skill/diretrizes-codificacao"
    assert item.description and "---" in item.content


def test_itens_por_tipo_e_invalidos_ignorados(tmp_path: Path) -> None:
    root = criar_projeto(tmp_path)
    escrever_item(root, "rule", "estilo", description="Estilo de código")
    (root / "library" / "rules" / "quebrado.md").write_text("sem frontmatter", encoding="utf-8")
    catalogo = FilesystemLibraryCatalog(root / "library")
    regras = catalogo.items(ItemKind.RULE)
    assert [(i.ref, i.description) for i in regras] == [("rule/estilo", "Estilo de código")]
    assert catalogo.items(ItemKind.SKILL) == []
    assert catalogo.index_text() == ""


def test_referencias_malformadas(tmp_path: Path) -> None:
    catalogo = FilesystemLibraryCatalog(criar_projeto(tmp_path) / "library")
    for ref in ("skill", "skill/", "x/y", "skill/../../etc", ""):
        assert not catalogo.exists(ref)


def test_sem_acervo(tmp_path: Path) -> None:
    catalogo = FilesystemLibraryCatalog(tmp_path / "library")
    assert catalogo.index_text() == ""
    assert catalogo.items(ItemKind.SKILL) == []
    assert not catalogo.exists("skill/x")
