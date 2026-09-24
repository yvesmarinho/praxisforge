# -*- coding: utf-8 -*-
"""
NOME: env_legacy_path_source.py
TITULO: Adapter LegacyPathSource — lê PRAXISFORGE_FOLDER_<ALIAS> (só para a migração v1 → v2)
DATA: 23/09/2026 16:50
MODIFICADO: 23/09/2026 16:50
VERSÃO: 0.1.0
DEPEND: os, praxisforge.application.ports
HISTÓRICO:
    - 23/09/2026 16:50: criação (T017, feature 005-caminho-absoluto-registro)
STATUS: DEV
"""

import os

from praxisforge.application.ports import LegacyPathSource


class EnvLegacyPathSource(LegacyPathSource):
    """Adapter que devolve o valor bruto da variável de ambiente antiga de um alias."""

    def lookup(self, alias: str) -> str | None:
        """Ver LegacyPathSource.lookup."""
        return os.environ.get(f"PRAXISFORGE_FOLDER_{alias.upper()}") or None
