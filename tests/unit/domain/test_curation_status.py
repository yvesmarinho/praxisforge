# -*- coding: utf-8 -*-
"""
NOME: test_curation_status.py
TITULO: Testes de falha — enum CurationStatus
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:47
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.curation_status
HISTÓRICO:
    - 22/09/2026 09:45: criação (T007)
STATUS: DEV
"""

import pytest

from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import PraxisForgeError


def test_cinco_valores_exatos() -> None:
    """CurationStatus tem exatamente cinco valores de máquina."""
    valores = {item.value for item in CurationStatus}
    assert valores == {"not_scanned", "scanned", "in_curation", "curated", "pending"}


def test_conversao_de_string_invalida_levanta_erro_semantico() -> None:
    """Converter uma string fora do conjunto levanta um erro semântico do domínio."""
    with pytest.raises(PraxisForgeError):
        CurationStatus.from_str("invalido")


@pytest.mark.parametrize(
    ("valor", "rotulo"),
    [
        ("not_scanned", "não varrida"),
        ("scanned", "varrida"),
        ("in_curation", "em curadoria"),
        ("curated", "curada"),
        ("pending", "pendente"),
    ],
)
def test_rotulos_pt_br(valor: str, rotulo: str) -> None:
    """Cada valor tem um rótulo em pt-BR para exibição na CLI."""
    status = CurationStatus.from_str(valor)
    assert status.label_pt_br() == rotulo
