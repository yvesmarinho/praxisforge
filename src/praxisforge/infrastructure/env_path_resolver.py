# -*- coding: utf-8 -*-
"""
NOME: env_path_resolver.py
TITULO: Adapter do PathResolver — resolve alias → caminho real via variável de ambiente
DATA: 22/09/2026 10:10
MODIFICADO: 22/09/2026 10:02
VERSÃO: 0.1.0
DEPEND: os, praxisforge.application.ports, praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 10:10: criação (T046) — faz tests/integration/test_env_path_resolver.py passar
STATUS: DEV
"""

import logging
import os
from pathlib import Path

from praxisforge.application.ports import PathResolver
from praxisforge.domain.errors import (
    FolderPathInvalidError,
    FolderPathNotConfiguredError,
    FolderPathUnreadableError,
)
from praxisforge.infrastructure.logging_setup import log_event

logger = logging.getLogger(__name__)


class EnvPathResolver(PathResolver):
    """Adapter que resolve `PRAXISFORGE_FOLDER_<ALIAS>` para um caminho real."""

    def resolve(self, alias: str) -> Path:
        """Ver PathResolver.resolve."""
        env_var = f"PRAXISFORGE_FOLDER_{alias.upper()}"
        raw = os.environ.get(env_var)
        if not raw:
            log_event(
                logger,
                event="resolve_path",
                alias=alias,
                outcome="falha",
                error_type="FolderPathNotConfiguredError",
            )
            raise FolderPathNotConfiguredError(alias)
        configured = Path(raw)
        if not configured.is_absolute() or ".." in configured.parts:
            log_event(
                logger,
                event="resolve_path",
                alias=alias,
                outcome="falha",
                error_type="FolderPathInvalidError",
            )
            raise FolderPathInvalidError(alias, reason="caminho relativo ou com '..'")
        try:
            resolved = configured.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            log_event(
                logger,
                event="resolve_path",
                alias=alias,
                outcome="falha",
                error_type="FolderPathInvalidError",
            )
            raise FolderPathInvalidError(alias, reason="caminho inexistente") from error
        if not resolved.is_dir():
            log_event(
                logger,
                event="resolve_path",
                alias=alias,
                outcome="falha",
                error_type="FolderPathInvalidError",
            )
            raise FolderPathInvalidError(alias, reason="caminho não é um diretório")
        if not os.access(resolved, os.R_OK | os.X_OK):
            log_event(
                logger,
                event="resolve_path",
                alias=alias,
                outcome="falha",
                error_type="FolderPathUnreadableError",
            )
            raise FolderPathUnreadableError(alias)
        log_event(logger, event="resolve_path", alias=alias, outcome="ok", error_type=None)
        return resolved
