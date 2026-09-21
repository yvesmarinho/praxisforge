# -*- coding: utf-8 -*-
"""
NOME: test_package.py
TITULO: Testes de contrato do pacote praxisforge
DATA: 21/09/2026 15:36
MODIFICADO: 21/09/2026 15:36
VERSÃO: 0.1.0
DEPEND: pytest
HISTÓRICO:
    - 21/09/2026 15:36: criação (smoke test do pacote)
STATUS: DEV
"""

import re

import praxisforge


def test_version_is_semver() -> None:
    """A versão exposta deve seguir o formato MAJOR.MINOR.PATCH."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", praxisforge.__version__)


def test_placeholder_main_removed() -> None:
    """O placeholder com print() do uv init não deve existir no pacote."""
    assert not hasattr(praxisforge, "main")
