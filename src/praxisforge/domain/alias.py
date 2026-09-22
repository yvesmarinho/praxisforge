# -*- coding: utf-8 -*-
"""
NOME: alias.py
TITULO: Value object Alias — identificador de pasta a curar
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:49
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 09:45: criação (T018) — faz tests/unit/domain/test_alias.py passar
STATUS: DEV
"""

import re
from dataclasses import dataclass

from praxisforge.domain.errors import InvalidAliasError

_ALIAS_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,62}$")


@dataclass(frozen=True)
class Alias:
    """
    Value object imutável do identificador de uma pasta a curar.

    :param value: string no formato `^[a-z][a-z0-9_]{1,62}$`.
    :type value: str
    :raises InvalidAliasError: quando `value` não atende ao formato.

    :Example:

    >>> Alias("github_forks").env_var_name
    'PRAXISFORGE_FOLDER_GITHUB_FORKS'
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _ALIAS_PATTERN.match(self.value):
            raise InvalidAliasError(f"alias inválido: {self.value!r}")

    def __str__(self) -> str:
        return self.value

    @property
    def env_var_name(self) -> str:
        """
        Nome da variável de ambiente que resolve o caminho real deste alias.

        :return: `PRAXISFORGE_FOLDER_<ALIAS EM MAIÚSCULAS>`.
        :rtype: str
        """
        return f"PRAXISFORGE_FOLDER_{self.value.upper()}"
