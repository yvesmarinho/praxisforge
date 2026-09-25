# -*- coding: utf-8 -*-
"""
NOME: filesystem_folder_probe.py
TITULO: Adapter do RootFolderProbe — lista subpastas e extrai description/license via filesystem
DATA: 22/09/2026 18:10
MODIFICADO: 25/09/2026 09:51
VERSÃO: 0.1.0
DEPEND: os, re, praxisforge.application.ports, praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 18:10: criação (T017) — faz test_filesystem_folder_probe.py passar
    - 24/09/2026 10:17: reconhece Elastic-2.0
STATUS: DEV
"""

import logging
import os
import re
from pathlib import Path

from praxisforge.application.ports import RootFolderProbe
from praxisforge.domain.errors import InvalidRootPathError
from praxisforge.infrastructure.logging_setup import log_event

logger = logging.getLogger(__name__)

_README_NAMES = ("README.md", "README", "README.rst")
_LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt")
_MAX_DESCRIPTION_LENGTH = 500

_CABECALHO_OU_BADGE = re.compile(r"^(#+\s|!\[|\[!\[)")

# Frases-chave por licença (research.md, Decisão 2) — case-insensitive.
_ASSINATURAS: dict[str, tuple[str, ...]] = {
    "MIT": ("permission is hereby granted, free of charge",),
    "Apache-2.0": ("apache license", "version 2.0"),
    "GPL-3.0": ("gnu general public license", "version 3"),
    "BSD-3-Clause": (
        "redistribution and use in source and binary forms",
        "neither the name of",
    ),
    "Elastic-2.0": ("elastic license 2.0",),
}


class FilesystemFolderProbe(RootFolderProbe):
    """Adapter que inspeciona uma pasta-raiz real via filesystem."""

    def list_subfolders(self, root: Path) -> list[Path]:
        """Ver RootFolderProbe.list_subfolders."""
        if not root.exists():
            log_event(
                logger,
                event="bootstrap_list_subfolders",
                alias="*",
                outcome="falha",
                error_type="InvalidRootPathError",
            )
            raise InvalidRootPathError(str(root), reason="não existe")
        if not root.is_dir():
            log_event(
                logger,
                event="bootstrap_list_subfolders",
                alias="*",
                outcome="falha",
                error_type="InvalidRootPathError",
            )
            raise InvalidRootPathError(str(root), reason="não é um diretório")
        if not os.access(root, os.R_OK | os.X_OK):
            log_event(
                logger,
                event="bootstrap_list_subfolders",
                alias="*",
                outcome="falha",
                error_type="InvalidRootPathError",
            )
            raise InvalidRootPathError(str(root), reason="sem permissão de leitura")
        subpastas = [item for item in root.iterdir() if item.is_dir()]
        log_event(
            logger, event="bootstrap_list_subfolders", alias="*", outcome="ok", error_type=None
        )
        return sorted(subpastas, key=lambda p: p.name)

    def read_description(self, path: Path) -> str | None:
        """Ver RootFolderProbe.read_description."""
        conteudo = self._ler_primeiro_arquivo(path, _README_NAMES)
        if conteudo is None:
            return None
        for linha in conteudo.splitlines():
            texto = linha.strip()
            if not texto or _CABECALHO_OU_BADGE.match(texto):
                continue
            return texto[:_MAX_DESCRIPTION_LENGTH]
        return None

    def detect_license(self, path: Path) -> str | None:
        """Ver RootFolderProbe.detect_license."""
        conteudo = self._ler_primeiro_arquivo(path, _LICENSE_NAMES)
        if conteudo is None:
            return None
        texto = conteudo.lower()
        reconhecidas = [
            nome for nome, frases in _ASSINATURAS.items() if all(frase in texto for frase in frases)
        ]
        if len(reconhecidas) == 1:
            return reconhecidas[0]
        return None  # nenhuma correspondência, ou ambíguo (mais de uma)

    @staticmethod
    def _ler_primeiro_arquivo(path: Path, nomes: tuple[str, ...]) -> str | None:
        for nome in nomes:
            arquivo = path / nome
            if arquivo.is_file():
                try:
                    return arquivo.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    return None
        return None
