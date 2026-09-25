# -*- coding: utf-8 -*-
"""
NOME: filesystem_index_writer.py
TITULO: Adapter de IndexWriter — grava library/INDEX.md de forma atômica
DATA: 25/09/2026 13:15
MODIFICADO: 25/09/2026 13:15
VERSÃO: 0.1.0
DEPEND: praxisforge.application.ports, praxisforge.domain.errors
HISTÓRICO:
    - 25/09/2026 13:15: criação (T030, feature 009) — sucede filesystem_catalog_writer.py
STATUS: DEV
"""

import os
import tempfile
from pathlib import Path

from praxisforge.application.ports import IndexWriter
from praxisforge.domain.errors import IndexWriteError


class FilesystemIndexWriter(IndexWriter):
    """
    Grava o índice em temporário na mesma pasta e troca com `os.replace`.

    :param target: arquivo do índice (`library/INDEX.md`).
    :type target: Path
    """

    def __init__(self, target: Path) -> None:
        self._target = target

    def write(self, content: str) -> None:
        """Ver IndexWriter.write."""
        temporario: Path | None = None
        try:
            descritor, nome = tempfile.mkstemp(
                prefix=".INDEX.", suffix=".tmp", dir=self._target.parent
            )
            temporario = Path(nome)
            with os.fdopen(descritor, "w", encoding="utf-8", newline="\n") as arquivo:
                arquivo.write(content)
            os.replace(temporario, self._target)
        except OSError as error:
            if temporario is not None:
                temporario.unlink(missing_ok=True)
            raise IndexWriteError(error.strerror or type(error).__name__) from error
