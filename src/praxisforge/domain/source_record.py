# -*- coding: utf-8 -*-
"""
NOME: source_record.py
TITULO: Entidade SourceRecord — proveniência de uma fonte curada
DATA: 22/09/2026 10:30
MODIFICADO: 22/09/2026 10:06
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 10:30: criação (T056) — faz tests/unit/domain/test_source_record.py passar
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
    Entidade SourceRecord — proveniência de uma fonte curada (frontmatter).

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
    :param extract_allowed: se a extração é permitida; obrigatoriamente False quando pending.
    :type extract_allowed: bool
    :raises InvalidFolderError: quando uma invariante é violada.
    """

    origin: str
    date: date
    license: str  # noqa: A003
    relevance: str
    status: str
    extract_allowed: bool

    def __post_init__(self) -> None:
        if not self.origin:
            raise InvalidFolderError("fonte: origin vazio")
        if _ABSOLUTE_PATH_PATTERN.match(self.origin):
            raise InvalidFolderError("fonte: origin não pode ser um caminho absoluto")
        if not self.relevance:
            raise InvalidFolderError("fonte: relevance vazio")
        if self.status not in ("active", "pending"):
            raise InvalidFolderError(f"fonte: status inválido {self.status!r}")
        if self.license == "unknown" and self.status != "pending":
            raise InvalidFolderError("fonte: licença 'unknown' exige status 'pending'")
        if self.status == "pending" and self.extract_allowed:
            raise InvalidFolderError("fonte: status 'pending' exige extract_allowed=false")
        if self.date > date.today():
            raise InvalidFolderError("fonte: date não pode estar no futuro")
