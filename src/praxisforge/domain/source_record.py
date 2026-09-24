# -*- coding: utf-8 -*-
"""
NOME: source_record.py
TITULO: Entidade SourceRecord — proveniência de uma fonte curada
DATA: 22/09/2026 10:30
MODIFICADO: 24/09/2026 10:55
VERSÃO: 0.2.0
DEPEND: praxisforge.domain.errors, praxisforge.domain.license_policy
HISTÓRICO:
    - 22/09/2026 10:30: criação (T056) — faz tests/unit/domain/test_source_record.py passar
    - 24/09/2026 10:55: v2 — extract_policy, atribuição e regra licença × política
      (T017, feature 006)
STATUS: DEV
"""

import re
from dataclasses import dataclass
from datetime import date

from praxisforge.domain.errors import (
    ExtractPolicyExceedsLicenseError,
    IncompleteAttributionError,
    InvalidFolderError,
)
from praxisforge.domain.license_policy import ExtractPolicy, ExtractScope, max_policy

_ABSOLUTE_PATH_PATTERN = re.compile(r"^(/|[A-Za-z]:\\)")


@dataclass(frozen=True)
class SourceRecord:
    """
    Entidade SourceRecord — proveniência de uma fonte curada (frontmatter v2).

    Ordem de verificação (determinística): forma → status/licença → política ≤ máxima →
    atribuição (`author`) → `notice_preserved` (verbatim) → `modified` (Apache-2.0 verbatim).

    :param origin: URL ou descrição da origem; não vazia, sem caminho absoluto.
    :type origin: str
    :param date: data de registro da fonte; não futura.
    :type date: date
    :param license: identificador SPDX ou `"unknown"`.
    :type license: str
    :param relevance: justificativa de relevância; não vazia.
    :type relevance: str
    :param status: `"active"` ou `"pending"`.
    :type status: str
    :param extract_policy: política declarada; não pode exceder a máxima da licença.
    :type extract_policy: ExtractPolicy
    :param author: autor da fonte; obrigatório quando a política é summary ou verbatim.
    :type author: str | None
    :param extract_scope: natureza do extrato; ausente equivale a código.
    :type extract_scope: ExtractScope | None
    :param notice_preserved: aviso de copyright e licença preservados; exigido em verbatim.
    :type notice_preserved: bool | None
    :param modified: se o trecho copiado foi alterado; exigido em verbatim de Apache-2.0.
    :type modified: bool | None
    :raises InvalidFolderError: invariante de forma ou status violada.
    :raises ExtractPolicyExceedsLicenseError: política declarada acima da máxima.
    :raises IncompleteAttributionError: campo de atribuição/conformidade ausente.

    :Example:

    >>> SourceRecord(
    ...     origin="https://x", date=date(2026, 9, 1), license="MIT", relevance="r",
    ...     status="active", extract_policy=ExtractPolicy.LINK,
    ... ).extract_policy.value
    'link'
    """

    origin: str
    date: date
    license: str  # noqa: A003
    relevance: str
    status: str
    extract_policy: ExtractPolicy
    author: str | None = None
    extract_scope: ExtractScope | None = None
    notice_preserved: bool | None = None
    modified: bool | None = None

    def __post_init__(self) -> None:
        self._verificar_forma()
        self._verificar_status()
        self._verificar_politica()
        self._verificar_atribuicao()

    def _verificar_forma(self) -> None:
        if not self.origin:
            raise InvalidFolderError("fonte: origin vazio")
        if _ABSOLUTE_PATH_PATTERN.match(self.origin):
            raise InvalidFolderError("fonte: origin não pode ser um caminho absoluto")
        if not self.relevance:
            raise InvalidFolderError("fonte: relevance vazio")
        if self.status not in ("active", "pending"):
            raise InvalidFolderError(f"fonte: status inválido {self.status!r}")
        if self.date > date.today():
            raise InvalidFolderError("fonte: date não pode estar no futuro")

    def _verificar_status(self) -> None:
        if self.license.casefold() == "unknown" and self.status != "pending":
            raise InvalidFolderError("fonte: licença 'unknown' exige status 'pending'")
        if self.status == "pending" and self.extract_policy is not ExtractPolicy.LINK:
            raise InvalidFolderError("fonte: status 'pending' exige extract_policy 'link'")

    def _verificar_politica(self) -> None:
        escopo = self.extract_scope or ExtractScope.CODE
        maxima = max_policy(self.license, escopo)
        if self.extract_policy > maxima:
            raise ExtractPolicyExceedsLicenseError(
                license=self.license,
                scope=escopo.value,
                declared=self.extract_policy.value,
                maximum=maxima.value,
            )

    def _verificar_atribuicao(self) -> None:
        politica = self.extract_policy
        if politica is ExtractPolicy.LINK:
            return
        if not self.author:
            raise IncompleteAttributionError(field="author", policy=politica.value)
        if politica is not ExtractPolicy.VERBATIM:
            return
        if self.notice_preserved is not True:
            raise IncompleteAttributionError(field="notice_preserved", policy=politica.value)
        if self.license.casefold() == "apache-2.0" and self.modified is None:
            raise IncompleteAttributionError(field="modified", policy=politica.value)
