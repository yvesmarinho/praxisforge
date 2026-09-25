# -*- coding: utf-8 -*-
"""
NOME: test_no_legacy_skills_dir.py
TITULO: Guarda — nada lê nem ensina o diretório antigo skills/ (FR-016, SC-002)
DATA: 25/09/2026 13:13
MODIFICADO: 25/09/2026 13:13
VERSÃO: 0.1.0
DEPEND: pytest
HISTÓRICO:
    - 25/09/2026 13:13: criação (T026, feature 009)
STATUS: DEV
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
# README.md é registro acumulativo (regra do projeto): menções antigas ficam como histórico
GUIAS = sorted((ROOT / "docs" / "guides").glob("*.md"))
_CAMINHO_ANTIGO = re.compile(r"(?<![\w./~-])skills/(_template|README\.md|<nome>|minha-skill)")
_CONSTANTE_ANTIGA = re.compile(r"""Path\(\s*["']skills["']\s*\)""")


@pytest.mark.parametrize("guia", GUIAS, ids=[g.name for g in GUIAS])
def test_guias_nao_ensinam_o_local_antigo(guia: Path) -> None:
    """Nenhum guia manda criar ou ler itens em skills/ do repositório."""
    achados = [
        linha
        for linha in guia.read_text(encoding="utf-8").splitlines()
        if _CAMINHO_ANTIGO.search(linha)
    ]
    assert achados == []


@pytest.mark.xfail(strict=True, reason="CLI e adapters da 008 saem em T038/T049")
def test_codigo_nao_monta_o_caminho_antigo() -> None:
    """Nenhum módulo em src/ monta Path("skills")."""
    achados = [
        str(arquivo.relative_to(ROOT))
        for arquivo in (ROOT / "src").rglob("*.py")
        if _CONSTANTE_ANTIGA.search(arquivo.read_text(encoding="utf-8"))
    ]
    assert achados == []
