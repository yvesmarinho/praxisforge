# -*- coding: utf-8 -*-
"""
NOME: test_prompt_set.py
TITULO: Testes de falha — conjunto de prompts versionados e impressão digital (feature 011)
DATA: 28/09/2026 15:51
MODIFICADO: 28/09/2026 15:51
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.prompt_set
HISTÓRICO:
    - 28/09/2026 15:51: criação (T007, feature 011)
STATUS: DEV
"""

import pytest

from praxisforge.domain.errors import PromptSetError
from praxisforge.domain.prompt_set import PromptSet


def _set(**campos: str) -> PromptSet:
    base = {"triage": "t", "draft": "d", "judge": "j", "criteria": "c"}
    return PromptSet(**(base | campos))


@pytest.mark.parametrize("papel", ["triage", "draft", "judge", "criteria"])
@pytest.mark.parametrize("vazio", ["", "  \n"])
def test_prompt_vazio(papel: str, vazio: str) -> None:
    with pytest.raises(PromptSetError, match=f"{papel}.md"):
        _set(**{papel: vazio})


def test_impressao_digital_estavel_e_sensivel() -> None:
    base = _set().fingerprint
    assert len(base) == 64 and base == _set().fingerprint
    for papel in ("triage", "draft", "judge", "criteria"):
        assert _set(**{papel: "outro"}).fingerprint != base


def test_impressao_digital_nao_confunde_fronteiras() -> None:
    # conteúdo deslocado entre arquivos não pode dar a mesma impressão digital
    assert _set(triage="ab", draft="c").fingerprint != _set(triage="a", draft="bc").fingerprint
