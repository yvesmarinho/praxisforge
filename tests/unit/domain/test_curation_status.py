# -*- coding: utf-8 -*-
"""
NOME: test_curation_status.py
TITULO: Testes de falha — enum CurationStatus
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 16:35
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.curation_status
HISTÓRICO:
    - 22/09/2026 09:45: criação (T007)
    - 22/09/2026 17:30: +IGNORE (T002, feature 003-bootstrap-registro-pastas)
STATUS: DEV
"""

import pytest

from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import PraxisForgeError


def test_seis_valores_exatos() -> None:
    """CurationStatus tem exatamente seis valores de máquina (feature 003: +ignore)."""
    valores = {item.value for item in CurationStatus}
    assert valores == {
        "not_scanned",
        "scanned",
        "in_curation",
        "curated",
        "pending",
        "ignore",
    }


def test_ignore_conversao_e_rotulo() -> None:
    """CurationStatus.IGNORE existe, é conversível por from_str e tem rótulo pt-BR (FR-010)."""
    status = CurationStatus.from_str("ignore")
    assert status is CurationStatus.IGNORE
    assert status.label_pt_br() == "ignorada"


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
        ("ignore", "ignorada"),
    ],
)
def test_rotulos_pt_br(valor: str, rotulo: str) -> None:
    """Cada valor tem um rótulo em pt-BR para exibição na CLI."""
    status = CurationStatus.from_str(valor)
    assert status.label_pt_br() == rotulo
