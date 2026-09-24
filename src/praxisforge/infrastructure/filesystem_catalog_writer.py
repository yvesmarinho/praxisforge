# -*- coding: utf-8 -*-
"""
NOME: filesystem_catalog_writer.py
TITULO: Adapter de CatalogWriter — grava skills/README.md de forma atômica
DATA: 24/09/2026 16:54
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.errors, praxisforge.application.ports
HISTÓRICO:
    - 24/09/2026 16:54: criação (T025, feature 008)
STATUS: DEV
"""

import os
import tempfile
from pathlib import Path

from praxisforge.application.ports import CatalogWriter
from praxisforge.domain.errors import CatalogWriteError


class FilesystemCatalogWriter(CatalogWriter):
    """
    Grava o catálogo em temporário na mesma pasta e troca com `os.replace`.

    :param target: arquivo do catálogo (`skills/README.md`).
    :type target: Path
    """

    def __init__(self, target: Path) -> None:
        self._target = target

    def write(self, content: str) -> None:
        """Ver CatalogWriter.write."""
        temporario: Path | None = None
        try:
            self._target.parent.mkdir(parents=True, exist_ok=True)
            descritor, nome = tempfile.mkstemp(
                prefix=".README.", suffix=".tmp", dir=self._target.parent
            )
            temporario = Path(nome)
            with os.fdopen(descritor, "w", encoding="utf-8", newline="\n") as arquivo:
                arquivo.write(content)
            os.replace(temporario, self._target)
        except OSError as error:
            if temporario is not None:
                temporario.unlink(missing_ok=True)
            raise CatalogWriteError(error.strerror or type(error).__name__) from error
