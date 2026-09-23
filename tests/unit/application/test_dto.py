# -*- coding: utf-8 -*-
"""
NOME: test_dto.py
TITULO: Testes de falha — DTOs pydantic de entrada da Application
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:48
VERSÃO: 0.1.0
DEPEND: pytest, pydantic, praxisforge.application.dto
HISTÓRICO:
    - 22/09/2026 09:45: criação (T014)
STATUS: DEV
"""

import pytest
from pydantic import ValidationError

from praxisforge.application.dto import RegisterFolderInput, UpdateFolderInput


@pytest.mark.parametrize(
    "campos",
    [
        {"alias": "", "description": "d", "content_type": "docs", "license": "MIT"},
        {"alias": 123, "description": "d", "content_type": "docs", "license": "MIT"},
        {"alias": "exemplo", "description": "", "content_type": "docs", "license": "MIT"},
        {"alias": "Exemplo", "description": "d", "content_type": "docs", "license": "MIT"},
    ],
)
def test_register_folder_input_rejeita_dados_invalidos(campos: dict[str, object]) -> None:
    """RegisterFolderInput rejeita tipos errados, vazios e alias inválido."""
    with pytest.raises(ValidationError):
        RegisterFolderInput(**campos)  # type: ignore[arg-type]


def test_register_folder_input_aceita_dados_validos() -> None:
    """RegisterFolderInput aceita um conjunto de dados válido."""
    dto = RegisterFolderInput(
        alias="exemplo",
        description="d",
        content_type="docs",
        license="MIT",
        status=None,
        path="/srv/pastas/exemplo",
    )
    assert dto.alias == "exemplo"


@pytest.mark.parametrize(
    "campos",
    [
        {"alias": ""},
        {"alias": 123},
    ],
)
def test_update_folder_input_rejeita_alias_invalido(campos: dict[str, object]) -> None:
    """UpdateFolderInput rejeita alias vazio ou de tipo errado."""
    with pytest.raises(ValidationError):
        UpdateFolderInput(**campos)  # type: ignore[arg-type]


def test_update_folder_input_aceita_apenas_alias() -> None:
    """UpdateFolderInput aceita apenas o alias, sem nenhum outro campo informado."""
    dto = UpdateFolderInput(alias="exemplo")
    assert dto.alias == "exemplo"
    assert dto.status is None
    assert dto.last_scanned is None
    assert dto.license is None
