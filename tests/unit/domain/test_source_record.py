# -*- coding: utf-8 -*-
"""
NOME: test_source_record.py
TITULO: Testes de falha — entidade SourceRecord v3 (só ideias)
DATA: 22/09/2026 10:30
MODIFICADO: 25/09/2026 13:04
VERSÃO: 0.3.0
DEPEND: pytest, praxisforge.domain.source_record
HISTÓRICO:
    - 22/09/2026 10:30: criação (T055)
    - 24/09/2026 10:53: v2 — extract_policy, atribuição e regra licença × política
      (T011, feature 006)
    - 25/09/2026 13:04: v3 — sem níveis de extração; licença só informativa (T040, feature 009)
STATUS: DEV
"""

from datetime import date, timedelta

import pytest

from praxisforge.domain.errors import InvalidFolderError
from praxisforge.domain.source_record import SourceRecord


def _make(**overrides: object) -> SourceRecord:
    fields: dict[str, object] = {
        "origin": "https://github.com/exemplo/repo",
        "date": date(2026, 9, 21),
        "license": "MIT",
        "relevance": "referência principal",
        "status": "active",
        "author": "Fulano",
    }
    fields.update(overrides)
    return SourceRecord(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize("campo", ["origin", "relevance"])
def test_campos_obrigatorios_vazios_levantam_erro(campo: str) -> None:
    """origin e relevance vazios são inválidos."""
    with pytest.raises(InvalidFolderError):
        _make(**{campo: ""})


def test_licenca_vazia_eh_recusada() -> None:
    """license é obrigatória (registro informativo, mas presente)."""
    with pytest.raises(InvalidFolderError):
        _make(license="")


def test_status_invalido_eh_recusado() -> None:
    """status fora de active/pending é inválido."""
    with pytest.raises(InvalidFolderError):
        _make(status="ativo")


def test_licenca_unknown_exige_pending() -> None:
    """Fonte sem licença conhecida fica pendente (constituição, Princípio V)."""
    with pytest.raises(InvalidFolderError):
        _make(license="unknown", status="active")


def test_unknown_pending_eh_valido() -> None:
    """unknown + pending é válido."""
    assert _make(license="unknown", status="pending").status == "pending"


def test_data_futura_eh_recusada() -> None:
    """date no futuro é inválida."""
    with pytest.raises(InvalidFolderError):
        _make(date=date.today() + timedelta(days=1))


def test_origin_com_caminho_absoluto_eh_recusado() -> None:
    """origin com caminho absoluto é inválido."""
    with pytest.raises(InvalidFolderError):
        _make(origin="/home/user/repo")


@pytest.mark.parametrize("licenca", ["MIT", "GPL-3.0", "Elastic-2.0", "MPL-2.0", "mit"])
def test_qualquer_licenca_conhecida_eh_aceita(licenca: str) -> None:
    """Só ideias: a licença não gradua nada; qualquer valor conhecido é aceito e preservado."""
    assert _make(license=licenca).license == licenca


def test_author_opcional() -> None:
    """author é opcional no v3."""
    assert _make(author=None).author is None
