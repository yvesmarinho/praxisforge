# -*- coding: utf-8 -*-
"""
NOME: test_validate_sources.py
TITULO: Testes de falha — caso de uso validate_sources (lote, schema v2 + domínio)
DATA: 24/09/2026 10:53
MODIFICADO: 24/09/2026 10:53
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.validate_sources
HISTÓRICO:
    - 24/09/2026 10:53: criação (T012, feature 006)
STATUS: DEV
"""

from collections.abc import Mapping
from pathlib import Path

from praxisforge.application.errors import ContractValidationError, RegistryUnavailableError
from praxisforge.application.ports import ContractValidator, SourceReader
from praxisforge.application.validate_sources import SourceValidationReport, validate_sources
from praxisforge.domain.errors import Violation


class _FakeReader(SourceReader):
    def __init__(self, documentos: Mapping[Path, dict[str, object] | Exception]) -> None:
        self._documentos = documentos

    def read(self, path: Path) -> dict[str, object]:
        documento = self._documentos[path]
        if isinstance(documento, Exception):
            raise documento
        return dict(documento)


class _FakeValidator(ContractValidator):
    """Aceita tudo, salvo documentos marcados com _invalido; registra o schema usado."""

    def __init__(self) -> None:
        self.schemas: list[str] = []

    def validate(self, document: Mapping[str, object], schema_name: str) -> None:
        self.schemas.append(schema_name)
        if document.get("_invalido"):
            raise ContractValidationError([Violation(field="origin", reason="vazio")])


def _fonte(**campos: object) -> dict[str, object]:
    documento: dict[str, object] = {
        "schema_version": "2",
        "origin": "https://github.com/exemplo/repo",
        "author": "Fulano",
        "date": "2026-09-20",
        "license": "MIT",
        "relevance": "padrões",
        "status": "active",
        "extract_policy": "verbatim",
        "notice_preserved": True,
    }
    documento.update(campos)
    return documento


def _validar(
    documentos: dict[Path, dict[str, object] | Exception],
) -> tuple[SourceValidationReport, _FakeValidator]:
    validator = _FakeValidator()
    report = validate_sources(_FakeReader(documentos), validator, list(documentos))
    return report, validator


def test_lote_misto_avalia_todos_e_agrega_falhas() -> None:
    """Válido, schema inválido e domínio inválido: 1 ok, 2 falhas (FR-012)."""
    ok, forma, dominio = Path("a.md"), Path("b.md"), Path("c.md")
    report, validator = _validar(
        {
            ok: _fonte(),
            forma: _fonte(_invalido=True),
            dominio: _fonte(license="Elastic-2.0"),
        }
    )
    assert report.ok == [ok]
    falhas = {f.path: f for f in report.failures}
    assert set(falhas) == {forma, dominio}
    assert falhas[forma].error_type == "ContractValidationError"
    assert falhas[dominio].error_type == "ExtractPolicyExceedsLicenseError"
    assert "máxima 'summary'" in falhas[dominio].message
    assert set(validator.schemas) == {"source-schema-v2"}


def test_registro_v1_pede_extract_policy() -> None:
    """schema_version 1 ou extract_allowed → SourceSchemaMigrationRequiredError (FR-014)."""
    v1, antigo = Path("v1.md"), Path("antigo.md")
    report, validator = _validar(
        {
            v1: {"schema_version": "1", "extract_allowed": True},
            antigo: _fonte(extract_allowed=False),
        }
    )
    assert report.ok == []
    for falha in report.failures:
        assert falha.error_type == "SourceSchemaMigrationRequiredError"
        assert "extract_policy" in falha.message
    assert validator.schemas == []


def test_arquivo_ilegivel_vira_falha_do_item() -> None:
    """Falha do reader (filesystem) não derruba o lote."""
    ruim, bom = Path("ruim.md"), Path("bom.md")
    report, _ = _validar({ruim: RegistryUnavailableError("fonte sem frontmatter"), bom: _fonte()})
    assert report.ok == [bom]
    assert report.failures[0].path == ruim
    assert report.failures[0].error_type == "RegistryUnavailableError"


def test_data_malformada_vira_falha_do_item() -> None:
    """date fora do ISO (quando o schema deixa passar) é falha do item, não exceção solta."""
    report, _ = _validar({Path("x.md"): _fonte(date="21/09/2026")})
    assert report.ok == []
    assert len(report.failures) == 1


def test_lista_vazia_devolve_relatorio_vazio() -> None:
    """Nenhum arquivo: nada a validar, sem erro."""
    report, _ = _validar({})
    assert report.ok == [] and report.failures == []


def test_licenca_nao_classificada_com_link_passa_sem_aviso() -> None:
    """MPL-2.0 com link é válido e não gera falha (Clarificação Q3)."""
    report, _ = _validar({Path("m.md"): _fonte(license="MPL-2.0", extract_policy="link")})
    assert len(report.ok) == 1 and report.failures == []


def test_resultado_ordenado_por_caminho() -> None:
    """ok e failures ordenados (determinismo)."""
    report, _ = _validar(
        {Path("z.md"): _fonte(), Path("a.md"): _fonte(), Path("m.md"): _fonte(license="unknown")}
    )
    assert report.ok == [Path("a.md"), Path("z.md")]
