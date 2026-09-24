# -*- coding: utf-8 -*-
"""
NOME: errors.py
TITULO: Reexportação de exceções semânticas para a Presentation (sem importar Domain diretamente)
DATA: 22/09/2026 10:05
MODIFICADO: 24/09/2026 10:52
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 10:05: criação — corrige violação de camada revelada por
      tests/architecture/test_layer_rules.py (presentation/cli.py importava
      praxisforge.domain.errors diretamente)
    - 22/09/2026 10:20: adiciona os erros de resolução de caminho (US2), para a
      CLI distinguir código de saída 1 (validação/negócio) de 3 (ambiente)
    - 22/09/2026 10:45: adiciona ContractValidationError e RegistryUnavailableError (US3),
      usados por `sources validate` na CLI
    - 22/09/2026 18:20: adiciona InvalidRootPathError (feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:07: reexporta ContentInspectionError (T011, feature 004)
    - 24/09/2026 10:52: reexporta exceções da política de extração (T009, feature 006)
STATUS: DEV
"""

from praxisforge.domain.errors import (
    ContentInspectionError,
    ContractValidationError,
    ExtractPolicyExceedsLicenseError,
    FolderNotFoundError,
    FolderPathInvalidError,
    FolderPathUnreadableError,
    IncompleteAttributionError,
    InvalidRootPathError,
    NestedFolderPathError,
    PathAlreadyRegisteredError,
    PraxisForgeError,
    RegistryMigrationRequiredError,
    RegistryUnavailableError,
    SourceSchemaMigrationRequiredError,
)

__all__ = [
    "ContentInspectionError",
    "ContractValidationError",
    "ExtractPolicyExceedsLicenseError",
    "FolderNotFoundError",
    "FolderPathInvalidError",
    "FolderPathUnreadableError",
    "IncompleteAttributionError",
    "InvalidRootPathError",
    "NestedFolderPathError",
    "PathAlreadyRegisteredError",
    "PraxisForgeError",
    "RegistryMigrationRequiredError",
    "RegistryUnavailableError",
    "SourceSchemaMigrationRequiredError",
]
