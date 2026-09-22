# -*- coding: utf-8 -*-
"""
NOME: test_alias.py
TITULO: Testes de falha — value object Alias
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:51
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.alias
HISTÓRICO:
    - 22/09/2026 09:45: criação (T006)
STATUS: DEV
"""

import pytest

from praxisforge.domain.alias import Alias
from praxisforge.domain.errors import InvalidAliasError


@pytest.mark.parametrize(
    "valor",
    [
        "",
        "   ",
        "Exemplo",
        "GITHUB_FORKS",
        "1exemplo",
        "exemplo/sub",
        "..",
        "a",
        "a" * 65,
    ],
)
def test_alias_invalido_levanta_erro(valor: str) -> None:
    """Formatos inválidos de alias levantam InvalidAliasError."""
    with pytest.raises(InvalidAliasError):
        Alias(valor)


def test_alias_valido_eh_aceito() -> None:
    """Um alias válido é aceito e preserva o valor."""
    alias = Alias("github_forks")
    assert str(alias) == "github_forks"


def test_alias_env_var_name() -> None:
    """env_var_name converte o alias para PRAXISFORGE_FOLDER_<ALIAS MAIÚSCULO>."""
    alias = Alias("github_forks")
    assert alias.env_var_name == "PRAXISFORGE_FOLDER_GITHUB_FORKS"


def test_alias_eh_imutavel() -> None:
    """Alias é um value object imutável (frozen dataclass)."""
    alias = Alias("github_forks")
    with pytest.raises(AttributeError):
        alias.value = "outro"  # type: ignore[misc]
