# -*- coding: utf-8 -*-
"""
NOME: test_source_record.py
TITULO: Testes de falha — entidade SourceRecord v2 (política de extração)
DATA: 22/09/2026 10:30
MODIFICADO: 24/09/2026 10:53
VERSÃO: 0.2.0
DEPEND: pytest, praxisforge.domain.source_record, praxisforge.domain.license_policy
HISTÓRICO:
    - 22/09/2026 10:30: criação (T055)
    - 24/09/2026 10:53: v2 — extract_policy, atribuição e regra licença × política
      (T011, feature 006)
STATUS: DEV
"""

from datetime import date, timedelta

import pytest

from praxisforge.domain.errors import (
    ExtractPolicyExceedsLicenseError,
    IncompleteAttributionError,
    InvalidFolderError,
)
from praxisforge.domain.license_policy import ExtractPolicy, ExtractScope
from praxisforge.domain.source_record import SourceRecord


def _make(**overrides: object) -> SourceRecord:
    fields: dict[str, object] = {
        "origin": "https://github.com/exemplo/repo",
        "date": date(2026, 9, 21),
        "license": "MIT",
        "relevance": "referência principal",
        "status": "active",
        "extract_policy": ExtractPolicy.VERBATIM,
        "author": "Fulano",
        "notice_preserved": True,
    }
    fields.update(overrides)
    return SourceRecord(**fields)  # type: ignore[arg-type]


# --- invariantes herdadas da v1 ---------------------------------------------------------


def test_campos_obrigatorios_vazios_levantam_erro() -> None:
    """origin/relevance vazios são inválidos."""
    with pytest.raises(InvalidFolderError):
        _make(origin="")
    with pytest.raises(InvalidFolderError):
        _make(relevance="")


def test_status_invalido_eh_recusado() -> None:
    """status fora de active/pending é inválido."""
    with pytest.raises(InvalidFolderError):
        _make(status="archived")


def test_licenca_unknown_exige_pending() -> None:
    """license 'unknown' com status active é inválida (FR-006)."""
    with pytest.raises(InvalidFolderError):
        _make(license="unknown", status="active", extract_policy=ExtractPolicy.LINK)


@pytest.mark.parametrize("politica", [ExtractPolicy.SUMMARY, ExtractPolicy.VERBATIM])
def test_pending_exige_link(politica: ExtractPolicy) -> None:
    """status 'pending' só admite política link (FR-006)."""
    with pytest.raises(InvalidFolderError):
        _make(status="pending", extract_policy=politica)


def test_data_futura_eh_recusada() -> None:
    """date no futuro é inválida."""
    with pytest.raises(InvalidFolderError):
        _make(date=date.today() + timedelta(days=1))


def test_origin_com_caminho_absoluto_eh_recusado() -> None:
    """origin com caminho absoluto é inválido."""
    with pytest.raises(InvalidFolderError):
        _make(origin="/home/user/repo")


# --- política × licença (FR-004, FR-005, SC-001) ----------------------------------------

_MAXIMAS = {
    "MIT": ExtractPolicy.VERBATIM,
    "BSD-3-Clause": ExtractPolicy.VERBATIM,
    "Apache-2.0": ExtractPolicy.VERBATIM,
    "GPL-3.0": ExtractPolicy.SUMMARY,
    "Elastic-2.0": ExtractPolicy.SUMMARY,
    "MPL-2.0": ExtractPolicy.LINK,
}

_MATRIZ = [(licenca, politica) for licenca in _MAXIMAS for politica in ExtractPolicy]


@pytest.mark.parametrize(("licenca", "politica"), _MATRIZ)
def test_matriz_licenca_politica(licenca: str, politica: ExtractPolicy) -> None:
    """Declarada ≤ máxima passa; acima da máxima levanta erro semântico com os 4 dados."""
    campos: dict[str, object] = {"license": licenca, "extract_policy": politica, "modified": False}
    maxima = _MAXIMAS[licenca]
    if politica <= maxima:
        assert _make(**campos).extract_policy is politica
        return
    with pytest.raises(ExtractPolicyExceedsLicenseError) as info:
        _make(**campos)
    assert info.value.license == licenca
    assert info.value.scope == "code"
    assert info.value.declared == politica.value
    assert info.value.maximum == maxima.value


def test_unknown_pending_link_eh_valido() -> None:
    """Fonte sem licença: pending + link é o único estado válido."""
    record = _make(license="unknown", status="pending", extract_policy=ExtractPolicy.LINK)
    assert record.status == "pending"


def test_licenca_em_caixa_diferente_eh_preservada() -> None:
    """Comparação sem caixa; valor registrado preservado (FR-011)."""
    record = _make(license="mit")
    assert record.license == "mit"


# --- atribuição e conformidade (FR-007, FR-008, FR-009) ---------------------------------


@pytest.mark.parametrize("politica", [ExtractPolicy.SUMMARY, ExtractPolicy.VERBATIM])
@pytest.mark.parametrize("autor", [None, ""])
def test_summary_e_verbatim_exigem_author(politica: ExtractPolicy, autor: str | None) -> None:
    """Sem autor não há atribuição completa."""
    with pytest.raises(IncompleteAttributionError) as info:
        _make(extract_policy=politica, author=autor)
    assert info.value.field == "author"


def test_link_dispensa_author() -> None:
    """Política link só exige origem e licença."""
    record = _make(extract_policy=ExtractPolicy.LINK, author=None, notice_preserved=None)
    assert record.author is None


@pytest.mark.parametrize("preservado", [None, False])
def test_verbatim_exige_notice_preserved_true(preservado: bool | None) -> None:
    """Cópia literal exige aviso de copyright e licença preservados."""
    with pytest.raises(IncompleteAttributionError) as info:
        _make(notice_preserved=preservado)
    assert info.value.field == "notice_preserved"


def test_summary_dispensa_notice_preserved() -> None:
    """notice_preserved só é exigido em verbatim."""
    assert _make(extract_policy=ExtractPolicy.SUMMARY, notice_preserved=None)


def test_apache_verbatim_exige_modified() -> None:
    """Apache-2.0 exige declarar se o trecho copiado foi alterado."""
    with pytest.raises(IncompleteAttributionError) as info:
        _make(license="Apache-2.0", modified=None)
    assert info.value.field == "modified"


@pytest.mark.parametrize("alterado", [True, False])
def test_apache_verbatim_com_modified_declarado_passa(alterado: bool) -> None:
    """Qualquer valor declarado de modified é aceito."""
    assert _make(license="apache-2.0", modified=alterado).modified is alterado


def test_mit_verbatim_dispensa_modified() -> None:
    """modified só é exigido para Apache-2.0."""
    assert _make(license="MIT", modified=None)


# --- GPL-3.0 por escopo (FR-010, US3) ----------------------------------------------------


def test_gpl_verbatim_em_documentacao_eh_aceito() -> None:
    """Documentação GPL pode ser copiada literalmente."""
    record = _make(license="GPL-3.0", extract_scope=ExtractScope.DOCS)
    assert record.extract_scope is ExtractScope.DOCS


@pytest.mark.parametrize("escopo", [ExtractScope.CODE, None])
def test_gpl_verbatim_em_codigo_ou_sem_escopo_excede(escopo: ExtractScope | None) -> None:
    """Código GPL (ou escopo ausente) fica limitado a summary."""
    with pytest.raises(ExtractPolicyExceedsLicenseError) as info:
        _make(license="GPL-3.0", extract_scope=escopo)
    assert info.value.scope == "code"
    assert info.value.maximum == "summary"
