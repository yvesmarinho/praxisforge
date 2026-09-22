# -*- coding: utf-8 -*-
"""
NOME: test_source_record.py
TITULO: Testes de falha — entidade SourceRecord (proveniência)
DATA: 22/09/2026 10:30
MODIFICADO: 22/09/2026 10:04
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.source_record
HISTÓRICO:
    - 22/09/2026 10:30: criação (T050)
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
        "extract_allowed": True,
    }
    fields.update(overrides)
    return SourceRecord(**fields)  # type: ignore[arg-type]


def test_campos_obrigatorios_vazios_levantam_erro() -> None:
    """origin/relevance vazios são inválidos."""
    with pytest.raises(InvalidFolderError):
        _make(origin="")
    with pytest.raises(InvalidFolderError):
        _make(relevance="")


def test_licenca_unknown_forca_pending_e_extract_allowed_false() -> None:
    """license 'unknown' exige status 'pending' e extract_allowed False."""
    with pytest.raises(InvalidFolderError):
        _make(license="unknown", status="active", extract_allowed=False)


def test_pending_com_extract_allowed_true_eh_recusado() -> None:
    """status 'pending' exige extract_allowed False."""
    with pytest.raises(InvalidFolderError):
        _make(status="pending", extract_allowed=True)


def test_data_futura_eh_recusada() -> None:
    """date no futuro é inválida."""
    futuro = date.today() + timedelta(days=1)
    with pytest.raises(InvalidFolderError):
        _make(date=futuro)


def test_origin_com_caminho_absoluto_eh_recusado() -> None:
    """origin com caminho absoluto é inválido."""
    with pytest.raises(InvalidFolderError):
        _make(origin="/home/user/repo")


def test_caso_feliz_valido() -> None:
    """Uma SourceRecord válida é construída sem levantar (acompanha os testes de falha acima)."""
    record = _make()
    assert record.origin == "https://github.com/exemplo/repo"
