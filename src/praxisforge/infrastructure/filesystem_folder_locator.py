# -*- coding: utf-8 -*-
"""
NOME: filesystem_folder_locator.py
TITULO: Adapter FolderLocator — canoniza e confere pastas pelo caminho do registro
DATA: 23/09/2026 16:50
MODIFICADO: 23/09/2026 16:50
VERSÃO: 0.1.0
DEPEND: os, pathlib, praxisforge.application.ports, praxisforge.domain.errors
HISTÓRICO:
    - 23/09/2026 16:50: criação (T016, feature 005-caminho-absoluto-registro) — substitui a
      resolução por variável de ambiente (env_path_resolver.py)
STATUS: DEV
"""

import logging
import os
from pathlib import Path

from praxisforge.application.ports import FolderLocator
from praxisforge.domain.errors import FolderPathInvalidError, FolderPathUnreadableError
from praxisforge.infrastructure.logging_setup import log_event

logger = logging.getLogger(__name__)


class FilesystemFolderLocator(FolderLocator):
    """Adapter que confere pastas reais; mensagens citam só o alias (FR-012)."""

    def canonicalize(self, alias: str, raw: str) -> Path:
        """Ver FolderLocator.canonicalize."""
        if not raw:
            self._falha(alias, "FolderPathInvalidError")
            raise FolderPathInvalidError(alias, reason="caminho vazio")
        try:
            resolved = Path(raw).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as error:
            self._falha(alias, "FolderPathInvalidError")
            raise FolderPathInvalidError(alias, reason="caminho inexistente") from error
        return self._conferir(alias, resolved)

    def check(self, alias: str, path: Path) -> Path:
        """Ver FolderLocator.check."""
        if not path.exists():
            self._falha(alias, "FolderPathInvalidError")
            raise FolderPathInvalidError(alias, reason="pasta não encontrada no caminho registrado")
        return self._conferir(alias, path)

    def _conferir(self, alias: str, path: Path) -> Path:
        if not path.is_dir():
            self._falha(alias, "FolderPathInvalidError")
            raise FolderPathInvalidError(alias, reason="caminho não é um diretório")
        if not os.access(path, os.R_OK | os.X_OK):
            self._falha(alias, "FolderPathUnreadableError")
            raise FolderPathUnreadableError(alias)
        log_event(logger, event="locate_folder", alias=alias, outcome="ok", error_type=None)
        return path

    @staticmethod
    def _falha(alias: str, error_type: str) -> None:
        log_event(
            logger, event="locate_folder", alias=alias, outcome="falha", error_type=error_type
        )
