# -*- coding: utf-8 -*-
"""
NOME: filesystem_registry_mover.py
TITULO: Adapter RegistryFileMover — move o registro com cópia verificada e troca atômica
DATA: 24/09/2026 14:35
MODIFICADO: 24/09/2026 14:35
VERSÃO: 0.1.0
DEPEND: praxisforge.application.ports, praxisforge.domain.errors
HISTÓRICO:
    - 24/09/2026 14:35: criação (T029, feature 007) — faz test_filesystem_registry_mover.py passar
STATUS: DEV
"""

import os
import shutil
import tempfile
from pathlib import Path

from praxisforge.application.ports import RegistryFileMover
from praxisforge.domain.errors import RegistryRelocationError


def _iguais(a: Path, b: Path) -> bool:
    """Compara o conteúdo dos dois arquivos byte a byte."""
    return a.read_bytes() == b.read_bytes()


class FilesystemRegistryMover(RegistryFileMover):
    """Copia para um temporário na pasta do destino, confere, troca e só então remove a origem."""

    def move(self, source: Path, target: Path) -> None:
        """Ver RegistryFileMover.move."""
        temporario: str | None = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temporario = tempfile.mkstemp(
                dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
            )
            os.close(fd)
            shutil.copy2(source, temporario)
            if not _iguais(source, Path(temporario)):
                raise RegistryRelocationError("cópia divergente da origem")
            os.replace(temporario, target)
            temporario = None
            source.unlink()
        except OSError as error:
            raise RegistryRelocationError(error.strerror or str(error)) from error
        finally:
            if temporario is not None and os.path.exists(temporario):
                os.unlink(temporario)
