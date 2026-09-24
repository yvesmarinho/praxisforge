# -*- coding: utf-8 -*-
"""
NOME: license_policy.py
TITULO: Política de extração por licença — níveis ordenados e tabela licença → máxima
DATA: 24/09/2026 10:52
MODIFICADO: 24/09/2026 10:57
VERSÃO: 0.1.0
DEPEND: (stdlib)
HISTÓRICO:
    - 24/09/2026 10:52: criação (T008, feature 006) — faz test_license_policy.py passar
    - 24/09/2026 10:57: GPL-3.0 verbatim para documentação (T032, US3, feature 006)
STATUS: DEV
"""

from enum import Enum
from functools import total_ordering
from types import MappingProxyType


@total_ordering
class ExtractPolicy(Enum):
    """
    Nível do que pode ser reproduzido de uma fonte no repositório público.

    Ordenado: link < summary < verbatim.

    :Example:

    >>> ExtractPolicy("summary") < ExtractPolicy.VERBATIM
    True
    """

    LINK = "link"
    SUMMARY = "summary"
    VERBATIM = "verbatim"

    @property
    def rank(self) -> int:
        """Posição do nível na ordem (0 = mais restritivo)."""
        return _ORDEM.index(self)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ExtractPolicy):
            return NotImplemented
        return self.rank < other.rank


_ORDEM = (ExtractPolicy.LINK, ExtractPolicy.SUMMARY, ExtractPolicy.VERBATIM)


class ExtractScope(Enum):
    """Natureza do extrato: documentação ou código (relevante para licenças copyleft)."""

    DOCS = "docs"
    CODE = "code"


# licença (casefold) → (máxima para docs, máxima para code)
_TABELA = MappingProxyType(
    {
        "mit": (ExtractPolicy.VERBATIM, ExtractPolicy.VERBATIM),
        "bsd-3-clause": (ExtractPolicy.VERBATIM, ExtractPolicy.VERBATIM),
        "apache-2.0": (ExtractPolicy.VERBATIM, ExtractPolicy.VERBATIM),
        "gpl-3.0": (ExtractPolicy.VERBATIM, ExtractPolicy.SUMMARY),  # código herda a GPL
        "elastic-2.0": (ExtractPolicy.SUMMARY, ExtractPolicy.SUMMARY),
        "unknown": (ExtractPolicy.LINK, ExtractPolicy.LINK),
    }
)


def is_classified(license: str) -> bool:  # noqa: A002
    """
    Informa se a licença consta da tabela (comparação sem caixa).

    :param license: identificador SPDX ou "unknown".
    :type license: str
    :return: True se a licença é classificada.
    :rtype: bool

    :Example:

    >>> is_classified("mit"), is_classified("MPL-2.0")
    (True, False)
    """
    return license.casefold() in _TABELA


def max_policy(license: str, scope: ExtractScope = ExtractScope.CODE) -> ExtractPolicy:  # noqa: A002
    """
    Política máxima permitida pela licença; não classificada → link.

    :param license: identificador SPDX ou "unknown".
    :type license: str
    :param scope: natureza do extrato (padrão: código, o caso conservador).
    :type scope: ExtractScope
    :return: nível máximo de extração.
    :rtype: ExtractPolicy

    :Example:

    >>> max_policy("Elastic-2.0").value
    'summary'
    >>> max_policy("MPL-2.0").value
    'link'
    """
    docs, code = _TABELA.get(license.casefold(), (ExtractPolicy.LINK, ExtractPolicy.LINK))
    return docs if scope is ExtractScope.DOCS else code
