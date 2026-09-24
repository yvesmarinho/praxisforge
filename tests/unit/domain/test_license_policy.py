# -*- coding: utf-8 -*-
"""
NOME: test_license_policy.py
TITULO: Testes de falha — tabela licença → política máxima de extração (feature 006)
DATA: 24/09/2026 10:51
MODIFICADO: 24/09/2026 10:51
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.license_policy
HISTÓRICO:
    - 24/09/2026 10:51: criação (T002, feature 006)
STATUS: DEV
"""

import pytest

from praxisforge.domain.license_policy import (
    ExtractPolicy,
    ExtractScope,
    is_classified,
    max_policy,
)


def test_politicas_sao_ordenadas() -> None:
    """link < summary < verbatim (FR-001)."""
    assert ExtractPolicy.LINK < ExtractPolicy.SUMMARY < ExtractPolicy.VERBATIM
    assert ExtractPolicy.VERBATIM > ExtractPolicy.LINK
    assert ExtractPolicy.SUMMARY <= ExtractPolicy.SUMMARY
    assert sorted([ExtractPolicy.VERBATIM, ExtractPolicy.LINK, ExtractPolicy.SUMMARY]) == [
        ExtractPolicy.LINK,
        ExtractPolicy.SUMMARY,
        ExtractPolicy.VERBATIM,
    ]


@pytest.mark.parametrize("valor", ["link", "summary", "verbatim"])
def test_politica_construida_a_partir_do_texto(valor: str) -> None:
    """Valores serializados em minúsculas."""
    assert ExtractPolicy(valor).value == valor


@pytest.mark.parametrize("valor", ["full", "LINK", "", "copy"])
def test_politica_desconhecida_eh_rejeitada(valor: str) -> None:
    """Valor fora dos três níveis é rejeitado."""
    with pytest.raises(ValueError):
        ExtractPolicy(valor)


def test_escopos() -> None:
    """Escopos docs e code; outro valor rejeitado."""
    assert ExtractScope("docs") is ExtractScope.DOCS
    assert ExtractScope("code") is ExtractScope.CODE
    with pytest.raises(ValueError):
        ExtractScope("tudo")


@pytest.mark.parametrize(
    ("licenca", "esperada"),
    [
        ("MIT", ExtractPolicy.VERBATIM),
        ("BSD-3-Clause", ExtractPolicy.VERBATIM),
        ("Apache-2.0", ExtractPolicy.VERBATIM),
        ("GPL-3.0", ExtractPolicy.SUMMARY),
        ("Elastic-2.0", ExtractPolicy.SUMMARY),
        ("unknown", ExtractPolicy.LINK),
        ("MPL-2.0", ExtractPolicy.LINK),
        ("CC-BY-4.0", ExtractPolicy.LINK),
        ("", ExtractPolicy.LINK),
    ],
)
def test_max_policy_escopo_code(licenca: str, esperada: ExtractPolicy) -> None:
    """Tabela única licença → máxima; não classificada → link (FR-002, FR-003)."""
    assert max_policy(licenca, ExtractScope.CODE) is esperada


def test_max_policy_escopo_padrao_eh_code() -> None:
    """Sem escopo informado, vale o escopo code (FR-010)."""
    assert max_policy("GPL-3.0") is ExtractPolicy.SUMMARY


@pytest.mark.parametrize(
    ("licenca", "esperada"),
    [
        ("mit", "verbatim"),
        ("APACHE-2.0", "verbatim"),
        ("elastic-2.0", "summary"),
        ("UNKNOWN", "link"),
    ],
)
def test_max_policy_ignora_caixa(licenca: str, esperada: str) -> None:
    """Comparação sem diferenciar maiúsculas (FR-011)."""
    assert max_policy(licenca).value == esperada


@pytest.mark.parametrize(
    ("licenca", "classificada"),
    [
        ("MIT", True),
        ("bsd-3-clause", True),
        ("Apache-2.0", True),
        ("GPL-3.0", True),
        ("Elastic-2.0", True),
        ("unknown", True),
        ("MPL-2.0", False),
        ("", False),
    ],
)
def test_is_classified(licenca: str, classificada: bool) -> None:
    """Só as licenças da tabela (e unknown) são classificadas."""
    assert is_classified(licenca) is classificada


@pytest.mark.parametrize(
    ("licenca", "docs", "code"),
    [
        ("GPL-3.0", ExtractPolicy.VERBATIM, ExtractPolicy.SUMMARY),
        ("gpl-3.0", ExtractPolicy.VERBATIM, ExtractPolicy.SUMMARY),
        ("MIT", ExtractPolicy.VERBATIM, ExtractPolicy.VERBATIM),
        ("Elastic-2.0", ExtractPolicy.SUMMARY, ExtractPolicy.SUMMARY),
        ("unknown", ExtractPolicy.LINK, ExtractPolicy.LINK),
        ("MPL-2.0", ExtractPolicy.LINK, ExtractPolicy.LINK),
    ],
)
def test_escopo_so_altera_gpl(licenca: str, docs: ExtractPolicy, code: ExtractPolicy) -> None:
    """GPL-3.0: documentação verbatim, código summary; demais licenças ignoram o escopo."""
    assert max_policy(licenca, ExtractScope.DOCS) is docs
    assert max_policy(licenca, ExtractScope.CODE) is code
