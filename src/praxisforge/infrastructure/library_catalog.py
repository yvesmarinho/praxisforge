# -*- coding: utf-8 -*-
"""
NOME: library_catalog.py
TITULO: Adapter LibraryCatalog — acervo library/ visto pela triagem (só leitura, feature 011)
DATA: 28/09/2026 16:01
MODIFICADO: 28/09/2026 16:01
VERSÃO: 0.1.0
DEPEND: praxisforge.infrastructure.filesystem_library_repository
HISTÓRICO:
    - 28/09/2026 16:01: criação (T027, feature 011) — faz test_library_catalog.py passar
STATUS: DEV
"""

import logging
from pathlib import Path

from praxisforge.application.ports import CatalogItem, LibraryCatalog
from praxisforge.domain.curation_triage import LIBRARY_REF
from praxisforge.domain.errors import PraxisForgeError
from praxisforge.domain.library_item import ItemKind
from praxisforge.infrastructure.filesystem_library_repository import FilesystemLibraryRepository

logger = logging.getLogger(__name__)

_INDEX = "INDEX.md"


class FilesystemLibraryCatalog(LibraryCatalog):
    """
    Índice, itens e existência de itens do acervo, sobre o `FilesystemLibraryRepository` (009).

    Itens inválidos (frontmatter quebrado) são ignorados: a triagem não é o validador do acervo.

    :param library_dir: diretório `library/` do projeto.
    :type library_dir: Path
    """

    def __init__(self, library_dir: Path) -> None:
        self._dir = library_dir
        self._repo = FilesystemLibraryRepository(library_dir)

    def index_text(self) -> str:
        """Ver LibraryCatalog.index_text."""
        try:
            return (self._dir / _INDEX).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""

    def _nomes(self, kind: ItemKind) -> list[str]:
        if not self._dir.is_dir():
            return []
        return self._repo.list_entries(kind)

    def items(self, kind: ItemKind) -> list[CatalogItem]:
        """Ver LibraryCatalog.items."""
        itens: list[CatalogItem] = []
        for nome in self._nomes(kind):
            try:
                documento = self._repo.load(kind, nome)
                caminho = self._repo.item_path(kind, nome)
                principal = caminho / kind.main_file if kind.main_file else caminho
                conteudo = principal.read_text(encoding="utf-8")
            except (PraxisForgeError, OSError, UnicodeDecodeError):
                logger.warning("item do acervo ignorado na triagem: %s/%s", kind.value, nome)
                continue
            descricao = documento.frontmatter.get("description")
            itens.append(
                CatalogItem(
                    ref=f"{kind.value}/{nome}",
                    kind=kind,
                    name=nome,
                    description=descricao if isinstance(descricao, str) else "",
                    content=conteudo,
                )
            )
        return itens

    def exists(self, ref: str) -> bool:
        """Ver LibraryCatalog.exists (formato validado antes de tocar o disco)."""
        if not LIBRARY_REF.match(ref):
            return False
        tipo, nome = ref.split("/", 1)
        return nome in self._nomes(ItemKind(tipo))
