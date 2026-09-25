# -*- coding: utf-8 -*-
"""
NOME: source_record.py
TITULO: Entidade SourceRecord — proveniência de uma fonte curada
DATA: 22/09/2026 10:30
MODIFICADO: 25/09/2026 13:05
VERSÃO: 0.3.0
DEPEND: praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 10:30: criação (T056) — faz tests/unit/domain/test_source_record.py passar
    - 24/09/2026 10:55: v2 — extract_policy, atribuição e regra licença × política
      (T017, feature 006)
    - 25/09/2026 13:05: v3 — só ideias; licença obrigatória e informativa (T042, feature 009)
STATUS: DEV
"""

import re
from dataclasses import dataclass
from datetime import date

from praxisforge.domain.errors import InvalidFolderError

_ABSOLUTE_PATH_PATTERN = re.compile(r"^(/|[A-Za-z]:\\)")


@dataclass(frozen=True)
class SourceRecord:
    """
    Entidade SourceRecord — proveniência de uma fonte curada (frontmatter v3, só ideias).

    Das fontes só se extraem ideias (constituição v4.0.0, Princípio V): a licença é registro
    obrigatório, mas não gradua nada. Fonte sem licença conhecida fica `pending`.

    :param origin: URL ou descrição da origem; não vazia, sem caminho absoluto.
    :type origin: str
    :param date: data de registro da fonte; não futura.
    :type date: date
    :param license: identificador SPDX ou `"unknown"`; não vazio.
    :type license: str
    :param relevance: justificativa de relevância; não vazia.
    :type relevance: str
    :param status: `"active"` ou `"pending"`.
    :type status: str
    :param author: autor da fonte (opcional).
    :type author: str | None
    :raises InvalidFolderError: invariante de forma ou status violada.

    :Example:

    >>> SourceRecord(
    ...     origin="https://x", date=date(2026, 9, 1), license="MIT", relevance="r",
    ...     status="active",
    ... ).license
    'MIT'
    """

    origin: str
    date: date
    license: str  # noqa: A003
    relevance: str
    status: str
    author: str | None = None

    def __post_init__(self) -> None:
        if not self.origin:
            raise InvalidFolderError("fonte: origin vazio")
        if _ABSOLUTE_PATH_PATTERN.match(self.origin):
            raise InvalidFolderError("fonte: origin não pode ser um caminho absoluto")
        if not self.relevance:
            raise InvalidFolderError("fonte: relevance vazio")
        if not self.license:
            raise InvalidFolderError("fonte: license vazia")
        if self.status not in ("active", "pending"):
            raise InvalidFolderError(f"fonte: status inválido {self.status!r}")
        if self.date > date.today():
            raise InvalidFolderError("fonte: date não pode estar no futuro")
        if self.license.casefold() == "unknown" and self.status != "pending":
            raise InvalidFolderError("fonte: licença 'unknown' exige status 'pending'")
