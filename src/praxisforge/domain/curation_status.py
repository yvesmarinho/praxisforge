# -*- coding: utf-8 -*-
"""
NOME: curation_status.py
TITULO: Enum CurationStatus — status de curadoria de uma pasta
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 16:36
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 09:45: criação (T019) — faz tests/unit/domain/test_curation_status.py passar
    - 22/09/2026 17:40: +IGNORE (T007, feature 003-bootstrap-registro-pastas)
STATUS: DEV
"""

from enum import Enum

from praxisforge.domain.errors import PraxisForgeError

_ROTULOS_PT_BR = {
    "not_scanned": "não varrida",
    "scanned": "varrida",
    "in_curation": "em curadoria",
    "curated": "curada",
    "pending": "pendente",
    "ignore": "ignorada",
}


class CurationStatus(Enum):
    """Status de curadoria de uma pasta registrada."""

    NOT_SCANNED = "not_scanned"
    SCANNED = "scanned"
    IN_CURATION = "in_curation"
    CURATED = "curated"
    PENDING = "pending"
    IGNORE = "ignore"

    @classmethod
    def from_str(cls, value: str) -> "CurationStatus":
        """
        Converte uma string no enum correspondente.

        :param value: valor de máquina (ex.: `"pending"`).
        :type value: str
        :return: instância de CurationStatus.
        :rtype: CurationStatus
        :raises PraxisForgeError: quando `value` não é um status conhecido.

        :Example:

        >>> CurationStatus.from_str("pending") is CurationStatus.PENDING
        True
        """
        try:
            return cls(value)
        except ValueError as error:
            raise PraxisForgeError(f"status de curadoria inválido: {value!r}") from error

    def label_pt_br(self) -> str:
        """
        Rótulo em pt-BR para exibição na CLI.

        :return: rótulo (ex.: `"pendente"`).
        :rtype: str
        """
        return _ROTULOS_PT_BR[self.value]
