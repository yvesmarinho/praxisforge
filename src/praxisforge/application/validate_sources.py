# -*- coding: utf-8 -*-
"""
NOME: validate_sources.py
TITULO: Caso de uso — validar registros de fonte (schema v2 + política de extração), em lote
DATA: 24/09/2026 10:55
MODIFICADO: 25/09/2026 13:05
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports, praxisforge.application.logging_events
HISTÓRICO:
    - 24/09/2026 10:55: criação (T019, feature 006) — faz test_validate_sources.py passar
    - 25/09/2026 13:05: source-schema-v3 (só ideias); v1/v2 pedem conversão (T042, feature 009)
STATUS: DEV
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import ContractValidator, SourceReader
from praxisforge.domain.errors import (
    InvalidFolderError,
    PraxisForgeError,
    SourceSchemaMigrationRequiredError,
)
from praxisforge.domain.source_record import SourceRecord

logger = logging.getLogger(__name__)

_SCHEMA = "source-schema-v3"


@dataclass(frozen=True)
class SourceFailure:
    """Falha de validação de um registro de fonte."""

    path: Path
    error_type: str
    message: str


@dataclass(frozen=True)
class SourceValidationReport:
    """Resultado da validação em lote: arquivos válidos e falhas por arquivo, ordenados."""

    ok: list[Path]
    failures: list[SourceFailure]


def _opcional_str(documento: Mapping[str, object], campo: str) -> str | None:
    valor = documento.get(campo)
    return valor if isinstance(valor, str) else None


def _to_record(documento: Mapping[str, object]) -> SourceRecord:
    """Converte um frontmatter já validado pelo schema v3 na entidade de domínio."""
    try:
        data = date.fromisoformat(str(documento["date"]))
    except ValueError as error:
        raise InvalidFolderError(f"fonte: date inválida ({error})") from error
    return SourceRecord(
        origin=str(documento["origin"]),
        date=data,
        license=str(documento["license"]),
        relevance=str(documento["relevance"]),
        status=str(documento["status"]),
        author=_opcional_str(documento, "author"),
    )


def _validar_um(reader: SourceReader, validator: ContractValidator, path: Path) -> None:
    documento = reader.read(path)
    if str(documento.get("schema_version")) in ("1", "2") or "extract_allowed" in documento:
        raise SourceSchemaMigrationRequiredError()
    validator.validate(documento, schema_name=_SCHEMA)
    _to_record(documento)


def validate_sources(
    reader: SourceReader, validator: ContractValidator, paths: Sequence[Path]
) -> SourceValidationReport:
    """
    Valida cada registro de fonte (forma pelo schema v3, regras pela entidade); falha por item.

    :param reader: porta de leitura do frontmatter.
    :type reader: SourceReader
    :param validator: porta de validação contra o contrato versionado.
    :type validator: ContractValidator
    :param paths: arquivos `.md` a validar.
    :type paths: Sequence[Path]
    :return: arquivos válidos e falhas por arquivo, ordenados por caminho.
    :rtype: SourceValidationReport
    """
    ok: list[Path] = []
    failures: list[SourceFailure] = []
    for path in sorted(paths):
        try:
            _validar_um(reader, validator, path)
        except PraxisForgeError as error:
            failures.append(
                SourceFailure(path=path, error_type=type(error).__name__, message=str(error))
            )
        else:
            ok.append(path)
    log_event(
        logger,
        event="validate_sources",
        alias="*",
        outcome=f"{len(ok)} ok, {len(failures)} com falha",
        error_type=None,
    )
    return SourceValidationReport(ok=ok, failures=failures)
