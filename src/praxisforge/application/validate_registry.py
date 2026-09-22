# -*- coding: utf-8 -*-
"""
NOME: validate_registry.py
TITULO: Caso de uso — validar registro de pastas contra contrato, em lote
DATA: 22/09/2026 10:30
MODIFICADO: 22/09/2026 10:08
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports
HISTÓRICO:
    - 22/09/2026 10:30: criação (T058) — faz tests/unit/application/test_validate_registry.py passar
    - 22/09/2026 10:40: relatório próprio (FoldersBatchReport) em vez de reusar
      BatchReport de resolve_folder_path (tipos de `ok` incompatíveis: dict[str, Path]
      vs list[str] — reusar via herança violaria LSP)
STATUS: DEV
"""

import logging
from dataclasses import dataclass

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import ContractValidator, FolderRegistryRepository
from praxisforge.application.resolve_folder_path import ItemFailure
from praxisforge.domain.errors import ContractValidationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FoldersBatchReport:
    """Relatório de validação em lote das pastas de um registro."""

    ok: list[str]
    failures: list[ItemFailure]


def validate_registry(
    repository: FolderRegistryRepository, validator: ContractValidator
) -> FoldersBatchReport:
    """
    Valida cada pasta do registro contra `folders-schema-v1`, agregando falhas por item.

    O documento inteiro (`schema_version`) é validado primeiro; uma versão não
    suportada levanta (não é falha por item). Depois, cada pasta é validada
    isoladamente, embrulhada em `{schema_version, folders: {alias: entry}}`.

    :param repository: porta de persistência do registro.
    :type repository: FolderRegistryRepository
    :param validator: porta de validação de contrato.
    :type validator: ContractValidator
    :return: relatório com aliases ok e falhas por item.
    :rtype: FoldersBatchReport
    :raises RegistryFileNotFoundError: registro ausente.
    :raises UnsupportedSchemaVersionError: versão do registro inteiro não suportada.
    """
    documento = repository.load_raw()
    schema_version = documento.get("schema_version")
    folders = documento.get("folders") or {}
    if not isinstance(folders, dict):
        folders = {}
    # valida o wrapper vazio primeiro para capturar schema_version ausente/errada
    validator.validate({"schema_version": schema_version, "folders": {}}, "folders-schema-v1")

    ok: list[str] = []
    failures: list[ItemFailure] = []
    for alias, entry in folders.items():
        try:
            validator.validate(
                {"schema_version": schema_version, "folders": {alias: entry}},
                "folders-schema-v1",
            )
        except ContractValidationError as error:
            motivo = "; ".join(f"{v.field}: {v.reason}" for v in error.violations)
            failures.append(
                ItemFailure(alias=alias, error_type=type(error).__name__, message=motivo)
            )
        else:
            ok.append(alias)
    log_event(
        logger,
        event="validate_registry",
        alias="*",
        outcome=f"{len(ok)} ok, {len(failures)} com falha",
        error_type=None,
    )
    return FoldersBatchReport(ok=ok, failures=failures)
